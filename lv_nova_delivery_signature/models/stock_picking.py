import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ------------------------------------------------------------------
    # Signature fields
    # ------------------------------------------------------------------

    delivery_signature = fields.Image(
        string='Delivery Signature',
        max_width=600,
        max_height=300,
        help='Touch or mouse signature captured on delivery.',
        copy=False,
    )
    signed_by = fields.Char(
        string='Signed By',
        help='Name of the person who signed (customer, driver, etc.).',
        copy=False,
    )
    signature_date = fields.Datetime(
        string='Signature Date',
        readonly=True,
        copy=False,
    )
    is_signed = fields.Boolean(
        string='Signed',
        compute='_compute_is_signed',
        store=True,
    )
    signature_required = fields.Boolean(
        string='Signature Required',
        related='picking_type_id.signature_required',
        readonly=True,
        store=False,
    )

    @api.depends('delivery_signature')
    def _compute_is_signed(self):
        for picking in self:
            picking.is_signed = bool(picking.delivery_signature)

    # ------------------------------------------------------------------
    # Record signature date on write
    # ------------------------------------------------------------------

    def write(self, vals):
        if vals.get('delivery_signature') and not vals.get('signature_date'):
            vals['signature_date'] = fields.Datetime.now()
        result = super().write(vals)
        # Log in chatter when signature is added
        if vals.get('delivery_signature'):
            for picking in self:
                signed_by_txt = (
                    _(' — signed by %s') % picking.signed_by
                    if picking.signed_by else ''
                )
                picking.message_post(
                    body=_(
                        'Delivery signature captured on %s%s.'
                    ) % (
                        str(fields.Datetime.now())[:19],
                        signed_by_txt,
                    ),
                    subtype_xmlid='mail.mt_note',
                )
        return result

    # ------------------------------------------------------------------
    # Override validate — block if signature is required but missing
    # ------------------------------------------------------------------

    def button_validate(self):
        for picking in self:
            if (
                picking.picking_type_id.signature_required
                and not picking.delivery_signature
                and picking.state not in ('done', 'cancel')
            ):
                raise UserError(_(
                    'A delivery signature is required for operation type '
                    '"%s" before this transfer can be validated.\n\n'
                    'Please capture the signature in the "Delivery Signature" '
                    'section before confirming.'
                ) % picking.picking_type_id.name)
        return super().button_validate()

    # ------------------------------------------------------------------
    # Helper: base64 for QWeb template
    # ------------------------------------------------------------------

    def _get_signature_b64(self):
        """Return the signature as a data URI string for embedding in PDF."""
        self.ensure_one()
        if not self.delivery_signature:
            return False
        img_b64 = self.delivery_signature
        if isinstance(img_b64, bytes):
            img_b64 = img_b64.decode()
        return 'data:image/png;base64,%s' % img_b64
