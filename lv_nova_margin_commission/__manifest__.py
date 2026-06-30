{
    'name': 'Margin-Based Commission Rules',
    'version': '18.0.1.0.0',
    'summary': (
        'Pay sales commission based on profit margin tiers, not just sales '
        'volume. Define brackets (e.g. 0-10% margin = 1%, 10-25% = 4%, '
        '25%+ = 8%) so reps are rewarded for protecting margin, not just '
        'closing deals at any discount.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Sales/Sales',
    'license': 'OPL-1',
    'price': 69.00,
    'currency': 'USD',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/margin_commission_scale_views.xml',
        'views/sale_order_views.xml',
        'views/res_users_views.xml',
        'report/margin_commission_report.xml',
        'report/margin_commission_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
