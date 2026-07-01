from collections import defaultdict
from odoo import api, fields, models, _


class ArAgingWizard(models.TransientModel):
    _name = 'ar.aging.wizard'
    _description = 'Accounts Receivable Aging Report'

    # -- Filters ---------------------------------------------------------
    as_of_date = fields.Date(
        string='As of Date',
        required=True,
        default=fields.Date.today,
        help='Compute overdue days relative to this date.',
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Customers',
        domain="[('customer_rank','>',0)]",
        help='Leave empty to include all customers.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    include_undue = fields.Boolean(
        string='Include Current (not yet due)',
        default=True,
    )

    # -- Bucket configuration -------------------------------------------
    bucket_1 = fields.Integer(string='Bucket 1 upper (days)', default=30)
    bucket_2 = fields.Integer(string='Bucket 2 upper (days)', default=60)
    bucket_3 = fields.Integer(string='Bucket 3 upper (days)', default=90)

    # ------------------------------------------------------------------
    # Computation engine
    # ------------------------------------------------------------------

    def _get_bucket_labels(self):
        return [
            _('Current'),
            _('1-%d days') % self.bucket_1,
            _('%d-%d days') % (self.bucket_1 + 1, self.bucket_2),
            _('%d-%d days') % (self.bucket_2 + 1, self.bucket_3),
            _('%d+ days') % (self.bucket_3 + 1),
        ]

    def _assign_bucket(self, days_overdue):
        """Return 0=current, 1,2,3,4 for each aging bucket."""
        if days_overdue <= 0:
            return 0
        if days_overdue <= self.bucket_1:
            return 1
        if days_overdue <= self.bucket_2:
            return 2
        if days_overdue <= self.bucket_3:
            return 3
        return 4

    def get_aging_data(self):
        """
        Returns a list of dicts, one per customer:
        {
          'partner': res.partner,
          'buckets': [b0, b1, b2, b3, b4],   # amounts
          'total': float,
          'oldest_days': int,                  # max days overdue
          'risk': 'ok'|'warning'|'critical',
          'lines': [{'name', 'ref', 'date', 'due_date', 'days', 'amount', 'bucket'}]
        }
        """
        self.ensure_one()
        as_of = self.as_of_date

        domain = [
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('company_id', '=', self.company_id.id),
            ('date_maturity', '!=', False),
            ('amount_residual', '!=', 0),
        ]
        if self.partner_ids:
            domain.append(
                ('partner_id', 'in', self.partner_ids.ids)
            )

        move_lines = self.env['account.move.line'].sudo().search(
            domain, order='partner_id, date_maturity asc'
        )

        by_partner = defaultdict(list)
        for ml in move_lines:
            due_date = ml.date_maturity
            days_overdue = (as_of - due_date).days if due_date else 0
            if days_overdue < 0 and not self.include_undue:
                continue
            amount = ml.amount_residual
            bucket = self._assign_bucket(days_overdue)
            by_partner[ml.partner_id].append({
                'name':     ml.move_id.name or '',
                'ref':      ml.move_id.ref or '',
                'date':     ml.move_id.invoice_date or ml.date,
                'due_date': due_date,
                'days':     max(days_overdue, 0),
                'amount':   amount,
                'bucket':   bucket,
            })

        rows = []
        for partner, lines in sorted(
            by_partner.items(), key=lambda kv: kv[0].name or ''
        ):
            buckets = [0.0, 0.0, 0.0, 0.0, 0.0]
            for line in lines:
                buckets[line['bucket']] += line['amount']
            total = sum(buckets)
            oldest = max((l['days'] for l in lines), default=0)
            if oldest > self.bucket_3:
                risk = 'critical'
            elif oldest > self.bucket_2:
                risk = 'warning'
            else:
                risk = 'ok'
            rows.append({
                'partner':     partner,
                'buckets':     buckets,
                'total':       total,
                'oldest_days': oldest,
                'risk':        risk,
                'lines':       lines,
            })

        return rows

    def get_totals(self, rows):
        totals = [0.0, 0.0, 0.0, 0.0, 0.0]
        for row in rows:
            for i in range(5):
                totals[i] += row['buckets'][i]
        return totals

    def _fmt(self, amount):
        c = self.company_id.currency_id
        if amount == 0:
            return '—'
        s = '{:,.2f}'.format(abs(amount))
        return (c.symbol + '\u00a0' + s if c.position == 'before'
                else s + '\u00a0' + c.symbol)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'lv_nova_ar_aging.action_report_ar_aging'
        ).report_action(self)

    def action_view_overdue_invoices(self):
        """Open the list of all overdue invoices for a quick review."""
        self.ensure_one()
        domain = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'in_payment')),
            ('company_id', '=', self.company_id.id),
            ('invoice_date_due', '<', str(self.as_of_date)),
        ]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Overdue Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': domain,
        }
