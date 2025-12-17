# -*- coding: utf-8 -*-
# © 2024 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0
from random import randint
from odoo import api, fields, models, _
from . import wallet
from datetime import date
import calendar
from odoo.exceptions import ValidationError

account_types = [('general', 'General'), ('cash', 'Cash'), ('bank', 'Bank'), ('credit_card', 'Credit card'),
                 ('savings', 'Savings'), ('investments', 'Investments')]


class WalletAccount(models.Model):
    _name = 'wallet.account'
    _description = 'Account Wallet'
    _order = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    name = fields.Char(required=True, tracking=True)
    account_type = fields.Selection(account_types, required=True, tracking=True)
    bank_id = fields.Many2one('res.bank', tracking=True, help='Bank to which this account is related')
    bank_number = fields.Char(tracking=True)
    card_number = fields.Char(tracking=True)
    amount = fields.Monetary(default=0.00, currency_field='company_currency_id')
    amount_allocated = fields.Monetary(default=0.00, currency_field='company_currency_id')
    amount_available = fields.Monetary(default=0.00, currency_field='company_currency_id',
                                       compute='_compute_amount_available', readonly=True, store=True)
    color = fields.Integer('Color Index')
    account_tag = fields.Html(compute='_compute_account_tag')
    cutoff_day = fields.Integer(tracking=True)
    next_cutoff_date = fields.Date(
        string="Next cut-off date",
        compute="_compute_next_cutoff_date",
        store=True
    )
    cutoff_day_color = fields.Selection(
        [
            ('1', 'Blue'),
            ('2', 'Yellow'),
            ('3', 'Red'),
        ],
        compute='_compute_cutoff_day_color',
        string="Cutoff Color",
        store=False,
    )
    active = fields.Boolean(default=True)
    image = fields.Image()
    permissions_ids = fields.One2many('wallet.account.permission', 'account_id', string="User Permissions")
    is_propietary = fields.Boolean(
        string="Is Propietary",
        compute="_compute_is_propietary",
        store=False
    )
    can_transact = fields.Boolean(
        string='You can transact',
        compute='_compute_can_transact',
        store=True,
    )
    share_available_users = fields.Many2many(
        'res.users',
        string='Share Available Users',
        compute='_compute_share_available_users'
    )
    show_panel = fields.Boolean(
        string='Show Panel',
        default=True,
        tracking=True
    )

    @api.depends('create_uid')
    def _compute_share_available_users(self):
        for rec in self:
            # Todos los usuarios menos el creador
            rec.share_available_users = self.env['res.users'].search([('id', '!=', rec.create_uid.id)])
    
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        # Solo aplica si el usuario quiere crear un nuevo registro
        if 'is_propietary' not in fields_list:
            vals['is_propietary'] = True
        if 'can_transact' not in fields_list:
            vals['can_transact'] = True
        return vals
    
    def _compute_is_propietary(self):
        current_user = self.env.user
        for rec in self:
            rec.is_propietary = (rec.create_uid == current_user)
            
    @api.depends('company_id', 'permissions_ids.user_id', 'permissions_ids.permission_type')
    def _compute_can_transact(self):
        user = self.env.user
        for rec in self:
            # si la compañía coincide
            if rec.company_id == user.company_id:
                rec.can_transact = True
                continue
            # sino coincide, validar permisos especiales
            has_permission = rec.permissions_ids.filtered(
                lambda p: p.user_id == user and p.type == 'transaccional'
            )
            rec.can_transact = bool(has_permission)
    
    @api.constrains('cutoff_day')
    def _check_cutoff_day(self):
        for record in self:
            if record.account_type == 'credit_card':
                if record.cutoff_day < 1 or record.cutoff_day > 31:
                    raise ValidationError(_("The cut-off day must be between 1 and 31."))
            
    @api.depends('cutoff_day')
    def _compute_next_cutoff_date(self):
        today = date.today()
        for record in self:
            if not record.cutoff_day:
                record.next_cutoff_date = False
                continue
            year = today.year
            month = today.month
            if today.day > record.cutoff_day:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            days_in_month = calendar.monthrange(year, month)[1]
            day = min(record.cutoff_day, days_in_month)
            record.next_cutoff_date = date(year, month, day)
            
    @api.depends('next_cutoff_date')
    def _compute_cutoff_day_color(self):
        today = date.today()
        for record in self:
            if not record.next_cutoff_date:
                record.cutoff_day_color = False
                continue
            days_left = (record.next_cutoff_date - today).days
            if days_left > 3:
                record.cutoff_day_color = '1'
            elif 1 <= days_left <= 3:
                record.cutoff_day_color = '2'
            else:
                record.cutoff_day_color = '3'
                
    @api.depends('amount')
    def _compute_amount_available(self):
        for record in self:
            record.amount_available = 0.00
            if record.amount_allocated:
                record.amount_available = record.amount_allocated - abs(record.amount)

    def cron_update_next_cutoff_dates(self):
        """Método que ejecutará el cron todos los días."""
        records = self.search([])
        for record in records:
            record._compute_next_cutoff_date()

    @api.depends('color', 'name')
    def _compute_account_tag(self):
        for account in self:
            account.account_tag = ''
            if account.name:
                account.account_tag = (
                    f'<span class="o_badge badge rounded-pill o_tag o_tag_color_{account.color}">'
                    f'{account.name}</span>'
                )

    @api.model
    def _fetch_query(self, query, fields):
        records = super(WalletAccount, self)._fetch_query(query, fields)
        for account in records:
            total = 0.0
            transactions = self.env['wallet.transaction'].search([('wallet_account', '=', account.id)])
            total += sum(transactions.mapped('amount_total'))
            account['amount'] = total
        return records

    @api.onchange('card_number', 'bank_number')
    def _onchange_anonymize_numbers(self):
        if self.card_number and len(self.card_number) > 8:
            self.card_number = 'X' * (len(self.card_number) - 4) + self.card_number[-4:]
        if self.bank_number:
            if len(self.bank_number) > 8:
                self.bank_number = self.bank_number[:4] + 'X' * (len(self.bank_number) - 8) + self.bank_number[-4:]
            else:
                self.bank_number = self.bank_number[:2] + 'X' * (len(self.bank_number) - 3) + self.bank_number[-2:]

    @api.onchange('bank_id')
    def onchange_bank_id(self):
        if not self.name and self.bank_id:
            self.name = _('Account - %s') % (self.bank_id.name)

    def action_view_transactions_all(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions',
            'res_model': 'wallet.transaction',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('lv_personal_wallet.view_wallet_transaction_tree').id, 'list'),
                (self.env.ref('lv_personal_wallet.view_wallet_transaction_form').id, 'form'),
            ],
            'domain': [('wallet_account', '=', self.id)],
            'context': {
                'default_wallet_account': self.id,
            },
        }

    def action_view_transactions_income(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions',
            'res_model': 'wallet.transaction',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('lv_personal_wallet.view_wallet_transaction_income_tree').id, 'list'),
                (self.env.ref('lv_personal_wallet.view_wallet_transaction_income_form').id, 'form'),
            ],
            'domain': [('wallet_account', '=', self.id), ('transaction_type', '=', 'income')],
            'context': {
                'default_wallet_account': self.id,
                'default_transaction_type': 'income',
            },
        }

    def action_view_transactions_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions',
            'res_model': 'wallet.transaction',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('lv_personal_wallet.view_wallet_transaction_expense_tree').id, 'list'),
                (self.env.ref('lv_personal_wallet.view_wallet_transaction_expense_form').id, 'form'),
            ],
            'domain': [('wallet_account', '=', self.id), ('transaction_type', '=', 'expense')],
            'context': {
                'default_wallet_account': self.id,
                'default_transaction_type': 'expense',
            },
        }
        
    def action_open_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Wallet Account',
            'res_model': 'wallet.account',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

