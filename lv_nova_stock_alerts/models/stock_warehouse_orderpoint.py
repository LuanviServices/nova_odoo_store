from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    # ------------------------------------------------------------------
    # Computed alert fields
    # ------------------------------------------------------------------

    alert_level = fields.Selection(
        [
            ('critical', 'Out of Stock'),
            ('warning', 'Low Stock'),
            ('ok', 'OK'),
        ],
        string='Alert Level',
        compute='_compute_alert_level',
        store=True,
        help='Critical: on-hand ≤ 0.  Low Stock: on-hand < minimum.  OK: on-hand ≥ minimum.',
    )
    qty_to_order = fields.Float(
        string='Qty to Order',
        compute='_compute_alert_level',
        store=True,
        digits='Product Unit of Measure',
        help='Quantity needed to bring stock up to the maximum level.',
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Preferred Supplier',
        compute='_compute_supplier_info',
        store=True,
    )
    supplier_price = fields.Float(
        string='Supplier Price',
        compute='_compute_supplier_info',
        store=True,
        digits='Product Price',
    )
    lead_days = fields.Integer(
        string='Lead Time (days)',
        compute='_compute_supplier_info',
        store=True,
    )
    estimated_arrival = fields.Date(
        string='Est. Arrival',
        compute='_compute_supplier_info',
        store=True,
        help='Today + lead time, if a supplier is set.',
    )
    last_alert_sent = fields.Datetime(
        string='Last Alert Email',
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('qty_on_hand', 'product_min_qty', 'product_max_qty')
    def _compute_alert_level(self):
        for op in self:
            qty = op.qty_on_hand
            if qty <= 0:
                op.alert_level = 'critical'
            elif qty < op.product_min_qty:
                op.alert_level = 'warning'
            else:
                op.alert_level = 'ok'

            if qty < op.product_min_qty:
                op.qty_to_order = max(0.0, (op.product_max_qty or op.product_min_qty) - qty)
            else:
                op.qty_to_order = 0.0

    @api.depends('product_id')
    def _compute_supplier_info(self):
        today = fields.Date.today()
        for op in self:
            sellers = op.product_id.seller_ids.filtered(
                lambda s: not s.date_end or s.date_end >= today
            ).sorted('sequence')[:1]
            if sellers:
                s = sellers[0]
                op.supplier_id = s.partner_id
                op.supplier_price = s.price
                op.lead_days = int(s.delay or 0)
                if s.delay:
                    op.estimated_arrival = fields.Date.add(today, days=int(s.delay))
                else:
                    op.estimated_arrival = False
            else:
                op.supplier_id = False
                op.supplier_price = 0.0
                op.lead_days = 0
                op.estimated_arrival = False

    # ------------------------------------------------------------------
    # Quick single-line PO action (button on form / list)
    # ------------------------------------------------------------------

    def action_create_po_single(self):
        """Create a draft PO for this single orderpoint line."""
        self.ensure_one()
        if not self.supplier_id:
            raise UserError(_(
                'Product "%s" has no preferred supplier defined. '
                'Please add one under the product\'s Purchase tab.'
            ) % self.product_id.display_name)
        if self.qty_to_order <= 0:
            raise UserError(_(
                'Stock is already at or above the minimum level for "%s".'
            ) % self.product_id.display_name)

        po = self._make_po({self.supplier_id: [(self, self.qty_to_order)]})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': po.id,
        }

    # ------------------------------------------------------------------
    # Shared PO builder (used by single button and bulk wizard)
    # ------------------------------------------------------------------

    def _make_po(self, by_supplier):
        """
        by_supplier: dict {partner: [(orderpoint, qty), ...]}
        Returns the last PO created (for single use) or all POs.
        """
        PO = self.env['purchase.order']
        all_pos = PO
        for partner, lines in by_supplier.items():
            order_lines = []
            for op, qty in lines:
                product = op.product_id
                uom = op.product_uom or product.uom_po_id or product.uom_id
                price = op.supplier_price or product.standard_price
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_qty': qty,
                    'product_uom': uom.id,
                    'price_unit': price,
                    'name': product.display_name,
                    'date_planned': fields.Datetime.now(),
                }))
            po = PO.create({
                'partner_id': partner.id,
                'order_line': order_lines,
                'origin': _('Stock Alert — Auto'),
            })
            all_pos |= po
        return all_pos

    # ------------------------------------------------------------------
    # Scheduled action — daily email digest to stock managers
    # ------------------------------------------------------------------

    @api.model
    def _cron_send_stock_alerts(self):
        """Send a daily email digest of all critical and low-stock items."""
        companies = self.env['res.company'].search([])
        for company in companies:
            alerts = self.search([
                ('alert_level', 'in', ('critical', 'warning')),
                ('company_id', '=', company.id),
            ], order='alert_level asc, product_id asc')
            if not alerts:
                continue

            # Find stock managers to notify
            group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
            if not group:
                continue
            managers = group.users.filtered(
                lambda u: u.company_ids & company
            )
            if not managers:
                continue

            body = self._build_alert_email_body(alerts, company)
            subject = _('[%s] Stock Alerts — %s item(s) below minimum') % (
                company.name, len(alerts)
            )
            for manager in managers:
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': manager.email,
                    'auto_delete': True,
                }).send()

            alerts.write({'last_alert_sent': fields.Datetime.now()})

    def _build_alert_email_body(self, alerts, company):
        critical = alerts.filtered(lambda a: a.alert_level == 'critical')
        warning  = alerts.filtered(lambda a: a.alert_level == 'warning')
        rows = ''
        for a in alerts:
            color = '#dc3545' if a.alert_level == 'critical' else '#ffc107'
            label = 'OUT OF STOCK' if a.alert_level == 'critical' else 'LOW STOCK'
            rows += (
                '<tr>'
                f'<td style="padding:6px 10px;">{a.product_id.display_name}</td>'
                f'<td style="padding:6px 10px; text-align:right;">{a.qty_on_hand:.2f}</td>'
                f'<td style="padding:6px 10px; text-align:right;">{a.product_min_qty:.2f}</td>'
                f'<td style="padding:6px 10px; text-align:right;">{a.qty_to_order:.2f}</td>'
                f'<td style="padding:6px 10px;">{a.supplier_id.name if a.supplier_id else "—"}</td>'
                f'<td style="padding:6px 10px; text-align:center;">{a.lead_days or "—"}</td>'
                f'<td style="padding:6px 10px;">'
                f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">'
                f'{label}</span></td>'
                '</tr>'
            )
        return f'''
<div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
  <h2 style="color:#0F6E56;">{company.name} — Stock Alert Digest</h2>
  <p>
    <strong style="color:#dc3545;">{len(critical)} out-of-stock</strong> &nbsp;|&nbsp;
    <strong style="color:#856404;">{len(warning)} low-stock</strong> item(s) require attention.
  </p>
  <table style="border-collapse:collapse;width:100%;font-size:13px;">
    <thead>
      <tr style="background:#f4f4f4;">
        <th style="padding:8px 10px;text-align:left;">Product</th>
        <th style="padding:8px 10px;text-align:right;">On Hand</th>
        <th style="padding:8px 10px;text-align:right;">Minimum</th>
        <th style="padding:8px 10px;text-align:right;">To Order</th>
        <th style="padding:8px 10px;text-align:left;">Supplier</th>
        <th style="padding:8px 10px;text-align:center;">Lead (days)</th>
        <th style="padding:8px 10px;">Level</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="margin-top:20px;color:#888;font-size:12px;">
    Sent automatically by Odoo — lv_nova_stock_alerts
  </p>
</div>'''
