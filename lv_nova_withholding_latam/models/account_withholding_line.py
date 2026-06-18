from odoo import api, fields, models


class AccountWithholdingLine(models.Model):
    _name = 'account.withholding.line'
    _description = 'Withholding Tax Line'

    move_id = fields.Many2one(
        'account.move',
        string='Invoice / Bill',
        required=True,
        ondelete='cascade',
    )
    tax_id = fields.Many2one(
        'account.withholding.tax',
        string='Withholding Tax',
        required=True,
    )
    base_amount = fields.Monetary(
        string='Base Amount',
        required=True,
        currency_field='currency_id',
    )
    percent = fields.Float(
        string='Percent',
        related='tax_id.percent',
        readonly=False,
        store=True,
    )
    amount = fields.Monetary(
        string='Withheld Amount',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='move_id.currency_id',
        store=True,
    )
    company_id = fields.Many2one(
        related='move_id.company_id',
        store=True,
    )

    @api.depends('base_amount', 'percent')
    def _compute_amount(self):
        for line in self:
            line.amount = line.base_amount * (line.percent / 100.0)

    @api.onchange('tax_id')
    def _onchange_tax_id(self):
        if self.tax_id and not self.base_amount and self.move_id:
            self.base_amount = self.move_id.amount_untaxed
