from odoo import api, fields, models


class SaleCommissionPlan(models.Model):
    _name = 'sale.commission.plan'
    _description = 'Sales Commission Plan'

    name = fields.Char(string='Plan Name', required=True)
    basis = fields.Selection(
        [
            ('order_confirm', 'On Order Confirmation'),
            ('invoice_payment', 'On Invoice Payment'),
        ],
        string='Trigger',
        required=True,
        default='invoice_payment',
        help='When the commission lines are generated: as soon as the '
             'sale order is confirmed, or only once the related invoice '
             'has been fully paid.',
    )
    calc_method = fields.Selection(
        [
            ('subtotal', 'Percentage of Subtotal'),
            ('margin', 'Percentage of Margin'),
        ],
        string='Calculation Method',
        required=True,
        default='subtotal',
    )
    default_rate = fields.Float(
        string='Default Rate (%)',
        default=5.0,
        help='Rate applied to products that do not match any category '
             'rule below.',
    )
    line_ids = fields.One2many(
        'sale.commission.plan.line', 'plan_id', string='Category Rates',
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    def _get_rate_for_product(self, product):
        """Return the commission rate (%) that applies to a given product,
        matching the most specific category rule, falling back to the
        plan's default rate."""
        self.ensure_one()
        category = product.categ_id
        for line in self.line_ids:
            if line.category_id and category and (
                category.id == line.category_id.id
                or category.parent_path.startswith(line.category_id.parent_path)
            ):
                return line.rate
        return self.default_rate


class SaleCommissionPlanLine(models.Model):
    _name = 'sale.commission.plan.line'
    _description = 'Sales Commission Plan — Category Rate'
    _order = 'sequence'

    plan_id = fields.Many2one(
        'sale.commission.plan', string='Plan', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        required=True,
        help='Applies to this category and its sub-categories.',
    )
    rate = fields.Float(string='Rate (%)', required=True)
