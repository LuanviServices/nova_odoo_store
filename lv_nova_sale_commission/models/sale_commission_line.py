from odoo import api, fields, models


class SaleCommissionLine(models.Model):
    _name = 'sale.commission.line'
    _description = 'Sales Commission Line'
    _order = 'date desc, id desc'

    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson', required=True, index=True,
    )
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    product_id = fields.Many2one('product.product', string='Product')
    plan_id = fields.Many2one('sale.commission.plan', string='Commission Plan')
    base_amount = fields.Monetary(string='Base Amount', currency_field='currency_id')
    rate = fields.Float(string='Rate (%)')
    commission_amount = fields.Monetary(
        string='Commission', currency_field='currency_id',
    )
    date = fields.Date(string='Date', default=fields.Date.context_today)
    payment_date = fields.Date(string='Paid On')
    state = fields.Selection(
        [
            ('confirmed', 'Confirmed'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='confirmed',
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    def action_mark_paid(self):
        self.write({
            'state': 'paid',
            'payment_date': fields.Date.context_today(self),
        })
