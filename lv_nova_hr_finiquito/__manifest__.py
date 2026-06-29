{
    'name': 'Employee Termination & Finiquito (LATAM)',
    'version': '18.0.1.0.0',
    'summary': (
        'Calculate employee termination payments: proportional vacation, '
        '13th/14th month salary, severance notice bonus, indemnification '
        'and reserve funds. Printable finiquito PDF ready for signature. '
        'Configurable for Ecuador, Colombia, Peru and similar regimes.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Human Resources/Employees',
    'license': 'OPL-1',
    'price': 79.00,
    'currency': 'USD',
    'depends': ['hr', 'hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_finiquito_views.xml',
        'views/hr_employee_views.xml',
        'report/hr_finiquito_report.xml',
        'report/hr_finiquito_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
