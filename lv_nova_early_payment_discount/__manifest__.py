{
    'name': 'Early Payment Discounts — Auto-Apply on Invoice Payment',
    'version': '18.0.1.0.0',
    'summary': (
        'Configure a cash discount % and deadline on payment terms. '
        'Invoices show the discounted amount prominently. When the '
        'customer pays within the discount window the discount journal '
        'entry is created automatically.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Accounting/Accounting',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_term_views.xml',
        'views/account_move_views.xml',
        'wizard/early_discount_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
