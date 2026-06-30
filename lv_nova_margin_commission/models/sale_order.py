from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_cost = fields.Monetary(
        string='Line Cost',
        compute='_compute_margin_commission',
        currency_field='currency_id',
        help='Product standard cost × quantity.',
    )
    line_margin = fields.Monetary(
        string='Line Margin',
        compute='_compute_margin_commission',
        currency_field='currency_id',
        help='Subtotal minus cost.',
    )
    line_margin_pct = fields.Float(
        string='Margin %',
        compute='_compute_margin_commission',
        digits=(5, 1),
    )
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        compute='_compute_margin_commission',
        digits=(5, 2),
    )
    commission_amount = fields.Monetary(
        string='Commission',
        compute='_compute_margin_commission',
        currency_field='currency_id',
    )

    @api.depends(
        'price_subtotal', 'product_uom_qty', 'product_id',
        'order_id.user_id', 'order_id.state',
    )
    def _compute_margin_commission(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.line_cost          = 0.0
                line.line_margin        = 0.0
                line.line_margin_pct    = 0.0
                line.commission_rate    = 0.0
                line.commission_amount  = 0.0
                continue

            cost   = line.product_id.standard_price * line.product_uom_qty
            margin = line.price_subtotal - cost
            margin_pct = (margin / line.price_subtotal * 100.0
                          if line.price_subtotal else 0.0)

            scale = line.order_id.margin_commission_scale_id
            rate  = scale._get_rate_for_margin(margin_pct) if scale else 0.0
            commission = line.price_subtotal * (rate / 100.0)

            line.line_cost         = cost
            line.line_margin       = margin
            line.line_margin_pct   = margin_pct
            line.commission_rate   = rate
            line.commission_amount = commission


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    margin_commission_scale_id = fields.Many2one(
        'margin.commission.scale',
        string='Margin Commission Scale',
        help='Scale used to compute commission per line based on its '
             'profit margin. Defaults from the salesperson\'s profile.',
    )
    total_margin = fields.Monetary(
        string='Total Margin',
        compute='_compute_margin_totals',
        currency_field='currency_id',
    )
    total_margin_pct = fields.Float(
        string='Overall Margin %',
        compute='_compute_margin_totals',
        digits=(5, 1),
    )
    total_commission = fields.Monetary(
        string='Total Commission',
        compute='_compute_margin_totals',
        currency_field='currency_id',
    )

    @api.depends(
        'order_line.line_margin', 'order_line.price_subtotal',
        'order_line.commission_amount',
    )
    def _compute_margin_totals(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            )
            margin     = sum(lines.mapped('line_margin'))
            subtotal   = sum(lines.mapped('price_subtotal'))
            commission = sum(lines.mapped('commission_amount'))

            order.total_margin       = margin
            order.total_margin_pct   = (margin / subtotal * 100.0
                                         if subtotal else 0.0)
            order.total_commission   = commission

    @api.onchange('user_id')
    def _onchange_user_id_margin_commission(self):
        if self.user_id and self.user_id.margin_commission_scale_id:
            self.margin_commission_scale_id = (
                self.user_id.margin_commission_scale_id
            )

    def action_print_commission_report(self):
        self.ensure_one()
        return self.env.ref(
            'lv_nova_margin_commission.action_report_margin_commission'
        ).report_action(self)

    def _fmt(self, amount):
        c = self.currency_id
        s = '{:,.2f}'.format(abs(amount))
        return (c.symbol + '\u00a0' + s if c.position == 'before'
                else s + '\u00a0' + c.symbol)
