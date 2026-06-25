import io
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    _logger.warning(
        'lv_nova_product_label: qrcode library not found. '
        'QR codes will be skipped. Install with: pip install qrcode[pil]'
    )


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

class ProductLabelWizard(models.TransientModel):
    _name = 'product.label.wizard'
    _description = 'Product Label Print Wizard'

    line_ids = fields.One2many(
        'product.label.wizard.line', 'wizard_id', string='Products',
    )

    # -- Label size ----------------------------------------------------------
    label_size = fields.Selection(
        [
            ('70x36',  '70 × 36 mm  (2 per row, standard)'),
            ('48x30',  '48 × 30 mm  (4 per row, small)'),
            ('100x50', '100 × 50 mm (2 per row, large)'),
        ],
        string='Label Size',
        required=True,
        default='70x36',
    )

    # -- Fields to show on each label ----------------------------------------
    show_name       = fields.Boolean(string='Product Name',  default=True)
    show_reference  = fields.Boolean(string='Internal Ref.', default=True)
    show_price      = fields.Boolean(string='Sale Price',    default=True)
    show_category   = fields.Boolean(string='Category',      default=False)
    show_lot        = fields.Boolean(string='Lot / Serial #', default=True)
    show_barcode    = fields.Boolean(string='Barcode (text)', default=True)
    show_qr         = fields.Boolean(string='QR Code',       default=True)

    # -- QR content ----------------------------------------------------------
    qr_content = fields.Selection(
        [
            ('barcode',    'Barcode / Internal Reference'),
            ('name',       'Product Name'),
            ('both',       'Barcode + Name'),
        ],
        string='QR Content',
        default='barcode',
        required=True,
    )

    # -- Computed helpers for template ---------------------------------------
    label_width_mm  = fields.Float(compute='_compute_label_dims')
    label_height_mm = fields.Float(compute='_compute_label_dims')
    cols_per_row    = fields.Integer(compute='_compute_label_dims')

    @api.depends('label_size')
    def _compute_label_dims(self):
        dims = {
            '70x36':  (70.0, 36.0, 2),
            '48x30':  (48.0, 30.0, 4),
            '100x50': (100.0, 50.0, 2),
        }
        for wiz in self:
            w, h, c = dims.get(wiz.label_size, (70.0, 36.0, 2))
            wiz.label_width_mm  = w
            wiz.label_height_mm = h
            wiz.cols_per_row    = c

    # -- Population helpers --------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        lines = []

        # From product.product or product.template list
        if ctx.get('active_model') in ('product.product', 'product.template'):
            product_model = ctx['active_model']
            for pid in ctx.get('active_ids', []):
                record = self.env[product_model].browse(pid)
                if product_model == 'product.template':
                    products = record.product_variant_ids
                else:
                    products = record
                for prod in products:
                    lines.append({
                        'product_id': prod.id,
                        'qty': 1,
                    })

        # From purchase.order
        elif ctx.get('active_model') == 'purchase.order':
            po = self.env['purchase.order'].browse(ctx.get('active_id', 0))
            for line in po.order_line.filtered(lambda l: l.product_id):
                lines.append({
                    'product_id': line.product_id.id,
                    'qty': int(line.product_qty) or 1,
                })

        # From stock.picking (delivery / receipt)
        elif ctx.get('active_model') == 'stock.picking':
            picking = self.env['stock.picking'].browse(ctx.get('active_id', 0))
            for move in picking.move_ids.filtered(lambda m: m.product_id):
                lines.append({
                    'product_id': move.product_id.id,
                    'qty': int(move.product_uom_qty) or 1,
                    'lot_id': move.lot_ids[:1].id if move.lot_ids else False,
                })

        if lines and 'line_ids' in fields_list:
            res['line_ids'] = [(0, 0, v) for v in lines]
        return res

    # -- Print action --------------------------------------------------------

    def action_print_labels(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Add at least one product line before printing.'))
        # Generate QR images for all lines
        self.line_ids._generate_qr(self.qr_content, self.show_qr)
        return self.env.ref(
            'lv_nova_product_label.action_report_product_label'
        ).report_action(self)

    def get_expanded_lines(self):
        """
        Returns a flat list of dicts, one entry per physical label to print.
        Each line with qty=3 becomes 3 dict entries.
        Used from the QWeb template.
        """
        result = []
        for line in self.line_ids:
            for _ in range(max(1, int(line.qty))):
                result.append(line)
        return result


# ---------------------------------------------------------------------------
# Wizard line
# ---------------------------------------------------------------------------

class ProductLabelWizardLine(models.TransientModel):
    _name = 'product.label.wizard.line'
    _description = 'Product Label Wizard Line'
    _order = 'sequence, id'

    wizard_id  = fields.Many2one('product.label.wizard', ondelete='cascade')
    sequence   = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty        = fields.Integer(string='Copies', default=1,
                                help='How many labels to print for this product.')
    lot_id     = fields.Many2one('stock.lot', string='Lot / Serial',
                                 domain="[('product_id','=',product_id)]")
    custom_price = fields.Float(string='Custom Price', digits='Product Price',
                                help='Leave 0 to use the product\'s sale price.')

    # Computed display helpers (non-stored)
    display_price    = fields.Float(compute='_compute_display_fields')
    display_barcode  = fields.Char(compute='_compute_display_fields')
    display_category = fields.Char(compute='_compute_display_fields')
    qr_image_b64     = fields.Char(string='QR Image (base64)')

    @api.depends('product_id', 'custom_price')
    def _compute_display_fields(self):
        for line in self:
            line.display_price = line.custom_price or line.product_id.list_price
            line.display_barcode = (
                line.product_id.barcode
                or line.product_id.default_code
                or ''
            )
            line.display_category = (
                line.product_id.categ_id.complete_name
                if line.product_id.categ_id else ''
            )

    def _generate_qr(self, qr_content_type, show_qr):
        """Generate and store QR code base64 for each line."""
        for line in self:
            if not show_qr or not HAS_QRCODE:
                line.qr_image_b64 = False
                continue
            product = line.product_id
            if qr_content_type == 'barcode':
                data = product.barcode or product.default_code or product.name
            elif qr_content_type == 'name':
                data = product.name
            else:  # both
                ref = product.barcode or product.default_code or ''
                data = '{} | {}'.format(ref, product.name) if ref else product.name

            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=6,
                    border=2,
                )
                qr.add_data(data)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                line.qr_image_b64 = base64.b64encode(buf.getvalue()).decode()
            except Exception as e:
                _logger.warning('QR generation failed for %s: %s', product.name, e)
                line.qr_image_b64 = False
