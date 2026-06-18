from odoo import fields as odoo_fields, http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerStatementPortal(CustomerPortal):
    """Extends the customer portal with an account-statement page."""

    # ------------------------------------------------------------------
    # Portal home — adds "Account Statement" entry to the home menu
    # ------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # We add no count badge; the entry is always visible for logged-in
        # customers.  Template handles the menu entry via template inheritance.
        return values

    # ------------------------------------------------------------------
    # /my/statement — HTML view
    # ------------------------------------------------------------------

    @http.route(['/my/statement'], type='http', auth='user', website=True)
    def portal_my_account_statement(self, date_from=None, date_to=None, **kw):
        partner = request.env.user.partner_id

        wizard_vals = {
            'partner_id': partner.id,
            'date_to': date_to or str(odoo_fields.Date.today()),
            'company_id': request.env.company.id,
        }
        if date_from:
            wizard_vals['date_from'] = date_from

        wizard = request.env['customer.statement.wizard'].sudo().create(wizard_vals)
        lines = wizard.get_lines()
        summary = wizard.get_summary(lines=lines)

        values = {
            'partner': partner,
            'lines': lines,
            'summary': summary,
            'wizard': wizard,
            'date_from': date_from or '',
            'date_to': date_to or str(odoo_fields.Date.today()),
            'page_name': 'statement',
        }
        return request.render(
            'customer_statement_portal.portal_my_statement', values
        )

    # ------------------------------------------------------------------
    # /my/statement/pdf — download PDF
    # ------------------------------------------------------------------

    @http.route(['/my/statement/pdf'], type='http', auth='user', website=True)
    def portal_my_statement_pdf(self, date_from=None, date_to=None, **kw):
        partner = request.env.user.partner_id

        wizard_vals = {
            'partner_id': partner.id,
            'date_to': date_to or str(odoo_fields.Date.today()),
            'company_id': request.env.company.id,
        }
        if date_from:
            wizard_vals['date_from'] = date_from

        wizard = request.env['customer.statement.wizard'].sudo().create(wizard_vals)

        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'customer_statement_portal.action_report_customer_statement',
            res_ids=[wizard.id],
        )
        filename = 'Account_Statement_{}.pdf'.format(
            partner.name.replace(' ', '_')
        )
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="{}"'.format(filename)),
            ],
        )
