from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    last_price_unit = fields.Monetary(
        string='Last Price',
        compute='_compute_price_history',
        currency_field='currency_id',
        help='Last unit price charged to this customer for this product, '
             'on a previous confirmed sale order.',
    )
    last_price_date = fields.Date(
        string='Last Sold On',
        compute='_compute_price_history',
        help='Date of the confirmed order where the last price was charged.',
    )
    price_history_count = fields.Integer(
        string='History Count',
        compute='_compute_price_history',
    )
    price_delta_percent = fields.Float(
        string='Price Δ %',
        compute='_compute_price_history',
        help='Variation between the current unit price and the last price '
             'charged to this customer, in percent.',
    )
    order_date = fields.Datetime(
        string='Order Date',
        related='order_id.date_order',
        store=False,
        readonly=True,
    )

    @api.depends(
        'product_id',
        'order_partner_id',
        'price_unit',
        'order_id.state',
    )
    def _compute_price_history(self):
        for line in self:
            last_price = 0.0
            last_date = False
            count = 0
            delta = 0.0

            partner = line.order_partner_id
            if line.product_id and partner:
                domain = [
                    ('product_id', '=', line.product_id.id),
                    (
                        'order_id.partner_id',
                        'child_of',
                        partner.commercial_partner_id.id,
                    ),
                    ('order_id.state', '=', 'sale'),
                    ('order_id.company_id', '=', line.company_id.id),
                ]
                # Exclude the current line itself when it already has a
                # real database id (new/unsaved lines have a virtual NewId).
                if isinstance(line.id, int):
                    domain.append(('id', '!=', line.id))

                history_lines = self.env['sale.order.line'].sudo().search(
                    domain, order='order_id desc, id desc', limit=50
                )
                count = len(history_lines)
                if history_lines:
                    latest = history_lines[0]
                    last_price = latest.price_unit
                    last_date = latest.order_id.date_order and \
                        latest.order_id.date_order.date()
                    if last_price:
                        delta = (line.price_unit - last_price) / last_price

            line.last_price_unit = last_price
            line.last_price_date = last_date
            line.price_history_count = count
            line.price_delta_percent = delta

    def action_view_price_history(self):
        """Open a read-only list of every confirmed order line for this
        customer + product, most recent first."""
        self.ensure_one()
        partner = self.order_partner_id
        domain = [
            ('product_id', '=', self.product_id.id),
            (
                'order_id.partner_id',
                'child_of',
                partner.commercial_partner_id.id if partner else 0,
            ),
            ('order_id.state', '=', 'sale'),
            ('order_id.company_id', '=', self.company_id.id),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Price History — %s', self.product_id.display_name),
            'res_model': 'sale.order.line',
            'view_mode': 'list,form',
            'views': [
                (
                    self.env.ref(
                        'lv_nova_price_history.view_sale_order_line_price_history_list'
                    ).id,
                    'list',
                ),
                (False, 'form'),
            ],
            'domain': domain,
            'target': 'new',
            'context': {'create': False, 'edit': False, 'delete': False},
        }
