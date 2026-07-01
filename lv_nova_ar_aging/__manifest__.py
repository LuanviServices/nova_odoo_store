{
    'name': 'Accounts Receivable Aging Report',
    'version': '18.0.1.0.0',
    'summary': (
        'Classic AR aging report: outstanding invoices bucketed by overdue '
        'days (Current, 1-30, 31-60, 61-90, 91+). Per-customer breakdown, '
        'risk-level colour coding, configurable buckets and printable PDF.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Accounting/Accounting',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/ar_aging_wizard_views.xml',
        'report/ar_aging_report.xml',
        'report/ar_aging_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
