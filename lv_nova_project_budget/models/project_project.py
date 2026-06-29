import json
from odoo import api, fields, models, _

ALERT_WARNING  = 80.0   # orange threshold
ALERT_EXCEEDED = 100.0  # red threshold


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # ------------------------------------------------------------------
    # Budget configuration
    # ------------------------------------------------------------------

    has_budget = fields.Boolean(
        string='Enable Budget',
        default=False,
        help='Enable hour and/or monetary budget tracking for this project.',
    )
    budget_hours = fields.Float(
        string='Hour Budget',
        digits=(10, 2),
        help='Maximum planned hours for this project.',
    )
    budget_amount = fields.Monetary(
        string='Monetary Budget',
        currency_field='currency_id',
        help='Maximum planned spend (timesheet costs + vendor bills via '
             'analytic account).',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    alert_80_sent = fields.Boolean(
        string='80% Alert Sent',
        default=False,
        copy=False,
        readonly=True,
    )
    alert_100_sent = fields.Boolean(
        string='100% Alert Sent',
        default=False,
        copy=False,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Computed progress fields
    # ------------------------------------------------------------------

    spent_hours = fields.Float(
        string='Logged Hours',
        compute='_compute_budget_progress',
        digits=(10, 2),
    )
    spent_amount = fields.Monetary(
        string='Spent Amount',
        compute='_compute_budget_progress',
        currency_field='currency_id',
    )
    remaining_hours = fields.Float(
        string='Remaining Hours',
        compute='_compute_budget_progress',
        digits=(10, 2),
    )
    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        compute='_compute_budget_progress',
        currency_field='currency_id',
    )
    hours_pct = fields.Float(
        string='Hours Used %',
        compute='_compute_budget_progress',
        digits=(5, 1),
    )
    amount_pct = fields.Float(
        string='Amount Used %',
        compute='_compute_budget_progress',
        digits=(5, 1),
    )
    budget_alert_level = fields.Selection(
        [
            ('ok',       'On Track'),
            ('warning',  'Warning (>80%)'),
            ('exceeded', 'Exceeded (>100%)'),
        ],
        string='Budget Status',
        compute='_compute_budget_progress',
    )

    @api.depends(
        'has_budget',
        'budget_hours',
        'budget_amount',
        'timesheet_ids.unit_amount',
        'analytic_account_id',
    )
    def _compute_budget_progress(self):
        for project in self:
            # -- Hours: from timesheet lines -----------------------
            spent_h = sum(project.timesheet_ids.mapped('unit_amount'))

            # -- Amount: timesheet cost + vendor bills on analytic --
            spent_a = 0.0
            if project.analytic_account_id:
                spent_a = project._get_spent_amount()

            # -- Percentages ---------------------------------------
            h_pct = (spent_h / project.budget_hours * 100.0
                     if project.budget_hours else 0.0)
            a_pct = (spent_a / project.budget_amount * 100.0
                     if project.budget_amount else 0.0)

            worst = max(h_pct if project.budget_hours else 0.0,
                        a_pct if project.budget_amount else 0.0)
            if worst >= ALERT_EXCEEDED:
                level = 'exceeded'
            elif worst >= ALERT_WARNING:
                level = 'warning'
            else:
                level = 'ok'

            project.spent_hours      = spent_h
            project.spent_amount     = spent_a
            project.remaining_hours  = max(0.0, project.budget_hours - spent_h)
            project.remaining_amount = max(0.0, project.budget_amount - spent_a)
            project.hours_pct        = min(h_pct, 200.0)   # cap display at 200%
            project.amount_pct       = min(a_pct, 200.0)
            project.budget_alert_level = level

    def _get_spent_amount(self):
        """
        Sum of posted vendor bill lines + timesheet cost lines
        linked to this project's analytic account.
        """
        self.ensure_one()
        analytic = self.analytic_account_id
        if not analytic:
            return 0.0

        company_currency = self.company_id.currency_id

        # Vendor bills via analytic distribution
        bill_lines = self.env['account.move.line'].sudo().search([
            ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
            ('move_id.state', '=', 'posted'),
            ('analytic_distribution', 'like', str(analytic.id)),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ])
        total = 0.0
        for line in bill_lines:
            pct = self._get_analytic_pct(line.analytic_distribution, analytic.id)
            sign = -1 if line.move_id.move_type == 'in_refund' else 1
            amount = line.price_subtotal * pct / 100.0 * sign
            if line.currency_id and line.currency_id != company_currency:
                amount = line.currency_id._convert(
                    amount, company_currency,
                    self.company_id,
                    line.move_id.invoice_date or fields.Date.today(),
                )
            total += amount

        # Timesheet cost (hours × employee rate)
        for ts in self.timesheet_ids:
            rate = (ts.employee_id.timesheet_cost
                    if ts.employee_id and hasattr(ts.employee_id, 'timesheet_cost')
                    else 0.0)
            total += ts.unit_amount * rate

        return total

    @staticmethod
    def _get_analytic_pct(analytic_distribution, account_id):
        if not analytic_distribution:
            return 100.0
        try:
            dist = (json.loads(analytic_distribution)
                    if isinstance(analytic_distribution, str)
                    else analytic_distribution)
            return float(dist.get(str(account_id), 0.0))
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Print action
    # ------------------------------------------------------------------

    def action_print_budget_report(self):
        self.ensure_one()
        return self.env.ref(
            'lv_nova_project_budget.action_report_project_budget'
        ).report_action(self)

    def _fmt(self, amount):
        c = self.currency_id
        s = '{:,.2f}'.format(abs(amount))
        sign = '-' if amount < 0 else ''
        return ('{}{}\u00a0{}'.format(sign, c.symbol, s)
                if c.position == 'before'
                else '{}{}\u00a0{}'.format(sign, s, c.symbol))

    # ------------------------------------------------------------------
    # Scheduled action — daily budget alert emails
    # ------------------------------------------------------------------

    @api.model
    def _cron_check_budget_alerts(self):
        """Daily job: send email alerts when projects cross 80% or 100%."""
        projects = self.search([
            ('has_budget', '=', True),
            '|', ('budget_hours', '>', 0), ('budget_amount', '>', 0),
        ])
        for project in projects:
            level = project.budget_alert_level
            managers = project.user_ids
            if not managers:
                continue

            if level == 'exceeded' and not project.alert_100_sent:
                project._send_budget_alert(managers, level='100')
                project.alert_100_sent = True
            elif level in ('warning', 'exceeded') and not project.alert_80_sent:
                project._send_budget_alert(managers, level='80')
                project.alert_80_sent = True

            # Reset flags if spending drops back below thresholds (e.g. after
            # a correction entry) so alerts fire again if needed.
            if level == 'ok':
                project.write({'alert_80_sent': False, 'alert_100_sent': False})

    def _send_budget_alert(self, managers, level='80'):
        subject = _(
            '[%s] Project Budget Alert — %s%% threshold reached'
        ) % (self.name, level)

        h_line = ''
        if self.budget_hours:
            h_line = (
                '<tr><td>Hours logged</td>'
                '<td><b>%.2f / %.2f h (%.1f%%)</b></td></tr>'
            ) % (self.spent_hours, self.budget_hours, self.hours_pct)

        a_line = ''
        if self.budget_amount:
            a_line = (
                '<tr><td>Amount spent</td>'
                '<td><b>%s / %s (%.1f%%)</b></td></tr>'
            ) % (self._fmt(self.spent_amount),
                 self._fmt(self.budget_amount),
                 self.amount_pct)

        color = '#dc3545' if level == '100' else '#856404'
        body = '''
<div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
  <h2 style="color:{color};">⚠ Budget Alert: {project}</h2>
  <p>The project <b>{project}</b> has reached <b>{level}%</b> of its budget.</p>
  <table style="border-collapse:collapse;font-size:13px;margin:10px 0;">
    <tr style="background:#f4f4f4;">
      <th style="padding:6px 12px;text-align:left;">Metric</th>
      <th style="padding:6px 12px;text-align:left;">Progress</th>
    </tr>
    {h_line}
    {a_line}
  </table>
  <p>Please review the project budget in Odoo to take corrective action.</p>
</div>
'''.format(
            color=color,
            project=self.name,
            level=level,
            h_line=h_line,
            a_line=a_line,
        )

        for manager in managers:
            if not manager.email:
                continue
            self.env['mail.mail'].create({
                'subject': subject,
                'body_html': body,
                'email_to': manager.email,
                'auto_delete': True,
            }).send()
