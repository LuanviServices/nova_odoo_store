from odoo import api, fields, models, _


class RecurringTaskInstance(models.Model):
    _name = 'recurring.task.instance'
    _description = 'Recurring Task Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date asc, id asc'

    name = fields.Char(string='Task', required=True)
    template_id = fields.Many2one(
        'recurring.task.template', string='Template',
        ondelete='cascade', index=True,
    )
    frequency = fields.Selection(
        related='template_id.frequency', store=True, readonly=True,
    )
    description = fields.Html(string='Instructions')
    due_date = fields.Date(string='Due Date', required=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Assigned To',
        default=lambda self: self.env.user,
    )
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Important'), ('2', 'Urgent')],
        string='Priority', default='0',
    )
    state = fields.Selection(
        [
            ('pending',  'Pending'),
            ('done',     'Done'),
            ('skipped',  'Skipped'),
            ('overdue',  'Overdue'),
        ],
        string='Status',
        default='pending',
        tracking=True,
        index=True,
    )
    completion_date = fields.Datetime(
        string='Completed On', readonly=True, copy=False,
    )
    completed_by = fields.Many2one(
        'res.users', string='Completed By', readonly=True, copy=False,
    )
    completion_notes = fields.Text(
        string='Completion Notes',
        help='Optional notes when marking this task as done.',
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_days_overdue',
    )
    kanban_state = fields.Selection(
        [
            ('normal',   'In Progress'),
            ('blocked',  'Blocked'),
            ('done',     'Ready'),
        ],
        string='Kanban State',
        default='normal',
    )

    @api.depends('due_date', 'state')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for inst in self:
            if inst.state in ('done', 'skipped'):
                inst.days_overdue = 0
            elif inst.due_date:
                delta = (today - inst.due_date).days
                inst.days_overdue = max(delta, 0)
            else:
                inst.days_overdue = 0

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_mark_done(self):
        self.ensure_one()
        self.write({
            'state':           'done',
            'completion_date': fields.Datetime.now(),
            'completed_by':    self.env.user.id,
        })
        self.message_post(
            body=_('Task marked as <b>Done</b> by %s.') % self.env.user.name,
            subtype_xmlid='mail.mt_note',
        )

    def action_mark_skipped(self):
        self.ensure_one()
        self.write({'state': 'skipped'})
        self.message_post(
            body=_('Task skipped by %s.') % self.env.user.name,
            subtype_xmlid='mail.mt_note',
        )

    def action_reset_pending(self):
        self.write({
            'state':           'pending',
            'completion_date': False,
            'completed_by':    False,
        })

    # ------------------------------------------------------------------
    # Cron: mark overdue
    # ------------------------------------------------------------------

    @api.model
    def _cron_mark_overdue(self):
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'pending'),
            ('due_date', '<', str(today)),
        ])
        overdue.write({'state': 'overdue'})
