from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosTipReportWizard(models.TransientModel):
    _name = 'pos.tip.report.wizard'
    _description = 'POS Tip Report Wizard'

    date_from = fields.Date(
        string='From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.today,
    )
    config_id = fields.Many2one(
        'pos.config',
        string='Point of Sale',
        help='Leave empty to include all POS.',
    )
    only_with_tips = fields.Boolean(
        string='Only orders with tips',
        default=True,
    )

    # ------------------------------------------------------------------
    # Data computation
    # ------------------------------------------------------------------

    def _get_tip_orders(self):
        self.ensure_one()
        domain = [
            ('date_order', '>=', fields.Datetime.from_string(
                str(self.date_from) + ' 00:00:00'
            )),
            ('date_order', '<=', fields.Datetime.from_string(
                str(self.date_to) + ' 23:59:59'
            )),
            ('state', 'in', ('done', 'paid', 'invoiced')),
        ]
        if self.config_id:
            domain.append(('config_id', '=', self.config_id.id))
        if self.only_with_tips:
            domain.append(('tip_amount', '>', 0))
        return self.env['pos.order'].sudo().search(domain, order='date_order asc')

    def get_report_data(self):
        """
        Returns a dict with:
          'by_cashier': [ { cashier, orders, tip_total, sales_total, tip_avg_pct }, ... ]
          'grand_total_tips': float
          'grand_total_sales': float
          'order_count': int
        """
        orders = self._get_tip_orders()

        by_cashier = defaultdict(lambda: {
            'orders': [],
            'tip_total': 0.0,
            'sales_total': 0.0,
        })

        for order in orders:
            key = order.cashier_name or _('Unknown')
            by_cashier[key]['orders'].append(order)
            by_cashier[key]['tip_total']   += order.tip_amount
            by_cashier[key]['sales_total'] += (
                order.amount_total - order.tip_amount
            )

        result = []
        for cashier, data in sorted(by_cashier.items()):
            sales = data['sales_total']
            tips  = data['tip_total']
            result.append({
                'cashier':     cashier,
                'orders':      data['orders'],
                'tip_total':   tips,
                'sales_total': sales,
                'tip_avg_pct': (tips / sales * 100.0) if sales else 0.0,
                'order_count': len(data['orders']),
            })

        grand_tips  = sum(r['tip_total']   for r in result)
        grand_sales = sum(r['sales_total'] for r in result)

        return {
            'by_cashier':        result,
            'grand_total_tips':  grand_tips,
            'grand_total_sales': grand_sales,
            'grand_avg_pct':     (grand_tips / grand_sales * 100.0) if grand_sales else 0.0,
            'order_count':       sum(r['order_count'] for r in result),
        }

    def _fmt(self, amount):
        c = self.env.company.currency_id
        s = '{:,.2f}'.format(abs(amount))
        sign = '-' if amount < 0 else ''
        return ('{}{}\u00a0{}'.format(sign, c.symbol, s)
                if c.position == 'before'
                else '{}{}\u00a0{}'.format(sign, s, c.symbol))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'lv_nova_pos_tips.action_report_pos_tips'
        ).report_action(self)

    def action_view_orders(self):
        self.ensure_one()
        orders = self._get_tip_orders()
        if not orders:
            raise UserError(_('No orders found for the selected period.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tip Orders'),
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', orders.ids)],
        }
