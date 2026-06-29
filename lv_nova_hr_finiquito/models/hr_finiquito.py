from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrFiniquito(models.Model):
    _name = 'hr.finiquito'
    _description = 'Employee Termination Calculation (Finiquito)'
    _order = 'date_end desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        readonly=True,
        default='New',
        copy=False,
    )
    state = fields.Selection(
        [
            ('draft',     'Draft'),
            ('confirmed', 'Confirmed'),
            ('paid',      'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        copy=False,
    )

    # -- Employee & contract -------------------------------------------
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        states={'confirmed': [('readonly', True)]},
    )
    contract_id = fields.Many2one(
        'hr.contract', string='Contract',
        domain="[('employee_id','=',employee_id)]",
        states={'confirmed': [('readonly', True)]},
    )
    date_start = fields.Date(
        string='Contract Start',
        required=True,
        states={'confirmed': [('readonly', True)]},
    )
    date_end = fields.Date(
        string='Termination Date',
        required=True,
        default=fields.Date.today,
        states={'confirmed': [('readonly', True)]},
    )
    termination_type = fields.Selection(
        [
            ('desahucio',       'Employer Termination (Desahucio)'),
            ('visto_bueno',     'Justified Dismissal (Visto Bueno)'),
            ('renuncia',        'Voluntary Resignation'),
            ('mutual',          'Mutual Agreement'),
            ('contract_end',    'End of Fixed-Term Contract'),
        ],
        string='Termination Type',
        required=True,
        default='renuncia',
        states={'confirmed': [('readonly', True)]},
    )

    # -- Salary basis --------------------------------------------------
    last_monthly_salary = fields.Monetary(
        string='Last Monthly Salary',
        required=True,
        currency_field='currency_id',
        states={'confirmed': [('readonly', True)]},
    )
    sbu = fields.Monetary(
        string='Basic Unified Salary (SBU)',
        default=460.00,
        currency_field='currency_id',
        help='Salario Básico Unificado vigente. Used for 14th month calculation.',
        states={'confirmed': [('readonly', True)]},
    )
    pending_vacation_days = fields.Float(
        string='Pending Vacation Days',
        help='Vacation days earned but not yet taken by the employee. '
             'Leave 0 to auto-compute from service time.',
        states={'confirmed': [('readonly', True)]},
    )

    # -- Toggles for components ----------------------------------------
    include_vacation         = fields.Boolean('Vacation',                default=True)
    include_decimotercer     = fields.Boolean('13th Month (Prop.)',       default=True)
    include_decimocuarto     = fields.Boolean('14th Month (Prop.)',       default=True)
    include_desahucio        = fields.Boolean('Severance Notice',         default=True)
    include_indemnizacion    = fields.Boolean('Indemnification',          default=False)
    include_fondos_reserva   = fields.Boolean('Reserve Funds (Prop.)',    default=True)

    # -- Computed service time -----------------------------------------
    service_years = fields.Float(
        string='Years of Service',
        compute='_compute_service_time',
        digits=(5, 2),
    )
    service_months_total = fields.Integer(
        string='Total Months',
        compute='_compute_service_time',
    )
    months_current_year = fields.Integer(
        string='Months in Current Period',
        compute='_compute_service_time',
        help='Months worked since the last anniversary (for proportional components).',
    )
    days_current_year = fields.Integer(
        string='Days in Current Period',
        compute='_compute_service_time',
    )

    # -- Lines & totals ------------------------------------------------
    line_ids = fields.One2many(
        'hr.finiquito.line', 'finiquito_id', string='Components',
        states={'confirmed': [('readonly', True)]},
    )
    total_earnings = fields.Monetary(
        string='Total Earnings',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    total_deductions = fields.Monetary(
        string='Total Deductions',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    total_net = fields.Monetary(
        string='Net to Pay',
        compute='_compute_totals',
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
    notes = fields.Text(string='Notes / Observations')

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------

    @api.depends('date_start', 'date_end')
    def _compute_service_time(self):
        for rec in self:
            if not rec.date_start or not rec.date_end:
                rec.service_years = 0.0
                rec.service_months_total = 0
                rec.months_current_year = 0
                rec.days_current_year = 0
                continue
            rd = relativedelta(rec.date_end, rec.date_start)
            total_months = rd.years * 12 + rd.months
            rec.service_years = round(
                (rec.date_end - rec.date_start).days / 365.0, 2
            )
            rec.service_months_total  = total_months
            rec.months_current_year   = rd.months
            rec.days_current_year     = rd.days

    @api.depends('line_ids.amount', 'line_ids.is_deduction')
    def _compute_totals(self):
        for rec in self:
            earnings   = sum(l.amount for l in rec.line_ids if not l.is_deduction)
            deductions = sum(l.amount for l in rec.line_ids if l.is_deduction)
            rec.total_earnings   = earnings
            rec.total_deductions = deductions
            rec.total_net        = earnings - deductions

    # ------------------------------------------------------------------
    # Onchange auto-fill from contract
    # ------------------------------------------------------------------

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', 'in', ('open', 'close')),
            ], order='date_start desc', limit=1)
            if contract:
                self.contract_id         = contract
                self.date_start          = contract.date_start
                self.last_monthly_salary = contract.wage

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.date_start          = self.contract_id.date_start
            self.last_monthly_salary = self.contract_id.wage

    # ------------------------------------------------------------------
    # Calculation engine
    # ------------------------------------------------------------------

    def _daily_salary(self):
        return self.last_monthly_salary / 30.0

    def _compute_vacation_days(self):
        """
        Ecuador: 15 days per year (1.25 per month).
        We compute days earned in the current period and add pending days.
        """
        earned = self.months_current_year * 1.25
        if self.pending_vacation_days:
            return self.pending_vacation_days
        return round(earned, 2)

    def action_compute(self):
        """Recompute all component lines based on current settings."""
        self.ensure_one()
        if self.state == 'confirmed':
            raise UserError(_('Cannot recompute a confirmed finiquito.'))
        if not self.date_start or not self.date_end:
            raise UserError(_('Please set both the contract start and termination dates.'))
        if self.last_monthly_salary <= 0:
            raise UserError(_('Please enter a valid last monthly salary.'))

        self.line_ids.unlink()
        lines = []
        daily = self._daily_salary()
        months = self.months_current_year
        days   = self.days_current_year

        # 1. Vacaciones proporcionales
        if self.include_vacation:
            vac_days = self._compute_vacation_days()
            vac_amt  = vac_days * daily
            lines.append({
                'name':         _('Proportional Vacation'),
                'component':    'vacation',
                'quantity':     vac_days,
                'unit':         'days',
                'basis':        daily,
                'amount':       vac_amt,
                'formula':      '%s days × $%.2f/day' % (vac_days, daily),
                'is_deduction': False,
            })

        # 2. Décimo tercer sueldo proporcional
        if self.include_decimotercer:
            d13 = (self.last_monthly_salary / 12.0) * months + \
                  (self.last_monthly_salary / 360.0) * days
            lines.append({
                'name':         _('Proportional 13th Month Salary'),
                'component':    'decimotercer',
                'quantity':     months + days / 30.0,
                'unit':         'months',
                'basis':        self.last_monthly_salary / 12.0,
                'amount':       round(d13, 2),
                'formula':      '($%.2f / 12) × %d months + days' % (
                    self.last_monthly_salary, months),
                'is_deduction': False,
            })

        # 3. Décimo cuarto sueldo proporcional (based on SBU)
        if self.include_decimocuarto:
            d14 = (self.sbu / 12.0) * months + (self.sbu / 360.0) * days
            lines.append({
                'name':         _('Proportional 14th Month Salary (SBU)'),
                'component':    'decimocuarto',
                'quantity':     months + days / 30.0,
                'unit':         'months',
                'basis':        self.sbu / 12.0,
                'amount':       round(d14, 2),
                'formula':      '(SBU $%.2f / 12) × %d months + days' % (
                    self.sbu, months),
                'is_deduction': False,
            })

        # 4. Bonificación por desahucio
        if self.include_desahucio and self.termination_type == 'desahucio':
            years = int(self.service_years)
            desahucio = 0.25 * self.last_monthly_salary * max(years, 1)
            lines.append({
                'name':         _('Severance Notice Bonus (Desahucio) 25%'),
                'component':    'desahucio',
                'quantity':     max(years, 1),
                'unit':         'years',
                'basis':        self.last_monthly_salary * 0.25,
                'amount':       round(desahucio, 2),
                'formula':      '25%% × $%.2f × %d year(s)' % (
                    self.last_monthly_salary, max(years, 1)),
                'is_deduction': False,
            })

        # 5. Indemnización por despido intempestivo
        if self.include_indemnizacion and self.termination_type in (
            'desahucio', 'visto_bueno'
        ):
            years = max(int(self.service_years), 1)
            indemnizacion = self.last_monthly_salary * years
            lines.append({
                'name':         _('Indemnification (Unjustified Dismissal)'),
                'component':    'indemnizacion',
                'quantity':     years,
                'unit':         'years',
                'basis':        self.last_monthly_salary,
                'amount':       round(indemnizacion, 2),
                'formula':      '$%.2f × %d year(s)' % (
                    self.last_monthly_salary, years),
                'is_deduction': False,
            })

        # 6. Fondos de reserva proporcional (8.33%, only after 1 year)
        if self.include_fondos_reserva and self.service_years >= 1.0:
            fr = self.last_monthly_salary * 0.0833 * (months + days / 30.0)
            lines.append({
                'name':         _('Proportional Reserve Funds (Fondos de Reserva 8.33%)'),
                'component':    'fondos_reserva',
                'quantity':     months + days / 30.0,
                'unit':         'months',
                'basis':        self.last_monthly_salary * 0.0833,
                'amount':       round(fr, 2),
                'formula':      '8.33%% × $%.2f × %.2f months' % (
                    self.last_monthly_salary, months + days / 30.0),
                'is_deduction': False,
            })

        # Create all lines
        for vals in lines:
            vals['finiquito_id'] = self.id
            self.env['hr.finiquito.line'].create(vals)

        return True

    # ------------------------------------------------------------------
    # State actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_(
                'Please click "Compute Finiquito" before confirming.'
            ))
        seq = self.env['ir.sequence'].next_by_code('hr.finiquito') or '/'
        self.write({'name': seq, 'state': 'confirmed'})
        self.message_post(
            body=_('Finiquito confirmed. Reference: <b>%s</b>. '
                   'Net to pay: <b>%s %s</b>') % (
                self.name,
                self.currency_id.symbol,
                '{:,.2f}'.format(self.total_net),
            ),
            subtype_xmlid='mail.mt_note',
        )

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft', 'name': 'New'})

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            'lv_nova_hr_finiquito.action_report_hr_finiquito'
        ).report_action(self)

    def _fmt(self, amount):
        c = self.currency_id
        s = '{:,.2f}'.format(abs(amount))
        return (c.symbol + '\u00a0' + s if c.position == 'before'
                else s + '\u00a0' + c.symbol)


class HrFiniquitoLine(models.Model):
    _name = 'hr.finiquito.line'
    _description = 'Finiquito Component Line'
    _order = 'is_deduction, id'

    finiquito_id = fields.Many2one(
        'hr.finiquito', required=True, ondelete='cascade',
    )
    name = fields.Char(string='Component', required=True)
    component = fields.Char(string='Type Code')
    quantity = fields.Float(string='Quantity', digits=(10, 4))
    unit = fields.Char(string='Unit')
    basis = fields.Float(string='Rate/Basis', digits=(10, 4))
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id', required=True,
    )
    formula = fields.Char(string='Calculation')
    is_deduction = fields.Boolean(string='Deduction', default=False)
    currency_id = fields.Many2one(related='finiquito_id.currency_id', store=True)
