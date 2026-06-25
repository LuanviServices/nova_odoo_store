from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockAlertCreatePoWizard(models.TransientModel):
    _name = 'stock.alert.create.po.wizard'
    _description = 'Create Purchase Orders from Stock Alerts'

    orderpoint_ids = fields.Many2many(
        'stock.warehouse.orderpoint',
        string='Reorder Rules',
        domain="[('alert_level', 'in', ('critical', 'warning'))]",
    )
    line_ids = fields.One2many(
        'stock.alert.create.po.wizard.line',
        'wizard_id',
        string='Lines',
    )
    total_lines = fields.Integer(compute='_compute_totals')
    total_suppliers = fields.Integer(compute='_compute_totals')

    @api.depends('line_ids')
    def _compute_totals(self):
        for wiz in self:
            wiz.total_lines = len(wiz.line_ids)
            wiz.total_suppliers = len(wiz.line_ids.mapped('supplier_id'))

    @api.onchange('orderpoint_ids')
    def _onchange_orderpoints(self):
        self.line_ids = [(5, 0, 0)]
        lines = []
        for op in self.orderpoint_ids.filtered(lambda o: o.qty_to_order > 0):
            lines.append((0, 0, {
                'orderpoint_id': op.id,
                'product_id': op.product_id.id,
                'supplier_id': op.supplier_id.id if op.supplier_id else False,
                'qty_to_order': op.qty_to_order,
                'price_unit': op.supplier_price,
                'alert_level': op.alert_level,
            }))
        self.line_ids = lines

    def action_confirm(self):
        self.ensure_one()
        lines_with_supplier = self.line_ids.filtered(lambda l: l.supplier_id)
        if not lines_with_supplier:
            raise UserError(_(
                'None of the selected products have a preferred supplier. '
                'Please set one on each product\'s Purchase tab.'
            ))

        by_supplier = defaultdict(list)
        for line in lines_with_supplier:
            by_supplier[line.supplier_id].append(
                (line.orderpoint_id, line.qty_to_order)
            )

        pos = self.orderpoint_ids._make_po(by_supplier)

        skipped = len(self.line_ids) - len(lines_with_supplier)
        msg = _('%d purchase order(s) created.') % len(pos)
        if skipped:
            msg += ' ' + _('%d line(s) skipped (no supplier defined).') % skipped

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pos.ids)],
        }


class StockAlertCreatePoWizardLine(models.TransientModel):
    _name = 'stock.alert.create.po.wizard.line'
    _description = 'Stock Alert PO Wizard Line'

    wizard_id = fields.Many2one(
        'stock.alert.create.po.wizard', ondelete='cascade',
    )
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint')
    product_id = fields.Many2one('product.product', string='Product')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    qty_to_order = fields.Float(string='Qty to Order', digits='Product Unit of Measure')
    price_unit = fields.Float(string='Price', digits='Product Price')
    alert_level = fields.Selection([
        ('critical', 'Out of Stock'),
        ('warning', 'Low Stock'),
    ])
