{
    'name': 'Overtime & Time Bank from Attendance',
    'version': '18.0.1.0.0',
    'summary': (
        'Detect overtime automatically from check-in/check-out attendance, '
        'approve it, route it to payment or to a time bank, and let '
        'employees consume banked hours later.'
    ),
    'description': 'See static/description/index.html',
    'author': 'Luanvi Services',
    'website': 'https://www.luanviservices.com',
    'support': 'luanviservicesinfo@gmail.com',
    'category': 'Human Resources/Attendances',
    'license': 'OPL-1',
    'price': 79.00,
    'currency': 'USD',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_overtime_line_views.xml',
        'views/hr_employee_views.xml',
        'wizard/hr_overtime_compute_wizard_views.xml',
        'report/hr_overtime_report.xml',
        'report/hr_overtime_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
