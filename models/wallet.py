# -*- coding: utf-8 -*-
# © 2024 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

transaction_types = [('income', 'Income'), ('expense', 'Expense')]
payment_types = [('cash', 'Cash'), ('transfer', 'Transfer')]

class WalletTransfer(models.Model):
    _name = 'wallet.transfer'
    _description = 'Transfer wallet'
    _rec_name = 'description'

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    description = fields.Char(required=True)
    origin_account = fields.Many2one('wallet.account', required=True)
    destiny_account = fields.Many2one('wallet.account', required=True)
    tag = fields.Many2one('wallet.tag')
    date = fields.Date(required=True)
    amount = fields.Monetary(default=0.00, currency_field='company_currency_id')
    origin_id = fields.Many2one('wallet.transaction', ondelete='cascade')
    destiny_id = fields.Many2one('wallet.transaction', ondelete='cascade')
    transaction_ids = fields.One2many('wallet.transaction',compute='_compute_transaction_ids', store=False)

    @api.model_create_multi
    def create(self, values):
        transf_category = self.env.user.company_id.transfer_category or False
        if not transf_category:
            raise ValidationError(_("The company does not have a sequence for income transactions."))
        for vals in values:
            v = self.create_transactions(vals, transf_category)
            vals['origin_id'] = v['origin']
            vals['destiny_id'] = v['destiny']
        return super(WalletTransfer, self).create(values)
    
    def write(self, vals):
        for transfer in self:
            if 'description' in vals:
                transfer.destiny_id.description = vals['description']
                transfer.origin_id.description = _('Transfer: ') + vals['description']
            if 'origin_account' in vals:
                transfer.destiny_id.wallet_account = vals['origin_account']
            if 'destiny_account' in vals:
                transfer.origin_id.wallet_account = vals['destiny_account']
            if 'date' in vals:
                transfer.origin_id.date = vals['date']
                transfer.destiny_id.date = vals['date']
            if 'amount' in vals:
                transfer.origin_id.amount = vals['amount']
                transfer.destiny_id.amount = vals['amount']
        return super(WalletTransfer, self).write(vals)

    def unlink(self):
        for transfer in self:
            if transfer.origin_id:
                transfer.origin_id.unlink()
            if transfer.destiny_id:
                transfer.destiny_id.unlink()
        return super(WalletTransfer, self).unlink()

    def create_transactions(self, values, category):
        transaction_obj = self.env['wallet.transaction']
        today = datetime.now()
        default_values = {
            'description': _('Transfer: ') + values.get('description'),
            'transaction_type': 'income',
            'wallet_account': values.get('destiny_account'),
            'tag': values.get('tag'),
            'date': values.get('date') or today,
            'amount': values.get('amount'),
            'transfer': True,
            'category': category.id
        }
        origin_id = transaction_obj.create(default_values)
        default_values.update({
            'description': values.get('description'),
            'transaction_type': 'expense',
            'wallet_account': values.get('origin_account'),
        })
        default_values['amount'] = transaction_obj.validate_inc_exp_amount(default_values['transaction_type'], default_values['amount'])
        destiny_id = transaction_obj.create(default_values)
        return {'origin': origin_id.id, 'destiny': destiny_id.id}

    
    @api.depends('origin_id', 'destiny_id')
    def _compute_transaction_ids(self):
        for record in self:
            record.transaction_ids = record.origin_id | record.destiny_id

