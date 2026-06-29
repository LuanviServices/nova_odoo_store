from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # ------------------------------------------------------------------
    # Tip product (the product added to the order when a tip is given)
    # ------------------------------------------------------------------
    tip_product_id = fields.Many2one(
        'product.product',
        string='Tip Product',
        domain=[('available_in_pos', '=', True)],
        help='Product used to record tips as an order line. '
             'It should be a service product with no tax.',
    )

    # ------------------------------------------------------------------
    # Suggested tip percentages shown on the receipt screen
    # ------------------------------------------------------------------
    tip_pct_1 = fields.Float(
        string='Tip % (1st suggestion)',
        default=10.0,
        digits=(5, 1),
    )
    tip_pct_2 = fields.Float(
        string='Tip % (2nd suggestion)',
        default=15.0,
        digits=(5, 1),
    )
    tip_pct_3 = fields.Float(
        string='Tip % (3rd suggestion)',
        default=20.0,
        digits=(5, 1),
    )
    tip_allow_custom = fields.Boolean(
        string='Allow Custom Amount',
        default=True,
        help='Let the cashier enter any tip amount, not just the preset %.',
    )