class WalletAccountPermission(models.Model):
    _name = 'wallet.account.permission'
    _description = 'Wallet Account Permission'
    _order = "user_id"

    account_id = fields.Many2one(
        'wallet.account',
        string="Wallet Account",
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True
    )
    permission_type = fields.Selection(
        [
            ('view', 'View only'),
            ('transaction', 'Allows transactions'),
        ],
        string="Type of permission",
        required=True,
        default='view'
    )

    _sql_constraints = [('unique_user_account', 'unique(account_id, user_id)', 'The user already has permissions configured for this account.')]

class WalletCategory(models.Model):
    _name = 'wallet.category'
    _description = 'Category Wallet'
    _parent_store = True
    _order = "complete_name"

    name = fields.Char(required=True, translate=True)
    complete_name = fields.Char(compute='_compute_complete_name', recursive=True, store=True)
    parent_id = fields.Many2one('wallet.category', string='Parent Category', index=True, ondelete="cascade")
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('wallet.category', 'parent_id', string='Children Categories', readonly=True)
    parents_and_self = fields.Many2many('wallet.category', compute='_compute_parents_and_self')
    color = fields.Integer('Color Index')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            name_translated = category.with_context(lang=self.env.user.lang).name
            if category.parent_id:
                parent_name_translated = category.parent_id.with_context(lang=self.env.user.lang).complete_name
                category.complete_name = '%s / %s' % (parent_name_translated, name_translated)
            else:
                category.complete_name = name_translated

    @api.constrains('parent_id')
    def check_parent_id(self):
        if self._has_cycle():
            raise ValueError(_('Error! You cannot create recursive categories.'))

    @api.depends('parents_and_self')
    def _compute_display_name(self):
        for category in self:
            category.display_name = " / ".join(category.parents_and_self.mapped(
                lambda cat: cat.name or _("New")
            ))

    @api.depends('parent_path')
    def _compute_parents_and_self(self):
        for category in self:
            if category.parent_path:
                category.parents_and_self = self.env['wallet.category'].browse([int(p) for p in category.parent_path.split('/')[:-1]])
            else:
                category.parents_and_self = category


