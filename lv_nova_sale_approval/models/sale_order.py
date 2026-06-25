from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Approval fields
    # ------------------------------------------------------------------

    approval_state = fields.Selection(
        [
            ('none',     'No Approval Needed'),
            ('pending',  'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval Status',
        default='none',
        copy=False,
        tracking=True,
    )
    approval_line_ids = fields.One2many(
        'sale.approval.line', 'order_id', string='Approval Lines', copy=False,
    )
    approval_pending_level = fields.Integer(
        string='Pending Level',
        compute='_compute_approval_pending_level',
    )
    current_user_can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_current_user_can_approve',
    )
    needs_approval = fields.Boolean(
        string='Needs Approval',
        compute='_compute_needs_approval',
        help='True if at least one active rule matches this order.',
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('approval_line_ids.state', 'approval_line_ids.sequence')
    def _compute_approval_pending_level(self):
        for order in self:
            pending = order.approval_line_ids.filtered(
                lambda l: l.state == 'pending'
            ).sorted('sequence')[:1]
            order.approval_pending_level = pending.sequence if pending else 0

    @api.depends('approval_state', 'approval_line_ids.state',
                 'approval_line_ids.approver_user_id',
                 'approval_line_ids.approver_group_id')
    def _compute_current_user_can_approve(self):
        me = self.env.user
        for order in self:
            if order.approval_state != 'pending':
                order.current_user_can_approve = False
                continue
            pending_line = order.approval_line_ids.filtered(
                lambda l: l.state == 'pending'
            ).sorted('sequence')[:1]
            if not pending_line:
                order.current_user_can_approve = False
                continue
            rule = pending_line.rule_id
            order.current_user_can_approve = rule._user_can_approve(me)

    @api.depends('amount_untaxed', 'order_line.discount', 'company_id')
    def _compute_needs_approval(self):
        for order in self:
            rules = self.env['sale.approval.rule'].search([
                ('active', '=', True),
                ('company_id', '=', order.company_id.id),
            ])
            order.needs_approval = any(r._matches_order(order) for r in rules)

    # ------------------------------------------------------------------
    # Helper: get matching rules ordered by sequence
    # ------------------------------------------------------------------

    def _get_matching_rules(self):
        self.ensure_one()
        rules = self.env['sale.approval.rule'].search([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
        ])
        return rules.filtered(lambda r: r._matches_order(self)).sorted('sequence')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_submit_for_approval(self):
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            raise UserError(_('Only draft or sent quotations can be submitted for approval.'))

        matching_rules = self._get_matching_rules()
        if not matching_rules:
            raise UserError(_(
                'No approval rules match this quotation. '
                'You can confirm it directly.'
            ))

        # Clear any previous approval lines
        self.approval_line_ids.unlink()

        lines = []
        for rule in matching_rules:
            lines.append({
                'order_id': self.id,
                'rule_id': rule.id,
                'approver_user_id': rule.approver_user_id.id
                    if rule.approver_type == 'user' else False,
                'approver_group_id': rule.approver_group_id.id
                    if rule.approver_type == 'group' else False,
                'state': 'pending',
            })
        self.env['sale.approval.line'].create(lines)
        self.approval_state = 'pending'

        # Notify first approver via chatter
        first = self.approval_line_ids.sorted('sequence')[:1]
        self._notify_approver(first)

        self.message_post(
            body=_('Quotation submitted for approval. Waiting for level: <b>%s</b>.')
                 % first.level_name,
            subtype_xmlid='mail.mt_note',
        )
        return True

    def action_approve(self):
        self.ensure_one()
        if self.approval_state != 'pending':
            raise UserError(_('This quotation is not waiting for approval.'))

        me = self.env.user
        pending_lines = self.approval_line_ids.filtered(
            lambda l: l.state == 'pending'
        ).sorted('sequence')
        if not pending_lines:
            raise UserError(_('No pending approval level found.'))

        current_line = pending_lines[0]
        if not current_line.rule_id._user_can_approve(me):
            raise UserError(_(
                'You are not authorised to approve level "%s".'
            ) % current_line.level_name)

        current_line.write({
            'state': 'approved',
            'approved_by': me.id,
            'decision_date': fields.Datetime.now(),
        })

        self.message_post(
            body=_('Level <b>%s</b> approved by %s.') % (current_line.level_name, me.name),
            subtype_xmlid='mail.mt_note',
        )

        # Check if more pending levels remain
        next_pending = self.approval_line_ids.filtered(
            lambda l: l.state == 'pending'
        ).sorted('sequence')[:1]

        if next_pending:
            self._notify_approver(next_pending)
            self.message_post(
                body=_('Waiting for next approval level: <b>%s</b>.') % next_pending.level_name,
                subtype_xmlid='mail.mt_note',
            )
        else:
            self.approval_state = 'approved'
            self.message_post(
                body=_('All approval levels completed. The quotation is ready to be confirmed.'),
                subtype_xmlid='mail.mt_note',
            )
            # Notify the salesperson
            if self.user_id:
                self.message_post(
                    body=_('Your quotation <b>%s</b> has been fully approved and is ready to confirm.') % self.name,
                    partner_ids=[self.user_id.partner_id.id],
                    subtype_xmlid='mail.mt_comment',
                )

    def action_reject(self):
        self.ensure_one()
        if self.approval_state != 'pending':
            raise UserError(_('This quotation is not waiting for approval.'))

        me = self.env.user
        pending_lines = self.approval_line_ids.filtered(
            lambda l: l.state == 'pending'
        ).sorted('sequence')
        if not pending_lines:
            raise UserError(_('No pending approval level found.'))

        current_line = pending_lines[0]
        if not current_line.rule_id._user_can_approve(me):
            raise UserError(_(
                'You are not authorised to reject level "%s".'
            ) % current_line.level_name)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Quotation'),
            'res_model': 'sale.approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_line_id': current_line.id,
            },
        }

    def action_reset_approval(self):
        """Put the quotation back to draft (no approval state)."""
        self.ensure_one()
        self.approval_state = 'none'
        self.approval_line_ids.unlink()
        self.message_post(
            body=_('Approval reset. Quotation returned to draft.'),
            subtype_xmlid='mail.mt_note',
        )

    # ------------------------------------------------------------------
    # Override confirm — block if approval is pending or rejected
    # ------------------------------------------------------------------

    def action_confirm(self):
        for order in self:
            if order._get_matching_rules() and order.approval_state not in ('approved',):
                if order.approval_state == 'pending':
                    raise UserError(_(
                        'Quotation "%s" is waiting for approval. '
                        'It cannot be confirmed until all levels are approved.'
                    ) % order.name)
                if order.approval_state == 'rejected':
                    raise UserError(_(
                        'Quotation "%s" was rejected. Reset it to draft and resubmit for approval.'
                    ) % order.name)
                if order.approval_state == 'none':
                    raise UserError(_(
                        'Quotation "%s" requires approval before it can be confirmed. '
                        'Please click "Submit for Approval".'
                    ) % order.name)
        return super().action_confirm()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _notify_approver(self, approval_line):
        """Post a chatter message notifying the approver of this level."""
        partners = []
        if approval_line.approver_user_id:
            partners.append(approval_line.approver_user_id.partner_id.id)
        elif approval_line.approver_group_id:
            partners = approval_line.approver_group_id.users.mapped('partner_id').ids

        if partners:
            self.message_post(
                body=_(
                    'Your approval is required for quotation <b>%s</b> '
                    '(Level: <b>%s</b>). Amount: %s.'
                ) % (
                    self.name,
                    approval_line.level_name,
                    self.currency_id.symbol + ' ' + '{:,.2f}'.format(self.amount_untaxed),
                ),
                partner_ids=partners,
                subtype_xmlid='mail.mt_comment',
            )


