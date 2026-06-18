import base64
from odoo import api, fields, models, _


class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Account Statement'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain="[('customer_rank', '>', 0)]",
    )
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.today,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # -------------------------------------------------------------------------
    # Data computation
    # -------------------------------------------------------------------------

    def _receivable_domain(self, date_start=None, date_end=None):
        """Build domain for receivable journal items."""
        domain = [
            ('partner_id', 'child_of', self.partner_id.id),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        if date_start:
            domain.append(('date', '>=', date_start))
        if date_end:
            domain.append(('date', '<=', date_end))
        return domain

    def get_opening_balance(self):
        """Sum of all posted receivable entries strictly before date_from."""
        self.ensure_one()
        if not self.date_from:
            return 0.0
        domain = [
            ('partner_id', 'child_of', self.partner_id.id),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('date', '<', self.date_from),
        ]
        lines = self.env['account.move.line'].search(domain)
        return sum(ln.debit - ln.credit for ln in lines)

    def get_lines(self):
        """
        Return a list of dicts representing journal items in the period,
        including a running balance column.
        """
        self.ensure_one()
        domain = self._receivable_domain(
            date_start=self.date_from,
            date_end=self.date_to,
        )
        move_lines = self.env['account.move.line'].search(
            domain, order='date asc, move_id asc, id asc'
        )
        today = fields.Date.today()
        balance = self.get_opening_balance()
        result = []
        for ml in move_lines:
            balance += ml.debit - ml.credit
            result.append({
                'date': ml.date,
                'move_name': ml.move_id.name or '',
                'ref': ml.ref or ml.move_id.ref or '',
                'label': ml.name or ml.move_id.payment_reference or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': balance,
                'due_date': ml.date_maturity,
                'is_overdue': bool(
                    ml.date_maturity
                    and ml.date_maturity < today
                    and ml.amount_residual > 0
                ),
            })
        return result

    def get_summary(self, lines=None):
        """Return aggregate totals for the statement."""
        self.ensure_one()
        if lines is None:
            lines = self.get_lines()
        opening = self.get_opening_balance()
        total_debit = sum(ln['debit'] for ln in lines)
        total_credit = sum(ln['credit'] for ln in lines)
        return {
            'opening_balance': opening,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'closing_balance': opening + total_debit - total_credit,
        }

    def _fmt(self, amount):
        """
        Format a float amount as a human-readable currency string.
        Used from QWeb templates via doc._fmt(value).
        """
        currency = self.company_id.currency_id
        sign = '-' if amount < 0 else ''
        formatted = '{:,.2f}'.format(abs(amount))
        if currency.position == 'before':
            return '{}{}\u00a0{}'.format(sign, currency.symbol, formatted)
        return '{}{}\u00a0{}'.format(sign, formatted, currency.symbol)

    def _email_body_html(self):
        """Build a plain HTML body for the send-email compose wizard."""
        if self.date_from:
            period = _(
                'From %(from)s to %(to)s',
                from_=str(self.date_from),
                to=str(self.date_to),
            )
        else:
            period = _('Up to %s') % str(self.date_to)
        return (
            '<p>Dear {name},</p>'
            '<p>Please find attached your account statement ({period}).</p>'
            '<p>If you have any questions, please do not hesitate to contact us.</p>'
            '<p>Best regards,<br/>{company}</p>'
        ).format(
            name=self.partner_id.name,
            period=period,
            company=self.company_id.name,
        )

    # -------------------------------------------------------------------------
    # Button actions
    # -------------------------------------------------------------------------

    def action_print_pdf(self):
        """Trigger the PDF report and return it to the browser."""
        self.ensure_one()
        return self.env.ref(
            'customer_statement_portal.action_report_customer_statement'
        ).report_action(self)

    def action_send_email(self):
        """
        Generate the PDF, attach it, and open the mail compose wizard
        pre-filled with the partner's email address.
        """
        self.ensure_one()
        # Render the PDF
        pdf_content, _mime = self.env['ir.actions.report']._render_qweb_pdf(
            'customer_statement_portal.action_report_customer_statement',
            res_ids=[self.id],
        )
        filename = 'Account_Statement_{}.pdf'.format(
            self.partner_id.name.replace(' ', '_')
        )
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode(),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        ctx = {
            'default_model': self._name,
            'default_res_ids': [self.id],
            'default_partner_ids': [(4, self.partner_id.id)],
            'default_attachment_ids': [(4, attachment.id)],
            'default_subject': _(
                'Account Statement — %s'
            ) % self.partner_id.name,
            'default_body': self._email_body_html(),
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'target': 'new',
            'context': ctx,
        }
