{
    'name': 'Multi-Level Quotation Approval',
    'version': '18.0.1.0.0',
    'summary': (
        'Add configurable approval levels to sale quotations. Trigger by '
        'order amount or discount percentage, assign approvers per level, '
        'and track the full approval history in the chatter.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Sales/Sales',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/sale_approval_rule_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
