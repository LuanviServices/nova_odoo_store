from odoo import api, fields, models


class SaleApprovalRule(models.Model):
    _name = 'sale.approval.rule'
    _description = 'Sale Quotation Approval Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(
        string='Level',
        default=10,
        help='Lower sequence = first level to be approved. Use 10, 20, 30… '
             'to leave room between levels.',
    )
    trigger = fields.Selection(
        [
            ('amount',   'Order Amount Exceeds'),
            ('discount', 'Line Discount Exceeds'),
            ('both',     'Amount OR Discount Exceeds'),
        ],
        string='Trigger',
        required=True,
        default='amount',
    )
    amount_threshold = fields.Monetary(
        string='Amount Threshold',
        currency_field='currency_id',
        help='Approval required when the order subtotal exceeds this amount.',
    )
    discount_threshold = fields.Float(
        string='Discount Threshold (%)',
        help='Approval required when any order line discount exceeds this %.',
    )
    approver_type = fields.Selection(
        [
            ('user',  'Specific User'),
            ('group', 'User Group'),
        ],
        string='Approver',
        required=True,
        default='user',
    )
    approver_user_id = fields.Many2one(
        'res.users',
        string='Approver User',
        domain="[('share', '=', False)]",
    )
    approver_group_id = fields.Many2one(
        'res.groups',
        string='Approver Group',
        help='Any user belonging to this group can approve.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    @api.constrains('approver_type', 'approver_user_id', 'approver_group_id')
    def _check_approver(self):
        for rule in self:
            if rule.approver_type == 'user' and not rule.approver_user_id:
                raise models.ValidationError(
                    'Please select a specific user for rule "%s".' % rule.name
                )
            if rule.approver_type == 'group' and not rule.approver_group_id:
                raise models.ValidationError(
                    'Please select a user group for rule "%s".' % rule.name
                )

    def _matches_order(self, order):
        """Return True if this rule should trigger for the given sale order."""
        self.ensure_one()
        amount_ok = (
            self.trigger in ('amount', 'both')
            and order.amount_untaxed >= self.amount_threshold
        )
        max_disc = max(
            (line.discount for line in order.order_line if not line.display_type),
            default=0.0,
        )
        discount_ok = (
            self.trigger in ('discount', 'both')
            and max_disc >= self.discount_threshold
        )
        if self.trigger == 'amount':
            return amount_ok
        if self.trigger == 'discount':
            return discount_ok
        return amount_ok or discount_ok

    def _user_can_approve(self, user):
        """Return True if the given user is authorized to approve this level."""
        self.ensure_one()
        if self.approver_type == 'user':
            return user == self.approver_user_id
        return user in self.approver_group_id.users
