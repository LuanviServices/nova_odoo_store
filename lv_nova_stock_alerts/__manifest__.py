{
    'name': 'Stock Alerts Dashboard — Reorder & Quick PO',
    'version': '18.0.1.0.0',
    'summary': (
        'Visual dashboard of products below minimum stock. Color-coded '
        'by alert level, supplier lead time, and one-click purchase order '
        'creation grouped by vendor.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/stock_alert_views.xml',
        'wizard/stock_alert_create_po_wizard_views.xml',
        'report/stock_alert_report.xml',
        'report/stock_alert_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
