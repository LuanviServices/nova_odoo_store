from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EarlyPaymentDiscountWizard(models.TransientModel):
    _name = 'early.payment.discount.wizard'
    _description = 'Apply Early Payment Discount'

    move_id = fields.Many2one(
        'account.move', string='Invoice', required=True,
        domain=[('state', '=', 'posted')],
    )
    discount_pct    = fields.Float(string='Discount %',   readonly=True, digits=(5, 2))
    discount_amount = fields.Monetary(string='Discount Amount', readonly=True,
                                       currency_field='currency_id')
    discount_account_id = fields.Many2one(
        'account.account', string='Discount Account', required=True,
    )
    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
    date = fields.Date(string='Discount Date', default=fields.Date.today, required=True)
    currency_id = fields.Many2one(related='move_id.currency_id')
    company_id  = fields.Many2one(related='move_id.company_id')
    within_period = fields.Boolean(readonly=True)
    deadline     = fields.Date(string='Discount Deadline', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move_id = self.env.context.get('default_move_id')
        if not move_id:
            return res
        move = self.env['account.move'].browse(move_id)
        term = move.invoice_payment_term_id

        res.update({
            'discount_pct':    move.early_discount_pct,
            'discount_amount': move.early_discount_amount,
            'within_period':   move.within_discount_period,
            'deadline':        move.early_discount_deadline,
        })

        # Default discount account from payment term or fallback search
        if term and term.early_discount_account_id:
            res['discount_account_id'] = term.early_discount_account_id.id
        else:
            account = self.env['account.account'].search([
                ('company_id', '=', move.company_id.id),
                ('deprecated', '=', False),
                ('account_type', 'in', ('income', 'income_other')),
                '|',
                ('name', 'ilike', 'discount'),
                ('code', 'ilike', 'discount'),
            ], limit=1)
            if account:
                res['discount_account_id'] = account.id

        # Default journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', move.company_id.id),
        ], limit=1)
        if journal:
            res['journal_id'] = journal.id

        return res

    def action_apply(self):
        self.ensure_one()
        move = self.move_id

        if move.early_discount_applied:
            raise UserError(_('A discount has already been applied to this invoice.'))
        if not self.discount_account_id:
            raise UserError(_('Please select a discount account.'))
        if self.discount_amount <= 0:
            raise UserError(_('The discount amount must be positive.'))

        # Find the open receivable/payable line on the invoice
        is_sale = move.move_type in ('out_invoice', 'out_refund')
        account_type = 'asset_receivable' if is_sale else 'liability_payable'

        open_line = move.line_ids.filtered(
            lambda l: l.account_id.account_type == account_type
            and not l.reconciled
        )[:1]

        if not open_line:
            raise UserError(_(
                'No open receivable/payable line found on this invoice. '
                'It may already be fully reconciled.'
            ))

        # Build the discount journal entry
        # For a sale invoice:
        #   DR  Accounts Receivable      (reduces what the customer owes)
        #   CR  Sales Discount Income    (records the granted discount)
        if is_sale:
            lines = [
                (0, 0, {
                    'account_id': open_line.account_id.id,
                    'partner_id': move.partner_id.id,
                    'name': _('Early payment discount — %s') % move.name,
                    'credit': self.discount_amount,
                    'debit': 0.0,
                    'currency_id': move.currency_id.id,
                }),
                (0, 0, {
                    'account_id': self.discount_account_id.id,
                    'partner_id': move.partner_id.id,
                    'name': _('Early payment discount — %s') % move.name,
                    'debit': 0.0,
                    'credit': 0.0,
                    'amount_currency': -self.discount_amount,
                }),
            ]
            # Correct amounts for the income side
            lines[1][2]['credit'] = self.discount_amount
            lines[1][2]['debit']  = 0.0
        else:
            # Vendor bill: discount reduces what we owe the vendor
            lines = [
                (0, 0, {
                    'account_id': open_line.account_id.id,
                    'partner_id': move.partner_id.id,
                    'name': _('Early payment discount — %s') % move.name,
                    'debit': self.discount_amount,
                    'credit': 0.0,
                    'currency_id': move.currency_id.id,
                }),
                (0, 0, {
                    'account_id': self.discount_account_id.id,
                    'partner_id': move.partner_id.id,
                    'name': _('Early payment discount — %s') % move.name,
                    'debit': 0.0,
                    'credit': self.discount_amount,
                    'currency_id': move.currency_id.id,
                }),
            ]

        discount_entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': _('Early payment discount — %s (%.2f%%)') % (
                move.name, self.discount_pct
            ),
            'line_ids': lines,
        })
        discount_entry.action_post()

        # Reconcile the receivable/payable line with the discount entry's
        # corresponding line so the invoice balance is reduced
        discount_counterpart = discount_entry.line_ids.filtered(
            lambda l: l.account_id.account_type == account_type
        )[:1]
        if discount_counterpart:
            (open_line + discount_counterpart).reconcile()

        move.early_discount_applied = True
        move.message_post(
            body=_(
                'Early payment discount of <b>%(pct).2f%%</b> '
                '(%(amount)s) applied. '
                'Journal entry: <a href="/web#id=%(entry_id)s&model=account.move">'
                '%(entry_name)s</a>'
            ) % {
                'pct':        self.discount_pct,
                'amount':     self._fmt(self.discount_amount, move),
                'entry_id':   discount_entry.id,
                'entry_name': discount_entry.name,
            },
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Discount Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': discount_entry.id,
        }

    @staticmethod
    def _fmt(amount, move):
        c = move.currency_id
        s = '{:,.2f}'.format(abs(amount))
        return (c.symbol + '\u00a0' + s) if c.position == 'before' else (s + '\u00a0' + c.symbol)
