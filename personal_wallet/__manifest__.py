# -*- coding: utf-8 -*-
# © 2024 Luanvi (luanviservicesinfo@gmail.com)
# License OPL-1.0

{
    'name': 'Personal Wallet',
    'version': '18.0.1.3.0',
    'category': 'Accounting/Personal Finance',
    'summary': 'Control your personal income and expenses',
    'description': """
Manage your personal finances directly in Odoo.

Track income and expenses, debts and financial goals
with a clean dashboard and automated calculations.
""",
    'author': 'Luanvi Services',
    'company': 'Luanvi Services',
    'maintainer': 'Luanvi Services',
    'website': 'https://luanviservices.com',
    'depends': [
        'contacts',
        'account',
        'board'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/wallet.category.csv',
        'data/ir_cron_data.xml',
        'views/settings_views.xml',
        'views/wallet_views.xml',
        'views/wallet_account_views.xml',
        'views/wallet_transaction_views.xml',
        'views/wallet_debts_views.xml',
        'views/wallet_budget_views.xml',
        'views/wallet_dashboard.xml',
        'views/res_partner_views.xml',
        'wizard/wallet_debts_actions_wizard_views.xml',
        'views/wallet_menu_items.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'assets': {
        'web.assets_backend': [
            'lv_personal_wallet/static/src/components/**/*.js',
            'lv_personal_wallet/static/src/components/**/*.xml',
        ]
    },
    'images': ['static/description/banner.png','static/description/icon.png'],
    'price': 12.00,
    'currency': 'USD',
}
