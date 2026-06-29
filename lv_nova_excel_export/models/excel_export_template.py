from odoo import api, fields, models


class ExcelExportTemplate(models.Model):
    _name = 'excel.export.template'
    _description = 'Excel Export Template'
    _order = 'model_id, name'

    name = fields.Char(string='Template Name', required=True)
    model_id = fields.Many2one(
        'ir.model', string='Model', required=True,
        domain=[('transient', '=', False)],
        ondelete='cascade',
    )
    model_name = fields.Char(related='model_id.model', store=True)
    sheet_title = fields.Char(
        string='Sheet Title',
        help='Title printed at the top of the Excel sheet. '
             'Leave empty to use the template name.',
    )
    include_company_header = fields.Boolean(
        string='Company Name Header', default=True,
    )
    freeze_header = fields.Boolean(
        string='Freeze Header Row', default=True,
    )
    alternating_rows = fields.Boolean(
        string='Alternating Row Colours', default=True,
    )
    header_bg_color = fields.Char(
        string='Header Background',
        default='1F4E79',
        help='Hex colour without #, e.g. 1F4E79',
    )
    header_font_color = fields.Char(
        string='Header Font',
        default='FFFFFF',
    )
    alt_row_color = fields.Char(
        string='Alternate Row Color',
        default='DDEEFF',
        help='Light colour for every other data row.',
    )
    line_ids = fields.One2many(
        'excel.export.template.line', 'template_id', string='Columns',
    )
    active = fields.Boolean(default=True)


class ExcelExportTemplateLine(models.Model):
    _name = 'excel.export.template.line'
    _description = 'Excel Export Template Column'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'excel.export.template', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    field_name = fields.Char(
        string='Field / Path',
        required=True,
        help='Field name (e.g. "name") or dotted path (e.g. "partner_id.name"). '
             'Use "display_name" for the record label.',
    )
    header = fields.Char(
        string='Column Header',
        help='Leave empty to use the field label.',
    )
    width = fields.Integer(
        string='Column Width',
        default=20,
        help='Column width in Excel character units. 0 = auto-fit.',
    )
    fmt = fields.Selection(
        [
            ('text',       'Text'),
            ('integer',    'Integer'),
            ('float',      'Number (2 dec)'),
            ('monetary',   'Monetary'),
            ('date',       'Date'),
            ('datetime',   'Date + Time'),
            ('percentage', 'Percentage'),
            ('boolean',    'Yes / No'),
        ],
        string='Format',
        default='text',
    )
    total = fields.Boolean(
        string='Sum in Footer',
        default=False,
        help='Include this column in the totals row at the bottom.',
    )
    bold = fields.Boolean(string='Bold', default=False)

    @api.onchange('field_name', 'template_id')
    def _onchange_field_name(self):
        """Auto-fill header from field label when field_name changes."""
        if self.field_name and self.template_id and self.template_id.model_id:
            model = self.template_id.model_id.model
            field_path = self.field_name.split('.')
            try:
                model_obj = self.env[model]
                for part in field_path[:-1]:
                    field = model_obj._fields.get(part)
                    if field and hasattr(field, 'comodel_name'):
                        model_obj = self.env[field.comodel_name]
                    else:
                        break
                last_field = model_obj._fields.get(field_path[-1])
                if last_field and not self.header:
                    self.header = last_field.string or field_path[-1].replace('_', ' ').title()
                # Auto-detect format
                if last_field and not self.fmt or self.fmt == 'text':
                    ftype = last_field.type
                    if ftype in ('float',):
                        self.fmt = 'float'
                    elif ftype in ('monetary',):
                        self.fmt = 'monetary'
                    elif ftype in ('date',):
                        self.fmt = 'date'
                    elif ftype in ('datetime',):
                        self.fmt = 'datetime'
                    elif ftype in ('integer',):
                        self.fmt = 'integer'
                    elif ftype in ('boolean',):
                        self.fmt = 'boolean'
            except Exception:
                pass
