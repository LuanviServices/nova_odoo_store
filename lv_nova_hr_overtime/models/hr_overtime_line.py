from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrOvertimeLine(models.Model):
    _name = 'hr.overtime.line'
    _description = 'Overtime / Time Bank Line'
    _order = 'date desc, id desc'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, index=True,
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    move_type = fields.Selection(
        [
            ('overtime', 'Overtime Earned'),
            ('compensation', 'Time Off Taken (from bank)'),
        ],
        string='Type',
        required=True,
        default='overtime',
    )
    hours = fields.Float(
        string='Hours',
        required=True,
        help='Positive for overtime earned. Negative for hours consumed '
             'from the time bank.',
    )
    compensation_type = fields.Selection(
        [
            ('pay', 'Paid in Payslip'),
            ('bank', 'Added to Time Bank'),
        ],
        string='Compensation',
        default='bank',
        help='Only relevant for "Overtime Earned" lines: whether these '
             'hours should be paid out or accumulated as banked time off.',
    )
    rate = fields.Float(
        string='Pay Rate',
        default=1.5,
        help='Multiplier applied when computing payable hours, e.g. 1.5 '
             'for time-and-a-half, 2.0 for double time.',
    )
    payable_hours = fields.Float(
        string='Payable Hours', compute='_compute_payable_hours', store=True,
    )
    state = fields.Selection(
        [
            ('draft', 'To Approve'),
            ('approved', 'Approved'),
            ('paid', 'Paid / Compensated'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    attendance_id = fields.Many2one(
        'hr.attendance', string='Source Attendance', readonly=True,
    )
    note = fields.Char(string='Note')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )

    @api.depends('hours', 'rate', 'move_type', 'compensation_type')
    def _compute_payable_hours(self):
        for line in self:
            if line.move_type == 'overtime' and line.compensation_type == 'pay':
                line.payable_hours = line.hours * line.rate
            else:
                line.payable_hours = 0.0

    @api.constrains('move_type', 'hours')
    def _check_hours_sign(self):
        for line in self:
            if line.move_type == 'compensation' and line.hours > 0:
                raise UserError(_(
                    'Time Off Taken lines must have a negative number of '
                    'hours (hours consumed from the bank).'
                ))
            if line.move_type == 'overtime' and line.hours < 0:
                raise UserError(_(
                    'Overtime Earned lines must have a positive number of '
                    'hours.'
                ))

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
        })

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'approved_by': False})
