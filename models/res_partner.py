# -*- coding: utf-8 -*-
# © 2024 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    transaction_count = fields.Integer(
        string='Transactions',
        compute='_compute_transaction_count'
    )
    transaction_income_count = fields.Integer(
        string='Transaction incomes',
        compute='_compute_transaction_income_count'
    )
    transaction_expense_count = fields.Integer(
        string='Transaction expenses',
        compute='_compute_transaction_expense_count'
    )
    debts_count = fields.Integer(
        string="Debts",
        compute="_compute_debts_count"
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            if not partner.is_company:
                partner.company_id = self.env.company.id
            else:
                partner.company_id = False
        return partners
    
    def _compute_transaction_count(self):
        for partner in self:
            partner.transaction_count = self.env['wallet.transaction'].search_count([
                ('beneficiary_id', '=', partner.id)
            ])
    
    def _compute_transaction_income_count(self):
        for partner in self:
            partner.transaction_income_count = self.env['wallet.transaction'].search_count([
                ('transaction_type', '=', 'income'),
                ('beneficiary_id', '=', partner.id)
            ])
            
    def _compute_transaction_expense_count(self):
        for partner in self:
            partner.transaction_expense_count = self.env['wallet.transaction'].search_count([
                ('transaction_type', '=', 'expense'),
                ('beneficiary_id', '=', partner.id)
            ])
            
    def _compute_debts_count(self):
        for partner in self:
            partner.debts_count = self.env['wallet.debts'].search_count([
                ('state', 'in', ['active', 'overdue']),
                ('partner_id', '=', partner.id)
            ])
            
    def action_view_transactions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions',
            'res_model': 'wallet.transaction',
            'view_mode': 'list,form',
            'domain': [('beneficiary_id', '=', self.id)],
            'context': {'default_beneficiary_id': self.id},
        }
        
    def action_view_transactions_income(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions - Incomes',
            'res_model': 'wallet.transaction',
            'view_mode': 'list,form',
            'domain': [
                ('transaction_type', '=', 'income'),
                ('beneficiary_id', '=', self.id)
            ],
            'context': {'default_beneficiary_id': self.id, 'default_transaction_type': 'income'},
        }
        
    def action_view_transactions_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions - Expenses',
            'res_model': 'wallet.transaction',
            'view_mode': 'list,form',
            'domain': [
                ('transaction_type', '=', 'expense'),
                ('beneficiary_id', '=', self.id)
            ],
            'context': {'default_beneficiary_id': self.id, 'default_transaction_type': 'income'},
        }
        
    def action_view_debts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Debts',
            'res_model': 'wallet.debts',
            'view_mode': 'list,form',
            'domain': [
                ('state', 'in', ['active', 'overdue']),
                ('partner_id', '=', self.id)
            ],
            'context': {'default_partner_id': self.id},
        }
