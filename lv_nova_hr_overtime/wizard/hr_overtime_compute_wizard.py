from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import api, fields, models, _


class HrOvertimeComputeWizard(models.TransientModel):
    _name = 'hr.overtime.compute.wizard'
    _description = 'Compute Overtime from Attendance'

    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    compensation_type = fields.Selection(
        [
            ('pay', 'Paid in Payslip'),
            ('bank', 'Added to Time Bank'),
        ],
        string='Send Overtime To',
        default='bank',
        required=True,
    )
    rate = fields.Float(string='Pay Rate', default=1.5)
    minimum_threshold = fields.Float(
        string='Minimum Overtime to Record (hrs)',
        default=0.25,
        help='Daily overtime below this threshold is ignored (avoids '
             'creating lines for a few rounding minutes).',
    )

    def action_compute(self):
        self.ensure_one()
        Attendance = self.env['hr.attendance']
        OvertimeLine = self.env['hr.overtime.line']

        date_start = datetime.combine(self.date_from, time.min)
        date_end = datetime.combine(self.date_to + timedelta(days=1), time.min)

        created = 0
        skipped_existing = 0

        for employee in self.employee_ids:
            attendances = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', date_start),
                ('check_in', '<', date_end),
                ('check_out', '!=', False),
            ])

            by_day = defaultdict(float)
            for att in attendances:
                day = fields.Datetime.context_timestamp(
                    self, att.check_in
                ).date()
                by_day[day] += att.worked_hours

            calendar = employee.resource_calendar_id
            expected_by_weekday = self._expected_hours_by_weekday(calendar)

            for day, worked in by_day.items():
                expected = expected_by_weekday.get(str(day.weekday()), 0.0)
                overtime = worked - expected
                if overtime < self.minimum_threshold:
                    continue

                existing = OvertimeLine.search_count([
                    ('employee_id', '=', employee.id),
                    ('date', '=', day),
                    ('move_type', '=', 'overtime'),
                ])
                if existing:
                    skipped_existing += 1
                    continue

                OvertimeLine.create({
                    'employee_id': employee.id,
                    'date': day,
                    'move_type': 'overtime',
                    'hours': round(overtime, 2),
                    'compensation_type': self.compensation_type,
                    'rate': self.rate,
                    'state': 'draft',
                    'note': _('Auto-detected: worked %.2f hrs, scheduled %.2f hrs')
                    % (worked, expected),
                })
                created += 1

        message = _('%(created)s overtime line(s) created.') % {'created': created}
        if skipped_existing:
            message += ' ' + _(
                '%(skipped)s day(s) skipped (a line already existed).'
            ) % {'skipped': skipped_existing}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Overtime Computed'),
                'message': message,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Overtime Lines'),
                    'res_model': 'hr.overtime.line',
                    'view_mode': 'list,form',
                    'domain': [('employee_id', 'in', self.employee_ids.ids),
                               ('date', '>=', self.date_from),
                               ('date', '<=', self.date_to)],
                },
            },
        }

    @staticmethod
    def _expected_hours_by_weekday(calendar):
        """Return {weekday_str: total_scheduled_hours} for a resource
        calendar, e.g. {'0': 8.0, '1': 8.0, ...} where '0' = Monday."""
        result = defaultdict(float)
        if not calendar:
            return result
        for line in calendar.attendance_ids:
            result[line.dayofweek] += (line.hour_to - line.hour_from)
        return result
