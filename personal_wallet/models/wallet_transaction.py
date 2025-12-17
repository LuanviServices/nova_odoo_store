# © 2024 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


transaction_types = [('income', 'Income'), ('expense', 'Expense')]
payment_types = [('cash', 'Cash'), ('transfer', 'Transfer')]


class WalletTransaction(models.Model):
    _name = 'wallet.transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Transaction Wallet'
    _order = "date desc"
    _rec_name = 'name'
    _rec_names_search = ['description', 'amount']

    name = fields.Char(string="Transaction Reference", required=True, copy=False, readonly=False, default=lambda self: _('/'))
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)
    description = fields.Text(required=True, tracking=True)
    transaction_type = fields.Selection(transaction_types, required=True)
    beneficiary_id = fields.Many2one('res.partner', tracking=True)
    wallet_account = fields.Many2one('wallet.account', required=True,  tracking=True, string="Account")
    account_tag = fields.Html(related='wallet_account.account_tag')
    category = fields.Many2one('wallet.category',  tracking=True)
    tag = fields.Many2many('wallet.tag', 'wallet_transaction_tag_rel', 'transaction_id', 'tag_id')
    date = fields.Date(required=True,  tracking=True)
    payment_method = fields.Selection(payment_types, tracking=True)
    amount = fields.Monetary(default=0.00, currency_field='company_currency_id')
    amount_tax = fields.Monetary(compute='_compute_amounts', store=True, currency_field='company_currency_id')
    amount_total = fields.Monetary(compute='_compute_amounts', store=True, currency_field='company_currency_id')
    transfer = fields.Boolean(default=False)
    template_id = fields.Many2one('wallet.template')
    tax_ids = fields.One2many('wallet.transaction.tax', 'transaction_id', string='Taxes')
    debt_id = fields.Many2one('wallet.debts', string='Related Debts', help="Debts associated with this transaction")
    shared_record = fields.Char(
        string="Shared Record",
        compute="_compute_shared_record",
        store=False
    )
    
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        # Solo aplica si el usuario quiere crear un nuevo registro
        vals['shared_record'] = 'propietary'
        return vals
    
    def _valid_permission_for_account(self, account):
        user = self.env.user
        if account.company_id and account.company_id != user.company_id:
            permission = self.env['wallet.account.permission'].search([
                ('account_id', '=', account.id),
                ('user_id', '=', user.id),
            ], limit=1)
            if not permission or permission.permission_type != 'transaction':
                raise ValidationError(_("You do not have permission for this account: %s") % account.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Validamos permisos sobre la cuenta
            if vals.get('wallet_account'):
                account = self.env['wallet.account'].browse(vals['wallet_account'])
                self._valid_permission_for_account(account)
            # Validamos el monto de la transacción (negativo si es gasto)
            vals['amount'] = self.validate_inc_exp_amount(
                transaction_type=vals.get('transaction_type'),
                amount=vals.get('amount', 0)
            )
            # Validamos que el monto no sea  (si es cero lanza una excepción)
            self.validate_amount(vals['amount'])
            # Generamos sequencia si es una transacción de ingresos
            if vals.get('transaction_type') == 'income':
                if self.env.user.company_id.wallet_seq_income_id:
                    vals['name'] = self.env.user.company_id.wallet_seq_income_id.next_by_id()
                else:
                    raise ValidationError(_("The company does not have a sequence for income transactions."))
            # Generamos la secuencia si es una transacción de gasto
            if vals.get('transaction_type') == 'expense':
                if self.env.user.company_id.wallet_seq_expense_id:
                    vals['name'] = self.env.user.company_id.wallet_seq_expense_id.next_by_id()
                else:
                    raise ValidationError(_("The company does not have a sequence for expense transactions."))
        return super().create(vals_list)
    
    def write(self, vals):
        for transaction in self:
            # Validamos permisos sobre la cuenta
            if vals.get('wallet_account'):
                account = self.env['wallet.account'].browse(vals['wallet_account'])
                self._valid_permission_for_account(account)
            if transaction.debt_id and 'debt_action' not in self.env.context:
                raise ValidationError(_("You cannot modify a transaction associated with a debt. Please modify the debt instead."))
            # Obtenemos los valores reales de la transacción
            new_transaction_type = vals.get('transaction_type', transaction.transaction_type)
            new_amount = vals.get('amount', transaction.amount)
            new_tax_ids = vals.get('tax_ids', transaction.tax_ids)
            # Validamos el monto de la transacción (negativo si es gasto)
            if 'amount' in vals or 'transaction_type' in vals:
                self.validate_amount(new_amount)
                vals['amount'] = self.validate_inc_exp_amount(
                    transaction_type=new_transaction_type,
                    amount=new_amount
                )
            # Regenerar la secuencia si el tipo de transacción cambia
            if new_transaction_type != transaction.transaction_type:
                if new_transaction_type == 'income':
                    vals['name'] = self.env.user.company_id.wallet_seq_income_id.next_by_id()
                elif new_transaction_type == 'expense':
                    vals['name'] = self.env.user.company_id.wallet_seq_expense_id.next_by_id()
            # Validamos el monto de los impuestos una vez guardados los cambios de la transacción (negativo si es gasto)
            if 'transaction_type' in vals:
                if new_tax_ids:
                    for tax in new_tax_ids:
                        tax.write({'amount': self.validate_inc_exp_amount(
                            transaction_type=new_transaction_type,
                            amount=tax.amount
                        )})
        return super().write(vals)

    def unlink(self):
        for transaction in self:
            # Validamos permisos sobre la cuenta
            self._valid_permission_for_account(transaction.wallet_account)
            if transaction.debt_id:
                raise ValidationError(_("You cannot delete a transaction associated with a debt. Please delete the debt instead."))
        return super().unlink()
    
    def _compute_shared_record(self):
        user = self.env.user
        user_company_id = user.company_id.id
        for rec in self:
            account = rec.wallet_account
            # 1. Si la cuenta no tiene company o coincide con la del usuario
            if not account.company_id or account.company_id.id == user_company_id:
                rec.shared_record = 'propietary'
                continue
            # 2. Verificar permisos personalizados
            permission = self.env['wallet.account.permission'].search([
                ('account_id', '=', account.id),
                ('user_id', '=', user.id),
            ], limit=1)
            if permission:
                rec.shared_record = permission.permission_type
    
    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def create_debt(self):
        """Crea una deuda asociada a la transacción actual."""
        self.ensure_one()
        if not self.is_debt:
            return False

        existing_debt = self.env['wallet.debts'].search([('origin_transaction_id', '=', self.id)], limit=1)
        if existing_debt:
            return existing_debt

        return self.env['wallet.debts'].create({
            'name': self.name,
            'company_id': self.company_id.id,
            'debt_type': 'receive' if self.transaction_type == 'income' else 'pay',
            'partner_id': self.beneficiary_id.id,
            'description': self.description,
            'wallet_account': self.wallet_account.id,
            'amount': abs(self.amount),
            'start_date': self.date,
            'end_date': fields.Date.today() + timedelta(days=30),  # Por ejemplo, 30 días después
            'origin_transaction_id': self.id,
        })

    def validate_inc_exp_amount(self, transaction_type, amount):
        if transaction_type == 'expense' and amount > 0:
            amount = -amount
        if transaction_type == 'income' and amount < 0:
            amount = abs(amount)
        return amount

    def validate_amount(self, amount):
        if amount == 0:
            raise ValidationError(_("Transactions must not be the value 0.00"))

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.description = self.template_id.description
            self.transaction_type = self.template_id.transaction_type
            self.beneficiary_id = self.template_id.beneficiary_id.id
            self.wallet_account = self.template_id.wallet_account.id
            self.category = self.template_id.category.id
            self.tag = self.template_id.tag.id
            self.date = datetime.now()
            self.payment_method = self.template_id.payment_method
            self.amount = self.template_id.amount

    @api.depends('amount', 'tax_ids.amount')
    def _compute_amounts(self):
        for record in self:
            total_tax = sum(tax.amount for tax in record.tax_ids)
            record.amount_tax = total_tax
            record.amount_total = record.amount + total_tax

    @api.depends('debt_ids', 'beneficiary_id', 'amount', 'date')
    def _compute_debt_ids(self):
        for transaction in self:
            # Obtenemos las deudas asociadas a la transacción
            debts = self.env['wallet.debts'].search([('origin_transaction_id', '=', transaction.id)])
            transaction.debt_ids = debts
            # Si no hay deudas, se asegura que el campo esté vacío
            if not debts:
                transaction.debt_ids = False

    def get_days_period(self, month, year):
        start_date = date(int(year), int(month), 1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        return start_date, end_date

    @api.model
    def get_summary_data(self, month, year):
        start_date, end_date = self.get_days_period(month, year)
        company_id = self.env.company.id
        # Período actual
        domain_current = [
            ('wallet_account.company_id', '=', company_id),
            ('wallet_account.show_panel', '=', True),
            ('transfer', '=', False),
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ]

        def total_amount(domain, tipo=None):
            dom = list(domain)
            if tipo:
                dom.append(('transaction_type', '=', tipo))
            return sum(self.search(dom).mapped('amount_total'))

        def count(domain):
            return self.search_count(domain)

        # Datos actuales
        transactions = count(domain_current)
        expenses = total_amount(domain_current, 'expense')
        revenue = total_amount(domain_current, 'income')
        accounts = total_amount(domain_current)

        return {
            'transactions': transactions,
            'expenses': expenses,
            'revenue': revenue,
            'accounts': accounts,
        }

    @api.model
    def get_top_chart_data(self, month, year):
        start_date, end_date = self.get_days_period(month, year)
        company_id = self.env.company.id
        domain = [('company_id', '=', company_id), ('transfer', '=', False), ('date', '>=', start_date), ('date', '<=', end_date)]
        domain_expenses = domain + [('transaction_type', '=', 'expense')]
        domain_incomes = domain + [('transaction_type', '=', 'income')]
        # --- Ingresos ---
        # Por categoría (nombre)
        incomes = self.read_group(
            domain_incomes,
            ['amount_total:sum'],
            ['category'],
            orderby='amount_total desc',
        )
        # Por cuentas
        incomes_accounts = self.read_group(
            domain_incomes,
            ['amount_total:sum'],
            ['wallet_account'],
            orderby='amount_total desc',
        )
        # Transacciones
        top_incomes_transactions = self.read_group(
            domain_incomes,
            ['amount_total:sum'],
            ['category'])
        # --- Gastos ---
        # Por categoría (nombre)
        expenses = self.read_group(
            domain_expenses,
            ['amount_total:sum'],
            ['category'],
            orderby='amount_total desc',
        )
        # Por cuentas
        expenses_accounts = self.read_group(
            domain_expenses,
            ['amount_total:sum'],
            ['wallet_account'],
            orderby='amount_total desc',
        )
        # Transacciones
        top_expenses_transactions = self.read_group(
            domain_expenses,
            ['amount_total:sum'],
            ['category'])
        return {
            # Ingresos
            'top_incomes': [
                {'label': i['category'][1], 'value': abs(i['amount_total'])} for i in incomes
            ],
            'top_incomes_accounts': [
                {'label': self.env['wallet.account'].browse(a['wallet_account'][0]).name, 'value': abs(a['amount_total'])}
                for a in incomes_accounts if a['wallet_account']
            ],
            'top_incomes_transactions': [
                {'label': t['category'][1], 'value': abs(t['amount_total'])} for t in top_incomes_transactions
            ],
            # Gastos
            'top_expenses': [
                {'label': e['category'][1], 'value': abs(e['amount_total'])} for e in expenses
            ],
            'top_expenses_accounts': [
                {'label': self.env['wallet.account'].browse(a['wallet_account'][0]).name, 'value': abs(a['amount_total'])}
                for a in expenses_accounts if a['wallet_account']
            ],
            'top_expenses_transactions': [
                {'label': t['category'][1], 'value': abs(t['amount_total'])} for t in top_expenses_transactions
            ],
        }


class WalletTransactionTax(models.Model):
    _name = 'wallet.transaction.tax'
    _description = 'Wallet Transaction Tax'
    _rec_name = 'tax_id'

    transaction_id = fields.Many2one('wallet.transaction', string='Transaction', required=True)
    company_currency_id = fields.Many2one(related='transaction_id.company_currency_id')
    tax_id = fields.Many2one('account.tax', string='Tax', required=True)
    beneficiary_id = fields.Many2one('res.partner')
    amount = fields.Monetary(currency_field='company_currency_id', compute='_compute_amount', store=True, readonly=True)

    @api.depends('transaction_id.amount', 'tax_id.amount')
    def _compute_amount(self):
        for record in self:
            base = record.transaction_id.amount or 0.0
            tax = record.tax_id.amount or 0.0
            record.amount = base * (tax / 100.0)