class WalletTag(models.Model):
    _name = 'wallet.tag'
    _description = 'Tag Wallet'
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
                                 default=lambda self: self.env.company)
    name = fields.Char(required=True)
    color = fields.Integer('Color Index', default=_get_default_color)
    active = fields.Boolean(default=True)


class WalletTemplate(models.Model):
    _name = 'wallet.template'
    _description = 'Template Wallet'
    _oder = "name"

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    name = fields.Char(required=True)
    description = fields.Char(required=True)
    amount = fields.Monetary(default=0.00, currency_field='company_currency_id')
    wallet_account = fields.Many2one('wallet.account', required=True)
    category = fields.Many2one('wallet.category', required=True)
    payment_method = fields.Selection(wallet.payment_types, required=True)
    tag = fields.Many2one('wallet.tag')
    transaction_type = fields.Selection(wallet.transaction_types, required=True)
    beneficiary_id = fields.Many2one('res.partner')
    active = fields.Boolean(default=True)

notification_list = [('none', 'None'), ('deadline', 'Deadline'), ('one_day_before', 'One day before'),
                     ('three_day_before', 'Three day before'), ('one_week_before', 'One week before')
                     ]
periodicity_list = [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('annually', 'Annually')]


class WalletScheduledPayment(models.Model):
    _name = 'wallet.scheduled.payment'
    _description = 'Scheduled Payment Wallet'
    _order = "name"

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    name = fields.Char(required=True)
    category = fields.Many2one('wallet.category', required=True)
    tag = fields.Many2many('wallet.tag', 'wallet_scheduledpayment_tag_rel', 'transaction_id', 'tag_id')
    wallet_account = fields.Many2one('wallet.account', required=True)
    payment_method = fields.Selection(wallet.payment_types, required=True)
    beneficiary_id = fields.Many2one('res.partner')
    description = fields.Char(required=True)
    transaction_type = fields.Selection(wallet.transaction_types, required=True)
    start_date = fields.Date(required=True)
    notifications = fields.Selection(notification_list)
    periodicity = fields.Selection(periodicity_list)
    tax_ids = fields.One2many('wallet.scheduled.payment.tax', 'payment_id', string='Taxes')
    amount = fields.Monetary(default=0.00, currency_field='company_currency_id')
    amount_tax = fields.Monetary(compute='_compute_amounts', store=True, currency_field='company_currency_id')
    amount_total = fields.Monetary(compute='_compute_amounts', store=True, currency_field='company_currency_id')
    active = fields.Boolean(default=True)

    @api.depends('amount', 'tax_ids.amount')
    def _compute_amounts(self):
        for record in self:
            total_tax = sum(tax.amount for tax in record.tax_ids)
            record.amount_tax = total_tax
            record.amount_total = record.amount + total_tax

