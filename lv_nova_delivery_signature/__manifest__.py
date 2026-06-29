{
    'name': 'Delivery Signature (Mobile & Tablet)',
    'version': '18.0.1.0.0',
    'summary': (
        'Capture a customer or driver signature directly on the delivery '
        'order using the touchscreen. Signature is stored on the picking, '
        'shown on the Delivery Slip PDF, and can be required before '
        'the delivery is validated.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        'report/stock_picking_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
