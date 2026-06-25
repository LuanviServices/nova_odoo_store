import json
from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # ------------------------------------------------------------------
    # Currency helper
    # ------------------------------------------------------------------
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Revenue
    # ------------------------------------------------------------------
    revenue_invoiced = fields.Monetary(
        string='Invoiced Revenue',
        compute='_compute_profitability',
        currency_field='currency_id',
        help='Sum of posted customer invoice lines whose analytic '
             'distribution includes this project\'s analytic account.',
    )
    revenue_to_invoice = fields.Monetary(
        string='Revenue to Invoice',
        compute='_compute_profitability',
        currency_field='currency_id',
        help='Sum of sale order lines linked to this project that have '
             'not yet been fully invoiced.',
    )

    # ------------------------------------------------------------------
    # Costs
    # ------------------------------------------------------------------
    cost_timesheet = fields.Monetary(
        string='Timesheet Cost',
        compute='_compute_profitability',
        currency_field='currency_id',
        help='Hours logged × employee hourly cost rate.',
    )
    cost_purchase = fields.Monetary(
        string='Purchase / Expense Cost',
        compute='_compute_profitability',
        currency_field='currency_id',
        help='Posted vendor bill lines whose analytic distribution '
             'includes this project\'s analytic account.',
    )
    cost_total = fields.Monetary(
        string='Total Cost',
        compute='_compute_profitability',
        currency_field='currency_id',
    )

    # ------------------------------------------------------------------
    # Margin
    # ------------------------------------------------------------------
    margin = fields.Monetary(
        string='Gross Margin',
        compute='_compute_profitability',
        currency_field='currency_id',
    )
    margin_percent = fields.Float(
        string='Margin %',
        compute='_compute_profitability',
        digits=(5, 1),
    )
    timesheet_hours = fields.Float(
        string='Logged Hours',
        compute='_compute_profitability',
        digits=(10, 2),
    )

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    @api.depends(
        'analytic_account_id',
        'timesheet_ids.unit_amount',
        'timesheet_ids.employee_id',
    )
    def _compute_profitability(self):
        for project in self:
            data = project._get_profitability_data()
            project.revenue_invoiced  = data['revenue_invoiced']
            project.revenue_to_invoice = data['revenue_to_invoice']
            project.cost_timesheet    = data['cost_timesheet']
            project.cost_purchase     = data['cost_purchase']
            project.cost_total        = data['cost_timesheet'] + data['cost_purchase']
            project.margin            = data['revenue_invoiced'] - project.cost_total
            project.margin_percent    = (
                (project.margin / data['revenue_invoiced'] * 100.0)
                if data['revenue_invoiced'] else 0.0
            )
            project.timesheet_hours   = data['timesheet_hours']

    def _get_profitability_data(self):
        """
        Return a dict with all profitability figures for this project.
        Called from _compute_profitability and from the PDF report.
        """
        self.ensure_one()
        result = {
            'revenue_invoiced':   0.0,
            'revenue_to_invoice': 0.0,
            'cost_timesheet':     0.0,
            'cost_purchase':      0.0,
            'timesheet_hours':    0.0,
            'timesheet_lines':    [],
            'invoice_lines':      [],
            'purchase_lines':     [],
        }

        analytic = self.analytic_account_id
        company_currency = self.company_id.currency_id

        # -- 1. Revenue: posted customer invoice lines -------------------
        if analytic:
            inv_lines = self.env['account.move.line'].sudo().search([
                ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
                ('move_id.state', '=', 'posted'),
                ('analytic_distribution', 'like', str(analytic.id)),
                ('display_type', 'not in', ('line_section', 'line_note')),
            ])
            for line in inv_lines:
                pct = self._get_analytic_pct(line.analytic_distribution, analytic.id)
                sign = -1 if line.move_id.move_type == 'out_refund' else 1
                amount = line.price_subtotal * pct / 100.0 * sign
                # Convert to company currency if needed
                if line.currency_id != company_currency:
                    amount = line.currency_id._convert(
                        amount, company_currency,
                        self.company_id, line.move_id.invoice_date or fields.Date.today()
                    )
                result['revenue_invoiced'] += amount
                result['invoice_lines'].append({
                    'date':     line.move_id.invoice_date,
                    'ref':      line.move_id.name,
                    'partner':  line.partner_id.name or '',
                    'product':  line.product_id.display_name or line.name or '',
                    'qty':      line.quantity,
                    'price':    line.price_unit,
                    'subtotal': amount,
                    'pct':      pct,
                })

        # -- 2. Revenue to invoice: uninvoiced sale order lines ----------
        sale_lines = self.env['sale.order.line'].sudo().search([
            ('order_id.project_id', '=', self.id),
            ('order_id.state', 'in', ('sale', 'done')),
            ('invoice_status', 'in', ('to invoice', 'no')),
        ])
        for sl in sale_lines:
            result['revenue_to_invoice'] += sl.price_subtotal - sl.untaxed_amount_to_invoice

        # -- 3. Timesheet cost -------------------------------------------
        ts_lines = self.env['account.analytic.line'].sudo().search([
            ('project_id', '=', self.id),
        ])
        for ts in ts_lines:
            hours = ts.unit_amount
            rate = (ts.employee_id.timesheet_cost
                    if ts.employee_id and hasattr(ts.employee_id, 'timesheet_cost')
                    else 0.0)
            cost = hours * rate
            result['cost_timesheet'] += cost
            result['timesheet_hours'] += hours
            result['timesheet_lines'].append({
                'date':     ts.date,
                'employee': ts.employee_id.name or '',
                'task':     ts.task_id.name if ts.task_id else '',
                'desc':     ts.name or '',
                'hours':    hours,
                'rate':     rate,
                'cost':     cost,
            })

        # -- 4. Purchase cost: posted vendor bill lines ------------------
        if analytic:
            bill_lines = self.env['account.move.line'].sudo().search([
                ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
                ('move_id.state', '=', 'posted'),
                ('analytic_distribution', 'like', str(analytic.id)),
                ('display_type', 'not in', ('line_section', 'line_note')),
            ])
            for line in bill_lines:
                pct = self._get_analytic_pct(line.analytic_distribution, analytic.id)
                sign = -1 if line.move_id.move_type == 'in_refund' else 1
                amount = line.price_subtotal * pct / 100.0 * sign
                if line.currency_id != company_currency:
                    amount = line.currency_id._convert(
                        amount, company_currency,
                        self.company_id, line.move_id.invoice_date or fields.Date.today()
                    )
                result['cost_purchase'] += amount
                result['purchase_lines'].append({
                    'date':    line.move_id.invoice_date,
                    'ref':     line.move_id.name,
                    'partner': line.partner_id.name or '',
                    'product': line.product_id.display_name or line.name or '',
                    'amount':  amount,
                    'pct':     pct,
                })

        return result

    @staticmethod
    def _get_analytic_pct(analytic_distribution, account_id):
        """Extract percentage for account_id from the JSON distribution dict."""
        if not analytic_distribution:
            return 100.0
        try:
            dist = (
                json.loads(analytic_distribution)
                if isinstance(analytic_distribution, str)
                else analytic_distribution
            )
            return float(dist.get(str(account_id), 0.0))
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Action buttons
    # ------------------------------------------------------------------

    def action_view_profitability(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Project Profitability',
            'res_model': 'project.project',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [
                (self.env.ref(
                    'lv_nova_project_profitability'
                    '.view_project_profitability_form'
                ).id, 'form'),
            ],
        }

    def action_print_profitability(self):
        self.ensure_one()
        return self.env.ref(
            'lv_nova_project_profitability.action_report_project_profitability'
        ).report_action(self)

    def _fmt(self, amount):
        """Format monetary amount for use in QWeb templates."""
        c = self.company_id.currency_id
        sign = '-' if amount < 0 else ''
        formatted = '{:,.2f}'.format(abs(amount))
        if c.position == 'before':
            return '{}{}\u00a0{}'.format(sign, c.symbol, formatted)
        return '{}{}\u00a0{}'.format(sign, formatted, c.symbol)