class WalletScheduledPaymentTax(models.Model):
    _name = 'wallet.scheduled.payment.tax'
    _description = 'Wallet Scheduled Payment Tax'
    _rec_name = 'tax_id'

    payment_id = fields.Many2one('wallet.scheduled.payment', string='Payment', required=True)
    company_currency_id = fields.Many2one(related='payment_id.company_currency_id')
    tax_id = fields.Many2one('account.tax', string='Tax', required=True)
    beneficiary_id = fields.Many2one('res.partner')
    amount = fields.Monetary(currency_field='company_currency_id', compute='_compute_amount', store=True, readonly=True)

    @api.depends('payment_id.amount', 'tax_id.amount')
    def _compute_amount(self):
        for record in self:
            base = record.payment_id.amount or 0.0
            tax = record.tax_id.amount or 0.0
            record.amount = base * (tax / 100.0)

class ResCompany(models.Model):
    _inherit = 'res.company'

    wallet_seq_income_id = fields.Many2one('ir.sequence', string='Income sequence')
    wallet_seq_expense_id = fields.Many2one('ir.sequence', string='Expense sequence')
    wallet_seq_pay_debt_id = fields.Many2one('ir.sequence', string='Pay Debts sequence')
    wallet_seq_rec_debt_id = fields.Many2one('ir.sequence', string='Receive Debts sequence')
    # Categorias por defecto wallet
    transfer_category = fields.Many2one('wallet.category')
    debt_category_id = fields.Many2one('wallet.category')

    @api.model_create_multi
    def create(self, vals):
        company = super().create(vals)
        # Crear secuencias por defecto para la nueva compañía
        company._create_wallet_sequences()
        return company

    def button_create_wallet_seq(self):
        self._create_wallet_sequences()

    def _create_wallet_sequences(self):
        self.ensure_one()
        # Metodo genérico para creación de sequencias

        def wallet_create_sequence(prefix, title, model):
            return self.env['ir.sequence'].create({
                'name': title,
                'code': model,
                'prefix': prefix,
                'padding': 7,
                'company_id': self.id,
            })

        if not self.wallet_seq_income_id:
            self.wallet_seq_income_id = wallet_create_sequence(
                prefix='IN-%(year)s-',
                title=f'Wallet Transaction Income - {self.name}',
                model='wallet.transaction'
            )
        if not self.wallet_seq_expense_id:
            self.wallet_seq_expense_id = wallet_create_sequence(
                prefix='EXP-%(year)s-',
                title=f'Wallet Transaction Expense - {self.name}',
                model='wallet.transaction'
            )

        if not self.wallet_seq_pay_debt_id:
            self.wallet_seq_pay_debt_id = wallet_create_sequence(
                prefix='DP-%(year)s-',
                title=f'Wallet Pay Debt - {self.name}',
                model='wallet.debts',
            )

        if not self.wallet_seq_rec_debt_id:
            self.wallet_seq_rec_debt_id = wallet_create_sequence(
                prefix='DC-%(year)s-',
                title=f'Wallet Receive Debt - {self.name}',
                model='wallet.debts',
            )
