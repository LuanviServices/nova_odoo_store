from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ------------------------------------------------------------------
    # Approval fields
    # ------------------------------------------------------------------

    transfer_approval_state = fields.Selection(
        [
            ('not_required', 'Not Required'),
            ('pending',      'Waiting Approval'),
            ('approved',     'Approved'),
            ('rejected',     'Rejected'),
        ],
        string='Approval Status',
        default='not_required',
        copy=False,
        tracking=True,
    )
    transfer_approval_required = fields.Boolean(
        string='Approval Required',
        compute='_compute_transfer_approval_required',
        store=True,
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved / Rejected By',
        readonly=True, copy=False,
    )
    approval_date = fields.Datetime(
        string='Decision Date', readonly=True, copy=False,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason', readonly=True, copy=False,
    )
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        compute='_compute_dest_warehouse',
        store=True,
    )
    current_user_can_approve = fields.Boolean(
        compute='_compute_current_user_can_approve',
    )

    # ------------------------------------------------------------------
    # Compute helpers
    # ------------------------------------------------------------------

    @api.depends('location_dest_id')
    def _compute_dest_warehouse(self):
        for picking in self:
            picking.dest_warehouse_id = (
                picking.location_dest_id.warehouse_id
                if picking.location_dest_id else False
            )

    @api.depends(
        'picking_type_code',
        'dest_warehouse_id',
        'dest_warehouse_id.transfer_approval_required',
    )
    def _compute_transfer_approval_required(self):
        for picking in self:
            picking.transfer_approval_required = (
                picking.picking_type_code == 'internal'
                and bool(
                    picking.dest_warehouse_id
                    and picking.dest_warehouse_id.transfer_approval_required
                )
            )

    @api.depends(
        'transfer_approval_state',
        'dest_warehouse_id.transfer_approver_id',
    )
    def _compute_current_user_can_approve(self):
        me = self.env.user
        stock_manager = self.env.ref(
            'stock.group_stock_manager', raise_if_not_found=False
        )
        is_manager = stock_manager and me in stock_manager.users

        for picking in self:
            if picking.transfer_approval_state != 'pending':
                picking.current_user_can_approve = False
                continue
            approver = picking.dest_warehouse_id.transfer_approver_id
            if approver:
                picking.current_user_can_approve = (me == approver)
            else:
                # Any stock manager can approve when no specific approver
                picking.current_user_can_approve = is_manager

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_submit_transfer_for_approval(self):
        """Submits the internal transfer for approval and notifies approver."""
        self.ensure_one()
        if not self.transfer_approval_required:
            raise UserError(_(
                'Approval is not required for this transfer.'
            ))
        if self.transfer_approval_state == 'approved':
            raise UserError(_('This transfer is already approved.'))

        self.write({
            'transfer_approval_state': 'pending',
            'rejection_reason':        False,
            'approved_by':             False,
            'approval_date':           False,
        })

        # Notify approver(s)
        approver = self.dest_warehouse_id.transfer_approver_id
        if approver and approver.partner_id:
            partners = [approver.partner_id.id]
        else:
            # Notify all stock managers
            stock_manager = self.env.ref(
                'stock.group_stock_manager', raise_if_not_found=False
            )
            partners = (stock_manager.users.mapped('partner_id').ids
                        if stock_manager else [])

        self.message_post(
            body=_(
                'Transfer <b>%s</b> has been submitted for approval '
                'by <b>%s</b>.<br/>'
                'From: <b>%s</b> → To: <b>%s</b>'
            ) % (
                self.name,
                self.env.user.name,
                self.location_id.complete_name,
                self.location_dest_id.complete_name,
            ),
            partner_ids=partners,
            subtype_xmlid='mail.mt_comment',
        )
        return True

    def action_approve_transfer(self):
        """Approves the transfer and notifies the requester."""
        self.ensure_one()
        if not self.current_user_can_approve:
            raise UserError(_(
                'You are not authorised to approve this transfer.'
            ))
        self.write({
            'transfer_approval_state': 'approved',
            'approved_by':             self.env.user.id,
            'approval_date':           fields.Datetime.now(),
            'rejection_reason':        False,
        })
        # Notify the person who wrote the last message (requester)
        self.message_post(
            body=_(
                'Transfer <b>%s</b> has been <b style="color:green;">approved</b> '
                'by %s. You can now validate the transfer.'
            ) % (self.name, self.env.user.name),
            subtype_xmlid='mail.mt_note',
        )
        return True

    def action_reject_transfer(self):
        """Opens the reject wizard."""
        self.ensure_one()
        if not self.current_user_can_approve:
            raise UserError(_(
                'You are not authorised to reject this transfer.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Transfer'),
            'res_model': 'stock.transfer.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }

    def action_reset_transfer_approval(self):
        """Resets to Not Required / draft so it can be resubmitted."""
        self.ensure_one()
        self.write({
            'transfer_approval_state': 'pending'
            if self.transfer_approval_required else 'not_required',
            'approved_by':             False,
            'approval_date':           False,
            'rejection_reason':        False,
        })
        # Set back to pending so the requester resubmits
        self.write({'transfer_approval_state': 'not_required'})
        self.message_post(
            body=_('Approval reset by %s.') % self.env.user.name,
            subtype_xmlid='mail.mt_note',
        )

    # ------------------------------------------------------------------
    # Override validate — block if pending approval or rejected
    # ------------------------------------------------------------------

    def button_validate(self):
        for picking in self:
            if not picking.transfer_approval_required:
                continue
            if picking.transfer_approval_state == 'pending':
                raise UserError(_(
                    'Transfer "%s" is waiting for approval from the '
                    'destination warehouse manager. '
                    'It cannot be validated until approved.'
                ) % picking.name)
            if picking.transfer_approval_state == 'rejected':
                raise UserError(_(
                    'Transfer "%s" was rejected. '
                    'Please reset it and resubmit for approval.'
                ) % picking.name)
            if picking.transfer_approval_state == 'not_required':
                # Automatically submit + approve if no prior action taken
                # (e.g. the approval setting was turned on after the PO)
                raise UserError(_(
                    'Transfer "%s" requires approval before validation. '
                    'Please click "Submit for Approval" first.'
                ) % picking.name)
        return super().button_validate()
