{
    'name': 'Project Profitability Report',
    'version': '18.0.1.0.0',
    'summary': (
        'Per-project profitability dashboard: compare invoiced revenue '
        'against timesheet costs, vendor bills and expenses linked via '
        'analytic accounts. Drill down by cost type and print a PDF summary.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Project/Project',
    'license': 'OPL-1',
    'price': 59.00,
    'currency': 'USD',
    'depends': ['project', 'account', 'hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_profitability_views.xml',
        'views/project_project_views.xml',
        'report/project_profitability_report.xml',
        'report/project_profitability_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
