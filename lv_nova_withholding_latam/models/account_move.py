from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    withholding_line_ids = fields.One2many(
        'account.withholding.line', 'move_id', string='Withholding Lines',
    )
    withholding_total = fields.Monetary(
        string='Total Withheld',
        compute='_compute_withholding_total',
        store=True,
        currency_field='currency_id',
    )
    withholding_move_id = fields.Many2one(
        'account.move',
        string='Withholding Journal Entry',
        readonly=True,
        copy=False,
    )
    withholding_certificate_number = fields.Char(
        string='Withholding Certificate #',
        readonly=True,
        copy=False,
    )

    @api.depends('withholding_line_ids.amount')
    def _compute_withholding_total(self):
        for move in self:
            move.withholding_total = sum(
                move.withholding_line_ids.mapped('amount')
            )

    # -------------------------------------------------------------------
    # Journal entry generation
    # -------------------------------------------------------------------

    def _get_withholding_journal(self):
        self.ensure_one()
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(_(
                'No miscellaneous (general) journal found for company %s. '
                'Please create one in Accounting > Configuration > Journals.'
            ) % self.company_id.name)
        return journal

    def _get_open_receivable_payable_line(self):
        self.ensure_one()
        return self.line_ids.filtered(
            lambda l: l.account_id.account_type in (
                'asset_receivable', 'liability_payable'
            ) and not l.reconciled
        )[:1]

    def action_create_withholding_entry(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_(
                'The invoice/bill must be posted before registering a '
                'withholding entry.'
            ))
        if not self.withholding_line_ids:
            raise UserError(_('Add at least one withholding line first.'))
        if self.withholding_move_id:
            raise UserError(_(
                'A withholding entry already exists for this document.'
            ))

        open_line = self._get_open_receivable_payable_line()
        if not open_line:
            raise UserError(_(
                'Could not find an open receivable/payable line on this '
                'document to apply the withholding against.'
            ))

        journal = self._get_withholding_journal()
        is_sale = self.move_type in ('out_invoice', 'out_refund')

        line_vals = []
        for wh_line in self.withholding_line_ids:
            if is_sale:
                # Customer withheld tax from us: asset (tax credit) debit
                line_vals.append((0, 0, {
                    'name': wh_line.tax_id.name,
                    'account_id': wh_line.tax_id.account_id.id,
                    'partner_id': self.partner_id.id,
                    'debit': wh_line.amount,
                    'credit': 0.0,
                }))
            else:
                # We withheld tax from the vendor: liability credit
                line_vals.append((0, 0, {
                    'name': wh_line.tax_id.name,
                    'account_id': wh_line.tax_id.account_id.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': wh_line.amount,
                }))

        # Counterpart line on the same receivable/payable account as the
        # original document, so it can be reconciled against it.
        if is_sale:
            line_vals.append((0, 0, {
                'name': _('Withholding — %s') % self.name,
                'account_id': open_line.account_id.id,
                'partner_id': self.partner_id.id,
                'debit': 0.0,
                'credit': self.withholding_total,
            }))
        else:
            line_vals.append((0, 0, {
                'name': _('Withholding — %s') % self.name,
                'account_id': open_line.account_id.id,
                'partner_id': self.partner_id.id,
                'debit': self.withholding_total,
                'credit': 0.0,
            }))

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': _('Withholding — %s') % self.name,
            'line_ids': line_vals,
        })
        entry.action_post()

        # Reconcile the new counterpart line with the original open line
        counterpart_line = entry.line_ids.filtered(
            lambda l: l.account_id.id == open_line.account_id.id
        )[:1]
        if counterpart_line:
            (open_line + counterpart_line).reconcile()

        sequence_number = self.env['ir.sequence'].next_by_code(
            'account.withholding.certificate'
        ) or '/'

        self.write({
            'withholding_move_id': entry.id,
            'withholding_certificate_number': sequence_number,
        })
        return True

    def action_view_withholding_entry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Withholding Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.withholding_move_id.id,
        }

    def action_print_withholding_certificate(self):
        self.ensure_one()
        if not self.withholding_line_ids:
            raise UserError(_('There are no withholding lines to print.'))
        return self.env.ref(
            'lv_nova_withholding_latam.action_report_withholding_certificate'
        ).report_action(self)
