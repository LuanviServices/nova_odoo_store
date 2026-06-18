{
    'name': 'Withholding Taxes (LATAM) — Customer & Vendor',
    'version': '18.0.1.0.0',
    'summary': (
        'Record income/VAT withholding taxes on customer invoices and '
        'vendor bills, auto-generate the matching journal entry, and '
        'print the withholding certificate. Built for Ecuador, Colombia, '
        'Peru and similar withholding-agent regimes.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Accounting/Localizations',
    'license': 'OPL-1',
    'price': 89.00,
    'currency': 'USD',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_withholding_tax_views.xml',
        'views/account_move_views.xml',
        'report/withholding_certificate_report.xml',
        'report/withholding_certificate_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
