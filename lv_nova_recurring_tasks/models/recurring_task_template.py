from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

FREQUENCY = [
    ('daily',     'Daily'),
    ('weekly',    'Weekly'),
    ('biweekly',  'Every 2 Weeks'),
    ('monthly',   'Monthly'),
    ('quarterly', 'Quarterly'),
    ('yearly',    'Yearly'),
]

ADVANCE_DAYS = {
    'daily':     0,
    'weekly':    2,
    'biweekly':  3,
    'monthly':   5,
    'quarterly': 7,
    'yearly':    14,
}


class RecurringTaskTemplate(models.Model):
    _name = 'recurring.task.template'
    _description = 'Recurring Task Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'frequency, name'

    name = fields.Char(string='Task Name', required=True, tracking=True)
    description = fields.Html(string='Instructions / Checklist')
    frequency = fields.Selection(
        FREQUENCY, string='Frequency', required=True,
        default='weekly', tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Assigned To',
        default=lambda self: self.env.user,
        tracking=True,
    )
    team_ids = fields.Many2many(
        'res.users', string='Team',
        help='Additional users who can work on this task.',
    )
    tag_ids = fields.Many2many(
        'recurring.task.tag', string='Tags',
    )
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Important'), ('2', 'Urgent')],
        string='Priority', default='0',
    )
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        help='First instance will be generated on or after this date.',
    )
    end_date = fields.Date(
        string='End Date',
        help='No instances will be generated after this date. '
             'Leave empty for indefinite.',
    )
    advance_days = fields.Integer(
        string='Generate N Days in Advance',
        help='Create the next instance this many days before it is due. '
             '0 means generate on the due date itself.',
        default=0,
    )

    # -- Statistics -------------------------------------------------------
    instance_ids = fields.One2many(
        'recurring.task.instance', 'template_id', string='Instances',
    )
    instance_count = fields.Integer(
        compute='_compute_stats', string='Total Instances',
    )
    done_count = fields.Integer(
        compute='_compute_stats', string='Completed',
    )
    overdue_count = fields.Integer(
        compute='_compute_stats', string='Overdue',
    )
    completion_rate = fields.Float(
        compute='_compute_stats', string='Completion Rate %', digits=(5, 1),
    )
    last_generated_date = fields.Date(
        string='Last Generated', readonly=True, copy=False,
    )
    next_due_date = fields.Date(
        string='Next Due Date',
        compute='_compute_next_due_date',
    )

    @api.depends('instance_ids.state')
    def _compute_stats(self):
        for tpl in self:
            instances = tpl.instance_ids
            total     = len(instances)
            done      = len(instances.filtered(lambda i: i.state == 'done'))
            overdue   = len(instances.filtered(lambda i: i.state == 'overdue'))
            tpl.instance_count  = total
            tpl.done_count      = done
            tpl.overdue_count   = overdue
            tpl.completion_rate = (done / total * 100.0) if total else 0.0

    @api.depends('last_generated_date', 'frequency', 'start_date')
    def _compute_next_due_date(self):
        for tpl in self:
            tpl.next_due_date = tpl._get_next_due_date()

    def _get_next_due_date(self):
        base = self.last_generated_date or self.start_date or date.today()
        return self._advance_date(base, self.frequency)

    @staticmethod
    def _advance_date(from_date, frequency):
        if frequency == 'daily':
            return from_date + timedelta(days=1)
        if frequency == 'weekly':
            return from_date + timedelta(weeks=1)
        if frequency == 'biweekly':
            return from_date + timedelta(weeks=2)
        if frequency == 'monthly':
            return from_date + relativedelta(months=1)
        if frequency == 'quarterly':
            return from_date + relativedelta(months=3)
        if frequency == 'yearly':
            return from_date + relativedelta(years=1)
        return from_date + timedelta(days=7)

    # ------------------------------------------------------------------
    # Instance generation
    # ------------------------------------------------------------------

    def action_generate_now(self):
        """Manually generate the next instance for this template."""
        self.ensure_one()
        instance = self._generate_instance()
        if not instance:
            raise UserError(_(
                'No instance generated — either the next due date is in '
                'the future (considering advance_days) or the end date '
                'has passed.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task Generated'),
            'res_model': 'recurring.task.instance',
            'view_mode': 'form',
            'res_id': instance.id,
        }

    def _generate_instance(self):
        """Generate the next pending instance if it is time to do so."""
        self.ensure_one()
        today = date.today()
        next_due = self._get_next_due_date()

        if self.end_date and next_due > self.end_date:
            return False

        adv = self.advance_days or ADVANCE_DAYS.get(self.frequency, 0)
        if (next_due - timedelta(days=adv)) > today:
            return False

        # Avoid duplicates
        existing = self.instance_ids.filtered(
            lambda i: i.due_date == next_due
            and i.state in ('pending', 'done')
        )
        if existing:
            return False

        instance = self.env['recurring.task.instance'].create({
            'template_id': self.id,
            'name':        self.name,
            'due_date':    next_due,
            'user_id':     self.user_id.id,
            'priority':    self.priority,
            'description': self.description,
        })
        self.last_generated_date = next_due
        return instance

    @api.model
    def _cron_generate_instances(self):
        """Daily cron: generate instances for all active templates."""
        templates = self.search([('active', '=', True)])
        for tpl in templates:
            tpl._generate_instance()
        # Also mark overdue
        self.env['recurring.task.instance']._cron_mark_overdue()


class RecurringTaskTag(models.Model):
    _name = 'recurring.task.tag'
    _description = 'Recurring Task Tag'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')
