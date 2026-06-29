from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    tip_amount = fields.Monetary(
        string='Tip Amount',
        compute='_compute_tip_amount',
        store=True,
        currency_field='currency_id',
        help='Sum of all order lines whose product matches the '
             'POS config tip product.',
    )
    tip_percent = fields.Float(
        string='Tip %',
        compute='_compute_tip_amount',
        store=True,
        digits=(5, 1),
        help='Tip as a percentage of the order subtotal (excluding the tip line).',
    )
    cashier_name = fields.Char(
        string='Cashier',
        compute='_compute_cashier_name',
        store=True,
    )

    @api.depends('lines.product_id', 'lines.price_subtotal_incl',
                 'config_id.tip_product_id')
    def _compute_tip_amount(self):
        for order in self:
            tip_product = order.config_id.tip_product_id
            if not tip_product:
                order.tip_amount  = 0.0
                order.tip_percent = 0.0
                continue

            tip_lines = order.lines.filtered(
                lambda l: l.product_id == tip_product
            )
            tip = sum(tip_lines.mapped('price_subtotal_incl'))
            subtotal = sum(
                order.lines.filtered(
                    lambda l: l.product_id != tip_product
                ).mapped('price_subtotal_incl')
            )
            order.tip_amount  = tip
            order.tip_percent = (tip / subtotal * 100.0) if subtotal else 0.0

    @api.depends('employee_id', 'user_id')
    def _compute_cashier_name(self):
        for order in self:
            if order.employee_id:
                order.cashier_name = order.employee_id.name
            elif order.user_id:
                order.cashier_name = order.user_id.name
            else:
                order.cashier_name = ''
