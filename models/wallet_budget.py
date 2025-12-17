# © 2025 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0
import random
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class WalletBudgetTag(models.Model):
    _name = 'wallet.budget.tag'
    _description = 'Budget Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(default=lambda self: self._get_random_color())

    @api.model
    def _get_random_color(self):
        return random.randint(1, 10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('color'):
                vals['color'] = self._get_random_color()
        return super().create(vals_list)


class WalletBudgetPlan(models.Model):
    _name = 'wallet.budget.plan'
    _description = 'Wallet Budget Planification'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_name(self):
        return _('Budget Plan %s') % fields.Date.today().year

    name = fields.Char(string='Budget Name', required=True, default=lambda self:  self._get_name())
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    start_date = fields.Date(required=True, help='Start date of the budget plan')
    end_date = fields.Date(required=True, help='End date must be after start date')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('wallet.budget.plan.line', 'plan_id', string='Budget Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('closed', 'Closed'),
    ], string='Status', default='draft')
    tag_ids = fields.Many2many('wallet.budget.tag', string='Tags')
    color = fields.Integer(default=lambda self: self.env['wallet.budget.tag']._get_random_color())
    ref = fields.Char(string='Reference', help='Unique reference for the budget plan')


class WalletBudgetPLanLine(models.Model):
    _name = 'wallet.budget.plan.line'
    _description = 'Wallet Budget Plan Line'

    plan_id = fields.Many2one('wallet.budget.plan', string='Budget Plan', required=True)
    category_id = fields.Many2one('wallet.category', string='Category', required=True)
    assigned_amount = fields.Monetary(string='Assigned Amount', required=True)
    committed_amount = fields.Monetary(string='Committed Amount', default=0.0)
    executed_amount = fields.Monetary(string='Executed Amount', default=0.0)
    available_amount = fields.Monetary(string='Available Amount', compute='_compute_available_amount', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='plan_id.currency_id', string='Currency', store=True, readonly=True)

    def _compute_available_amount(self):
        for line in self:
            line.amount_available = 0.00


class WalletBudgetPlanOperation(models.Model):
    _name = 'wallet.budget.plan.operation'
    _description = 'Wallet Budget Operations'

    name = fields.Char(string='Operation Reference')
    date = fields.Date(string='Operation Date', default=fields.Date.context_today)
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    operation_type = fields.Selection([
        ('expense', 'Expense'),
        ('income', 'Income'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Adjustment'),
    ], string='Operation Type', required=True)
    budget_line_id = fields.Many2one('wallet.budget.plan.line', string='Budget Line', required=True)
    transaction_id = fields.Many2one('wallet.transaction', string='Related Transaction')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
