# © 2024 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0

from datetime import datetime
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError


class WalletDebts(models.Model):
    _name = 'wallet.debts'
    _description = 'Debts wallet'
    _order = "start_date desc"
    _rec_name = 'name'
    _rec_names_search = ['name', 'partner_id']
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Debt Reference", required=True, copy=False, readonly=False, default=lambda self: _('Draft Debt'))
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    debt_type = fields.Selection([('pay', 'Pay'), ('receive', 'Receive')], required=True)
    partner_id = fields.Many2one('res.partner', string="Creditor", help="The partner to whom the debt is owed or who owes the debt", required=True)
    description = fields.Text()
    wallet_account = fields.Many2one('wallet.account', string="Account", help="The account where the debt is recorded")
    account_tag = fields.Html(related='wallet_account.account_tag')
    amount = fields.Monetary(default=0.00, currency_field='company_currency_id')
    amount_paid = fields.Monetary(compute='_compute_amount_paid', currency_field='company_currency_id', store=True)
    amount_residual = fields.Monetary(compute='_compute_amount_paid', currency_field='company_currency_id', store=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    transaction_ids = fields.One2many('wallet.transaction', 'debt_id', string="Related Transactions", readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('overdue', 'Overdue'), ('closed', 'Closed')], default='draft')
    payment_status = fields.Selection([('pending', 'Pending'), ('partial', 'Partial'), ('liquidated', 'Liquidated'), ('forgiven', 'Forgiven')], default='pending')
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
        store=False
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Validamos el monto de la transacción (negativo si es por pagar)
            vals['amount'] = self.validate_inc_exp_amount(
                debt_type = vals.get('debt_type'),
                amount = vals.get('amount', 0)
            )
            # Validamos que el monto no sea  (si es cero lanza una excepción)
            self.validate_amount(vals['amount'])
        return super().create(vals_list)
    
    def write(self, vals):
        for debt in self:
            # Validamos el monto de la transacción (negativo si es por pagar)
            if 'amount' in vals:
                vals['amount'] = debt.validate_inc_exp_amount(
                    debt_type = vals.get('debt_type', debt.debt_type),
                    amount = vals.get('amount', debt.amount)
                )
        return super(WalletDebts, self).write(vals)

    def action_confirm(self):
        # Verificamos si la deuda esta vinculada con alguna transacción prexistente
        # caso contrario la creamos
        self.ensure_one()
        self.state = 'active'
        # Crear transaccion
        debt_vals = {
            'beneficiary_id': self.partner_id.id,
            'description': self.description,
            'wallet_account': self.wallet_account.id,
            'date': self.start_date,
            'amount': self.amount,
        }
        if self.debt_type == 'pay':
            debt_vals['transation_type'] = 'income'
        else:
            debt_vals['transation_type'] = 'expense'
        if self.transaction_ids:
            transaction = self.transaction_ids[0]
            write_vals = self._get_vals_for_debt_transaction(debt_vals)
            transaction.write(write_vals)
        else:
            transaction = self.create_debt_transaction(debt_vals)
            transaction.message_post(
                body=_("Debt related transaction %s") % transaction.name,
            )
            # generamos en la secuencia de la deuda
            self.generate_debt_sequence()
        self.payment_status = 'pending'
        if self.is_overdue:
            self.state = 'overdue'

    def action_to_draft(self):
        self.ensure_one()
        if self.state in ['closed', 'cancel']:
            raise ValidationError(_("You cannot revert a debt that is already closed or canceled."))
        self.state = 'draft'

    def generate_debt_sequence(self):
        if self.debt_type == 'receive':
            self.name = self.company_id.wallet_seq_rec_debt_id.next_by_id()
        elif self.debt_type == 'pay':
            self.name = self.company_id.wallet_seq_pay_debt_id.next_by_id()
            
    def validate_inc_exp_amount(self, debt_type, amount):
        if debt_type == 'receive':
            amount = abs(amount)
        if debt_type == 'pay':
            amount = -abs(amount)
        return amount
    
    def validate_amount(self, amount):
        if amount == 0:
            raise ValidationError(_("Transactions must not be the value 0.00"))

    @api.depends('end_date', 'payment_status', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = (
                record.end_date
                and record.end_date < today
                and record.payment_status in ('pending', 'partial')
                and record.state not in ('closed', 'cancel')
            )
            record.state = 'overdue' if record.is_overdue and record.state == 'active' else record.state

    @api.depends('transaction_ids.amount')
    def _compute_amount_paid(self):
        for record in self:
            debt_type = record.debt_type
            if debt_type == 'pay':
                amount_paid = sum(transaction.amount for transaction in record.transaction_ids if transaction.amount < 0.00)
                record.amount_paid = abs(amount_paid)
                record.amount_residual = abs(amount_paid) - abs(record.amount)
            else:
                amount_paid = sum(transaction.amount for transaction in record.transaction_ids if transaction.amount > 0.00)
                record.amount_paid = -abs(amount_paid)
                record.amount_residual = record.amount - abs(amount_paid)
                
    def _get_vals_for_debt_transaction(self, vals):
        today = datetime.now()
        debt_category = False
        if self.company_id.debt_category_id:
            debt_category = self.company_id.debt_category_id
        else:
            raise ValidationError(_("The company does not have a category for debt transactions."))
        default_values = {
            'description': _('Debt: ') + vals.get('description', ''),
            'transaction_type': 'expense' if self.debt_type == 'pay' else 'income',
            'wallet_account': vals.get('wallet_account'),
            'date': vals.get('date') or today,
            'amount': vals.get('amount', 0.0),
            'debt_id': self.id,
            'category': debt_category.id,
        }
        if 'transation_type' in vals:
            default_values['transaction_type'] = vals['transation_type']
        return default_values

    def create_debt_transaction(self, vals):
        """ Create a transaction for the debt """
        default_values = self._get_vals_for_debt_transaction(vals)
        transaction = self.env['wallet.transaction'].create(default_values)
        return transaction
    
    @api.model
    def get_top_chart_data(self, month, year):
        start_date, end_date = self.env['wallet.transaction'].get_days_period(month, year)
        company_id = self.env.company.id
        domain = [('company_id', '=', company_id), ('state', '=', 'active'), ('end_date', '>=', start_date)]
        domain_pay = domain + [('debt_type', '=', 'pay')]
        domain_receive = domain + [('debt_type', '=', 'receive')]
        # --- Cobrar ---
        # Por partner (nombre)
        pays = self.read_group(
            domain_pay,
            ['amount_residual:sum'],
            ['partner_id'],
            orderby='amount_residual desc',
        )
        # --- Pagar ---
        # Por partner (nombre)
        receives = self.read_group(
            domain_receive,
            ['amount_residual:sum'],
            ['partner_id'],
            orderby='amount_residual desc',
        )
        return {
            # Pagar
            'top_pays': [
                {'label': p['partner_id'][1], 'value': abs(p['amount_residual'])} for p in pays
            ],
            # Cobrar
            'top_receives': [
                {'label': r['partner_id'][1], 'value': abs(r['amount_residual'])} for r in receives
            ],
        }

    def action_forgive_debt(self):
        return {
            'name': _("Forgive Debt"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wallet.debts.actions.wizard',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'debt_action': 'forgive_debt',
            },
        }

    def action_settle_debt(self):
        return {
            'name': _("Settle Debt"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wallet.debts.actions.wizard',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'debt_action': 'settle_debt',
            },
        }

    def action_postpone_debt(self):
        return {
            'name': _("Postpone Debt"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wallet.debts.actions.wizard',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'debt_action': 'postpone_debt',
            },
        }
