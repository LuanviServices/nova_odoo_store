{
    'name': 'Project Budget with Alerts',
    'version': '18.0.1.0.0',
    'summary': (
        'Set hour and monetary budgets per project. Visual progress bars '
        'and color-coded alerts when spending reaches 80% or 100%. '
        'Automatic email notifications to the project manager.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Project/Project',
    'license': 'OPL-1',
    'price': 49.00,
    'currency': 'USD',
    'depends': ['project', 'hr_timesheet', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/project_budget_views.xml',
        'report/project_budget_report.xml',
        'report/project_budget_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
