from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    signature_required = fields.Boolean(
        string='Require Signature',
        default=False,
        help='When enabled, a delivery signature must be captured '
             'before the picking can be validated.',
    )
