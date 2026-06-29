from odoo import fields, models, _


class StockTransferRejectWizard(models.TransientModel):
    _name = 'stock.transfer.reject.wizard'
    _description = 'Reject Transfer Wizard'

    picking_id = fields.Many2one(
        'stock.picking', string='Transfer', required=True,
    )
    reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Explain why this transfer request is being rejected. '
             'This message will be visible to the requester.',
    )

    def action_confirm_reject(self):
        self.ensure_one()
        picking = self.picking_id
        me = self.env.user

        picking.write({
            'transfer_approval_state': 'rejected',
            'approved_by':             me.id,
            'approval_date':           fields.Datetime.now(),
            'rejection_reason':        self.reason,
        })
        picking.message_post(
            body=_(
                'Transfer <b>%s</b> has been <b style="color:red;">rejected</b> '
                'by %s.<br/><b>Reason:</b> %s'
            ) % (picking.name, me.name, self.reason),
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}
