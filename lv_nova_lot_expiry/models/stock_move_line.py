from odoo import api, fields, models

EXPIRY_WARNING_DAYS = 30   # orange zone: expiring within N days


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    lot_expiration_date = fields.Datetime(
        string='Expiry Date',
        related='lot_id.expiration_date',
        store=False,
        readonly=True,
    )

    expiry_state = fields.Selection(
        [
            ('expired',  'Expired'),
            ('warning',  'Expiring Soon'),
            ('ok',       'OK'),
            ('no_date',  'No Date'),
        ],
        string='Expiry Status',
        compute='_compute_expiry_state',
        store=False,
    )

    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_expiry_state',
        store=False,
    )

    @api.depends('lot_id', 'lot_id.expiration_date')
    def _compute_expiry_state(self):
        today = fields.Date.today()
        for line in self:
            exp = line.lot_id.expiration_date if line.lot_id else False
            if not exp:
                line.expiry_state  = 'no_date'
                line.days_to_expiry = 0
                continue
            exp_date = exp.date() if hasattr(exp, 'date') else exp
            delta = (exp_date - today).days
            line.days_to_expiry = delta
            if delta < 0:
                line.expiry_state = 'expired'
            elif delta <= EXPIRY_WARNING_DAYS:
                line.expiry_state = 'warning'
            else:
                line.expiry_state = 'ok'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_expiry_alerts = fields.Boolean(
        string='Has Expiry Alerts',
        compute='_compute_has_expiry_alerts',
        store=False,
    )
    expiry_alert_summary = fields.Char(
        string='Expiry Alert Summary',
        compute='_compute_has_expiry_alerts',
        store=False,
    )

    @api.depends('move_line_ids.lot_id', 'move_line_ids.lot_id.expiration_date')
    def _compute_has_expiry_alerts(self):
        today = fields.Date.today()
        for picking in self:
            expired  = []
            warning  = []
            for ml in picking.move_line_ids.filtered('lot_id'):
                exp = ml.lot_id.expiration_date
                if not exp:
                    continue
                exp_date = exp.date() if hasattr(exp, 'date') else exp
                delta = (exp_date - today).days
                if delta < 0:
                    expired.append(ml.lot_id.name)
                elif delta <= EXPIRY_WARNING_DAYS:
                    warning.append(ml.lot_id.name)

            parts = []
            if expired:
                parts.append('%d expired lot(s)' % len(expired))
            if warning:
                parts.append('%d expiring soon' % len(warning))

            picking.has_expiry_alerts = bool(expired or warning)
            picking.expiry_alert_summary = ', '.join(parts) if parts else ''
