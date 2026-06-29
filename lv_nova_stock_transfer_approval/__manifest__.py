{
    'name': 'Inter-Warehouse Transfer Approval',
    'version': '18.0.1.0.0',
    'summary': (
        'Require approval before processing internal stock transfers '
        'between warehouses. The destination warehouse manager is '
        'notified and can approve or reject with a mandatory reason. '
        'Blocked validation until all approvals are granted.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'price': 49.00,
    'currency': 'USD',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/stock_picking_views.xml',
        'wizard/stock_transfer_reject_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
