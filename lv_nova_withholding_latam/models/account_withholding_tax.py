from odoo import api, fields, models


class AccountWithholdingTax(models.Model):
    _name = 'account.withholding.tax'
    _description = 'Withholding Tax Type'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(
        string='Code',
        help='Legal/fiscal code used by the tax authority (e.g. "303", "1%").',
    )
    percent = fields.Float(string='Percentage', required=True, digits=(5, 2))
    move_type = fields.Selection(
        [
            ('sale', 'Customer Invoices (withheld by the customer)'),
            ('purchase', 'Vendor Bills (withheld by us)'),
            ('both', 'Both'),
        ],
        string='Applies To',
        required=True,
        default='both',
    )
    account_id = fields.Many2one(
        'account.account',
        string='Withholding Account',
        required=True,
        help='Account used to post the withheld amount: an asset account '
             'for customer invoices (tax credit) or a liability account '
             'for vendor bills (amount owed to the tax authority).',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'percent_range',
            'CHECK(percent >= 0 AND percent <= 100)',
            'The withholding percentage must be between 0 and 100.',
        ),
    ]

    def name_get(self):
        result = []
        for tax in self:
            label = tax.name
            if tax.code:
                label = '[%s] %s (%s%%)' % (tax.code, tax.name, tax.percent)
            else:
                label = '%s (%s%%)' % (tax.name, tax.percent)
            result.append((tax.id, label))
        return result
