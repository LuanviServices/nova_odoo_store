from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarginCommissionScale(models.Model):
    _name = 'margin.commission.scale'
    _description = 'Margin-Based Commission Scale'

    name = fields.Char(string='Scale Name', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'margin.commission.scale.line', 'scale_id', string='Margin Brackets',
    )
    below_minimum_rate = fields.Float(
        string='Rate Below Minimum Margin (%)',
        default=0.0,
        help='Commission rate applied when the margin is below the lowest '
             'bracket (e.g. negative margin, sold at a loss). Usually 0.',
    )

    def _get_rate_for_margin(self, margin_pct):
        """Return the commission rate (%) for a given margin percentage,
        matching the bracket whose [min, max) range contains it."""
        self.ensure_one()
        lines = self.line_ids.sorted('margin_from')
        for line in lines:
            upper = line.margin_to if line.margin_to else float('inf')
            if line.margin_from <= margin_pct < upper:
                return line.commission_rate
        return self.below_minimum_rate


class MarginCommissionScaleLine(models.Model):
    _name = 'margin.commission.scale.line'
    _description = 'Margin Commission Bracket'
    _order = 'margin_from'

    scale_id = fields.Many2one(
        'margin.commission.scale', required=True, ondelete='cascade',
    )
    margin_from = fields.Float(
        string='Margin From (%)',
        required=True,
        help='Inclusive lower bound of this bracket.',
    )
    margin_to = fields.Float(
        string='Margin To (%)',
        help='Exclusive upper bound. Leave 0/empty for "and above".',
    )
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        required=True,
        help='Commission rate applied to the line subtotal when its '
             'margin falls in this bracket.',
    )

    @api.constrains('margin_from', 'margin_to')
    def _check_range(self):
        for line in self:
            if line.margin_to and line.margin_to <= line.margin_from:
                raise ValidationError(
                    'The "Margin To" must be greater than "Margin From" '
                    'for bracket starting at %.1f%%.' % line.margin_from
                )
