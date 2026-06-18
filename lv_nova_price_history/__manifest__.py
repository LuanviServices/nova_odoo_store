{
    'name': 'Customer Price History on Quotations',
    'version': '18.0.1.0.0',
    'summary': (
        'See the last price charged to each customer for each product '
        'directly on the quotation line, plus full price history popup.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Sales/Sales',
    'license': 'OPL-1',
    'price': 25.00,
    'currency': 'USD',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
