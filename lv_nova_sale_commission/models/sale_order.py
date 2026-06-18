from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commission_plan_id = fields.Many2one(
        'sale.commission.plan',
        string='Commission Plan',
        help='Plan used to compute the salesperson commission for this '
             'order. Defaults from the salesperson\'s profile.',
    )
    commission_line_count = fields.Integer(
        string='Commission Line Count',
        compute='_compute_commission_line_count',
    )

    @api.depends()
    def _compute_commission_line_count(self):
        groups = self.env['sale.commission.line']._read_group(
            [('sale_order_id', 'in', self.ids)],
            groupby=['sale_order_id'],
            aggregates=['__count'],
        )
        counts = {order.id: count for order, count in groups}
        for order in self:
            order.commission_line_count = counts.get(order.id, 0)

    @api.onchange('user_id')
    def _onchange_user_id_commission(self):
        if self.user_id and self.user_id.commission_plan_id:
            self.commission_plan_id = self.user_id.commission_plan_id

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if (
                order.commission_plan_id
                and order.commission_plan_id.basis == 'order_confirm'
            ):
                order._generate_commission_lines()
        return res

    def _generate_commission_lines(self):
        self.ensure_one()
        plan = self.commission_plan_id
        if not plan:
            return
        if self.env['sale.commission.line'].search_count(
            [('sale_order_id', '=', self.id)]
        ):
            return  # already generated, avoid duplicates on re-confirm

        Commission = self.env['sale.commission.line']
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            rate = plan._get_rate_for_product(line.product_id)
            if plan.calc_method == 'margin':
                cost = line.product_id.standard_price * line.product_uom_qty
                base = line.price_subtotal - cost
            else:
                base = line.price_subtotal
            Commission.create({
                'salesperson_id': self.user_id.id,
                'sale_order_id': self.id,
                'sale_order_line_id': line.id,
                'product_id': line.product_id.id,
                'plan_id': plan.id,
                'base_amount': base,
                'rate': rate,
                'commission_amount': base * (rate / 100.0),
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
            })

    def action_view_commission_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commission Lines',
            'res_model': 'sale.commission.line',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
        }
