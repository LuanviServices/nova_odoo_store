from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    transfer_approval_required = fields.Boolean(
        string='Require Transfer Approval',
        default=False,
        help='When enabled, any internal transfer whose destination '
             'is a location belonging to this warehouse will require '
             'approval before it can be validated.',
    )
    transfer_approver_id = fields.Many2one(
        'res.users',
        string='Transfer Approver',
        domain="[('share', '=', False)]",
        help='User who will receive approval requests and can approve '
             'or reject incoming transfer requests for this warehouse. '
             'If empty, any Stock Manager can approve.',
    )
