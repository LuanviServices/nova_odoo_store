from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_expiry_display = fields.Char(
        string='Lots / Expiry',
        compute='_compute_lot_expiry_display',
        store=False,
        help='Lot numbers and expiry dates from related deliveries or receipts.',
    )
    lot_expiry_state = fields.Selection(
        [
            ('expired', 'Has Expired Lots'),
            ('warning', 'Has Lots Expiring Soon'),
            ('ok',      'All Lots OK'),
            ('none',    'No Lots'),
        ],
        string='Expiry Status',
        compute='_compute_lot_expiry_display',
        store=False,
    )

    @api.depends('move_id', 'product_id')
    def _compute_lot_expiry_display(self):
        today = fields.Date.today()
        for line in self:
            lots = self._get_lots_for_line(line)
            if not lots:
                line.lot_expiry_display = ''
                line.lot_expiry_state   = 'none'
                continue

            parts  = []
            worst  = 'ok'
            for lot in lots:
                exp = lot.expiration_date
                text = lot.name
                if exp:
                    exp_date = exp.date() if hasattr(exp, 'date') else exp
                    delta    = (exp_date - today).days
                    text    += ' — %s' % str(exp_date)
                    if delta < 0:
                        text  += ' ⚠ EXPIRED'
                        worst  = 'expired'
                    elif delta <= 30:
                        text  += ' ⚠ %dd' % delta
                        if worst != 'expired':
                            worst = 'warning'
                parts.append(text)

            line.lot_expiry_display = ' | '.join(parts)
            line.lot_expiry_state   = worst

    @staticmethod
    def _get_lots_for_line(line):
        """Collect stock.lot records linked to this invoice/bill line."""
        lots = line.env['stock.lot'].browse()

        # Path 1: via sale.order.line (sales invoices)
        sale_lines = getattr(line, 'sale_line_ids', line.env['sale.order.line']
                             if 'sale.order.line' in line.env else [])
        for sl in sale_lines:
            for move in getattr(sl, 'move_ids', []):
                if move.state == 'done':
                    lots |= move.move_line_ids.mapped('lot_id')

        # Path 2: via purchase.order.line (vendor bills)
        purchase_line = getattr(line, 'purchase_line_id', False)
        if purchase_line:
            for move in getattr(purchase_line, 'move_ids', []):
                if move.state == 'done':
                    lots |= move.move_line_ids.mapped('lot_id')

        return lots.filtered(lambda l: l.id)
