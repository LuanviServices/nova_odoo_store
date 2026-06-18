{
    'name': 'Customer Account Statement — Portal & PDF',
    'version': '18.0.1.0.0',
    'summary': (
        'Account statement per customer: pending invoices, payments and '
        'running balance. Print PDF, send by email, and self-service portal.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Accounting/Accounting',
    'license': 'OPL-1',
    'price': 35.00,
    'currency': 'USD',
    'depends': ['account', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/customer_statement_wizard_views.xml',
        'views/res_partner_views.xml',
        'report/customer_statement_report.xml',
        'report/customer_statement_template.xml',
        'templates/portal_statement.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
