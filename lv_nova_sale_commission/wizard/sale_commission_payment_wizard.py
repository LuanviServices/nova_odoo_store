from odoo import api, fields, models


class SaleCommissionPaymentWizard(models.TransientModel):
    _name = 'sale.commission.payment.wizard'
    _description = 'Mark Commission Lines as Paid'

    commission_line_ids = fields.Many2many(
        'sale.commission.line', string='Commission Lines',
    )
    payment_date = fields.Date(
        string='Payment Date', default=fields.Date.context_today, required=True,
    )
    total_amount = fields.Monetary(
        string='Total to Pay', compute='_compute_total_amount',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )

    @api.depends('commission_line_ids.commission_amount')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = sum(
                wiz.commission_line_ids.mapped('commission_amount')
            )

    def action_confirm(self):
        self.ensure_one()
        self.commission_line_ids.write({
            'state': 'paid',
            'payment_date': self.payment_date,
        })
        return {'type': 'ir.actions.act_window_close'}
