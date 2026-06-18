from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    commission_plan_id = fields.Many2one(
        'sale.commission.plan',
        string='Commission Plan',
        help='Default commission plan applied to this salesperson\'s '
             'sales orders.',
    )
