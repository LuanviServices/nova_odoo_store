{
    'name': 'Advanced Excel Export with Templates',
    'version': '18.0.1.0.0',
    'summary': (
        'Export any Odoo list to a beautifully formatted Excel file. '
        'Configure reusable templates per model: custom headers, column '
        'widths, colours, totals row and auto-fit. Works from Sale Orders, '
        'Invoices, Purchase Orders, Inventory and more.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Extra Tools',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['base', 'mail'],
    'external_dependencies': {'python': ['openpyxl']},
    'data': [
        'security/ir.model.access.csv',
        'data/excel_export_template_data.xml',
        'views/excel_export_template_views.xml',
        'wizard/excel_export_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
