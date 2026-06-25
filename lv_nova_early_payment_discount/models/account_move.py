from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Computed discount fields (display only — no stored DB columns)
    # ------------------------------------------------------------------

    early_discount_available = fields.Boolean(
        compute='_compute_early_discount',
        string='Early Discount Available',
    )
    early_discount_pct = fields.Float(
        compute='_compute_early_discount',
        string='Discount %',
        digits=(5, 2),
    )
    early_discount_deadline = fields.Date(
        compute='_compute_early_discount',
        string='Pay by',
    )
    early_discount_amount = fields.Monetary(
        compute='_compute_early_discount',
        string='Discount Amount',
        currency_field='currency_id',
    )
    early_discount_total = fields.Monetary(
        compute='_compute_early_discount',
        string='Amount if Paid Early',
        currency_field='currency_id',
    )
    within_discount_period = fields.Boolean(
        compute='_compute_early_discount',
        string='Within Discount Period',
    )
    early_discount_applied = fields.Boolean(
        string='Early Discount Applied',
        default=False,
        copy=False,
        readonly=True,
        help='Set to True once the early payment discount journal entry '
             'has been posted for this invoice.',
    )

    @api.depends(
        'invoice_payment_term_id',
        'invoice_date',
        'amount_untaxed',
        'state',
        'move_type',
    )
    def _compute_early_discount(self):
        today = fields.Date.today()
        for move in self:
            term = move.invoice_payment_term_id
            is_invoice = move.move_type in ('out_invoice', 'out_refund',
                                             'in_invoice', 'in_refund')
            if (
                not is_invoice
                or not term
                or not term.early_discount
                or not move.invoice_date
            ):
                move.early_discount_available = False
                move.early_discount_pct       = 0.0
                move.early_discount_deadline  = False
                move.early_discount_amount    = 0.0
                move.early_discount_total     = move.amount_total
                move.within_discount_period   = False
                continue

            from datetime import timedelta
            deadline = move.invoice_date + timedelta(days=term.early_discount_days)
            discount_amt = move.amount_untaxed * (term.early_discount_pct / 100.0)

            move.early_discount_available = True
            move.early_discount_pct       = term.early_discount_pct
            move.early_discount_deadline  = deadline
            move.early_discount_amount    = discount_amt
            move.early_discount_total     = move.amount_total - discount_amt
            move.within_discount_period   = today <= deadline

    # ------------------------------------------------------------------
    # Action: open apply-discount wizard
    # ------------------------------------------------------------------

    def action_apply_early_discount(self):
        self.ensure_one()
        if not self.early_discount_available:
            raise UserError(_('No early payment discount is configured for this invoice.'))
        if self.early_discount_applied:
            raise UserError(_('An early payment discount has already been applied to this invoice.'))
        if self.payment_state in ('paid', 'in_payment'):
            raise UserError(_('This invoice is already fully paid.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Apply Early Payment Discount'),
            'res_model': 'early.payment.discount.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }
