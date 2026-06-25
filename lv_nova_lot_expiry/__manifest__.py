{
    'name': 'Lot Expiry Dates on Deliveries & Invoices',
    'version': '18.0.1.0.0',
    'summary': (
        'Show lot and serial number expiry dates directly on delivery '
        'orders and customer invoices. Color-coded alerts: expired (red), '
        'expiring soon (orange), OK (green). Included in PDF reports.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'price': 29.00,
    'currency': 'USD',
    'depends': ['stock', 'account', 'product_expiry'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_move_line_views.xml',
        'views/account_move_views.xml',
        'report/stock_picking_report.xml',
        'report/account_invoice_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
