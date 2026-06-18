{
    'name': 'Sales Commission — Plans, Categories & Tiers',
    'version': '18.0.1.0.0',
    'summary': (
        'Configure commission plans by product category, trigger on order '
        'confirmation or invoice payment, and track every commission line '
        'per salesperson with a bulk "mark as paid" wizard.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Sales/Sales',
    'license': 'OPL-1',
    'price': 69.00,
    'currency': 'USD',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/sale_commission_plan_views.xml',
        'views/sale_commission_line_views.xml',
        'views/sale_order_views.xml',
        'views/res_users_views.xml',
        'wizard/sale_commission_payment_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
