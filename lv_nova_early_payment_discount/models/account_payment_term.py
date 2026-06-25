from odoo import api, fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    early_discount = fields.Boolean(
        string='Early Payment Discount',
        default=False,
        help='Enable a cash discount if the invoice is paid before '
             'the discount deadline.',
    )
    early_discount_pct = fields.Float(
        string='Discount (%)',
        digits=(5, 2),
        default=2.0,
        help='Percentage discount applied to the untaxed amount.',
    )
    early_discount_days = fields.Integer(
        string='Discount Days',
        default=10,
        help='Number of days from the invoice date within which the '
             'customer must pay to receive the discount.',
    )
    early_discount_account_id = fields.Many2one(
        'account.account',
        string='Discount Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        help='Account used to post the discount amount when granted. '
             'Typically a "Sales Discounts" or "Early Payment Discounts" '
             'income account.',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    @api.constrains('early_discount_pct')
    def _check_discount_pct(self):
        for term in self:
            if term.early_discount and not (0 < term.early_discount_pct <= 100):
                raise models.ValidationError(
                    'Discount percentage must be between 0 and 100.'
                )
