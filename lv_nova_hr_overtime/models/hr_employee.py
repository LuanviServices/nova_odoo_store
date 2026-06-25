from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    overtime_bank_balance = fields.Float(
        string='Time Bank Balance (hrs)',
        compute='_compute_overtime_bank_balance',
    )
    overtime_line_count = fields.Integer(
        string='Overtime Line Count',
        compute='_compute_overtime_bank_balance',
    )

    def _compute_overtime_bank_balance(self):
        groups = self.env['hr.overtime.line']._read_group(
            [
                ('employee_id', 'in', self.ids),
                ('state', '=', 'approved'),
                '|',
                ('move_type', '=', 'compensation'),
                '&', ('move_type', '=', 'overtime'),
                ('compensation_type', '=', 'bank'),
            ],
            groupby=['employee_id'],
            aggregates=['hours:sum', '__count'],
        )
        balances = {emp.id: total for emp, total, _cnt in groups}
        counts = {emp.id: cnt for emp, _total, cnt in groups}
        for employee in self:
            employee.overtime_bank_balance = balances.get(employee.id, 0.0)
            employee.overtime_line_count = counts.get(employee.id, 0)

    def action_view_overtime_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Overtime / Time Bank',
            'res_model': 'hr.overtime.line',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
