{
    'name': 'Product Labels with QR Code — Bulk Print',
    'version': '18.0.1.0.0',
    'summary': (
        'Print product labels in bulk with QR code, barcode and configurable '
        'fields. Three label sizes, selectable fields, print from product list, '
        'purchase orders or delivery orders.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'price': 29.00,
    'currency': 'USD',
    'depends': ['stock', 'purchase'],
    'external_dependencies': {'python': ['qrcode']},
    'data': [
        'security/ir.model.access.csv',
        'views/product_label_views.xml',
        'report/product_label_report.xml',
        'report/product_label_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