class SaleApprovalRejectWizard(models.TransientModel):
    _name = 'sale.approval.reject.wizard'
    _description = 'Reject Quotation Approval'

    order_id = fields.Many2one('sale.order', required=True)
    line_id  = fields.Many2one('sale.approval.line', required=True)
    reason   = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        me = self.env.user
        self.line_id.write({
            'state': 'rejected',
            'approved_by': me.id,
            'decision_date': fields.Datetime.now(),
            'comment': self.reason,
        })
        # Mark all remaining pending lines as rejected too
        self.order_id.approval_line_ids.filtered(
            lambda l: l.state == 'pending'
        ).write({'state': 'rejected'})

        self.order_id.approval_state = 'rejected'
        self.order_id.message_post(
            body=_(
                'Quotation <b>rejected</b> at level <b>%s</b> by %s.<br/>'
                '<b>Reason:</b> %s'
            ) % (self.line_id.level_name, me.name, self.reason),
            subtype_xmlid='mail.mt_note',
        )
        # Notify salesperson
        if self.order_id.user_id:
            self.order_id.message_post(
                body=_(
                    'Your quotation <b>%s</b> was rejected at level <b>%s</b>.<br/>'
                    '<b>Reason:</b> %s'
                ) % (self.order_id.name, self.line_id.level_name, self.reason),
                partner_ids=[self.order_id.user_id.partner_id.id],
                subtype_xmlid='mail.mt_comment',
            )
        return {'type': 'ir.actions.act_window_close'}
