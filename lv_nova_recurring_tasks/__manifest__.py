{
    'name': 'Recurring Tasks Manager',
    'version': '18.0.1.0.0',
    'summary': (
        'Create recurring task templates (daily, weekly, monthly, '
        'quarterly, yearly) and let Odoo auto-generate the task instances. '
        'Dashboard shows overdue, due today and upcoming tasks. Track '
        'completion rate per template over time.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Productivity',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/recurring_task_views.xml',
        'report/recurring_task_report.xml',
        'report/recurring_task_template_qweb.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
