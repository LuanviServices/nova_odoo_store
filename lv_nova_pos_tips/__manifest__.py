{
    'name': 'POS Tips — Per-Waiter Report & Tip Tracking',
    'version': '18.0.1.0.0',
    'summary': (
        'Track tips per order in the Point of Sale. Configure a tip product '
        'and suggested percentages, and generate a detailed tip report '
        'per cashier or waiter for any date range.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Point of Sale/Point of Sale',
    'license': 'OPL-1',
    'price': 29.00,
    'currency': 'USD',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'wizard/pos_tip_report_wizard_views.xml',
        'report/pos_tip_report.xml',
        'report/pos_tip_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
