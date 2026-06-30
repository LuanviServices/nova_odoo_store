from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    margin_commission_scale_id = fields.Many2one(
        'margin.commission.scale',
        string='Margin Commission Scale',
        help='Default margin-based commission scale applied to this '
             'salesperson\'s confirmed orders.',
    )
