from odoo import fields, models


class SaleApprovalLine(models.Model):
    _name = 'sale.approval.line'
    _description = 'Sale Quotation Approval Line'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order', string='Quotation', required=True, ondelete='cascade',
    )
    rule_id = fields.Many2one(
        'sale.approval.rule', string='Rule', required=True,
    )
    sequence = fields.Integer(related='rule_id.sequence', store=True)
    level_name = fields.Char(
        string='Level', related='rule_id.name', store=True,
    )
    approver_user_id = fields.Many2one(
        'res.users', string='Assigned To',
        help='Specific user assigned to approve this level.',
    )
    approver_group_id = fields.Many2one(
        'res.groups', string='Approver Group',
    )
    state = fields.Selection(
        [
            ('pending',  'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='pending',
        required=True,
    )
    approved_by = fields.Many2one(
        'res.users', string='Decided By', readonly=True,
    )
    decision_date = fields.Datetime(string='Decision Date', readonly=True)
    comment = fields.Text(string='Comment / Reason')
