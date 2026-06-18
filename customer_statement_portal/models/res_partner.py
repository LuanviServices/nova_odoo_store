from odoo import models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_account_statement(self):
        """Open the account statement wizard pre-filled with this partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Account Statement'),
            'res_model': 'customer.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_company_id': self.env.company.id,
            },
        }
