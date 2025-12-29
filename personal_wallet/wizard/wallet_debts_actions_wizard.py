
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WalletDebtsActionWizard(models.TransientModel):
    _name = 'wallet.debts.actions.wizard'
    _description = "Debts Action Wizard"

    actions = fields.Selection([('forgive_debt', 'Forgive Debt'), ('settle_debt', 'Settle Debt'), ('postpone_debt', 'Postpone Debt')])
    debt_id = fields.Many2one('wallet.debts', help='Selectd debts to perform the action on', required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=False, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date()
    wallet_account_id = fields.Many2one('wallet.account', string='Account', help="Account where the debt is recorded")
    expiration_date = fields.Date(string="Expiration date", help="Date when the debt expire")
    payment_date = fields.Date(help="Date when the payment will be made")
    payment_amount = fields.Monetary(help="Amount to be paid", currency_field='currency_id')
    description = fields.Text()
    days = fields.Integer(help="Number of days that the user wishes to postpone the debt due date", default=0)
    amount_debt = fields.Monetary(compute='_compute_amount_debt', currency_field='currency_id')
    amount_paid = fields.Monetary(compute='_compute_amount_debt', currency_field='currency_id')
    debt_type = fields.Selection([('income', 'Income'), ('expense', 'Expense')], required=True)
    amount_residual = fields.Monetary(compute='_compute_amount_debt', currency_field='currency_id')
    amount = fields.Monetary(default=0.00, currency_field='currency_id')
    exist_transaction = fields.Boolean(string="Exist Transaction", default=False, help="Indicates if the debt has an existing transaction")
    transaction_id = fields.Many2one('wallet.transaction', string="Transaction", help="Transaction related to the debt")

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)

        if 'debt_id' in fields_list and 'debt_id' not in result:
            debt_id = self._context.get('active_ids', [])
            if any(debts.state not in ['active', 'overdue'] for debts in self.env['wallet.debts'].browse(debt_id)):
                raise UserError(_("You cannot perform the following action on debts that are not active"))

            # Cargamos la cuenta de la deuda si solo hay una deuda seleccionada
            if len(debt_id) == 1:
                debt = self.env['wallet.debts'].browse(debt_id[0])
                result['wallet_account_id'] = debt.wallet_account.id
                result['expiration_date'] = debt.end_date
                result['date'] = fields.Date.today()
                result['debt_type'] = 'expense' if debt.debt_type == 'pay' else 'income'

            result['debt_id'] = debt_id[0] if debt_id else False

        if 'actions' in fields_list and 'actions' not in result:
            action = self._context.get('debt_action')
            result['actions'] = action

        return result

    @api.depends('debt_id', 'amount', 'amount_debt', 'payment_amount')
    def _compute_amount_debt(self):
        for wizard in self:
            debt_type = wizard.debt_type
            if debt_type == 'expense':
                wizard.amount_debt = wizard.debt_id.amount if wizard.debt_id else 0.0
                wizard.amount_paid = round(wizard.debt_id.amount_paid + wizard.payment_amount, 2) if wizard.debt_id else 0.0
                wizard.amount_residual = round(wizard.amount_paid - abs(wizard.debt_id.amount), 2) if wizard.debt_id else 0.0
            else:
                wizard.amount_debt = abs(wizard.debt_id.amount) if wizard.debt_id else 0.0
                wizard.amount_paid = round(-(abs(wizard.debt_id.amount_paid) + abs(wizard.payment_amount)), 2) if wizard.debt_id else 0.0
                wizard.amount_residual = round(abs(wizard.debt_id.amount) - abs(wizard.amount_paid), 2) if wizard.debt_id else 0.0

    @api.onchange('days')
    def _onchange_pospone_days(self):
        for wizard in self:
            if wizard.days < 0:
                raise UserError(_("The number of days to postpone cannot be negative."))

    # @api.onchange('payment_amount')
    # def onchange_payment_amount(self):
    #     if self.amount_debt < 0 and self.payment_amount:
    #         self.payment_amount = self.payment_amount * -1

    @api.onchange('transaction_id')
    def _onchange_transaction_id(self):
        for wizard in self:
            if wizard.transaction_id:
                wizard.payment_amount = abs(wizard.transaction_id.amount)
            else:
                wizard.payment_amount = 0.0

    def action_date_postpone(self):
        """ Posponer Deudas """

        for wizard in self:
            if wizard.days <= 0:
                raise UserError(_("The number of days to postpone must be greater than zero."))
            debt = wizard.debt_id

            new_date = fields.Date.add(debt.end_date, days=wizard.days)
            debt.write({
                'end_date': new_date,
                'state': 'active',
                'payment_status': 'pending',
            })

            debt.message_post(
                body=Markup(
                    _("The debt has been postponed by <b> %(days)s days </b>. For the following reason : <br/> <b> %(reason)s </b>") % {'days': wizard.days, 'reason': wizard.description or ''}
                )
            )

        return {'type': 'ir.actions.act_window_close'}

    def action_forgive_debt(self):
        """  Perdonar deudas """
        for wizard in self:
            debt = wizard.debt_id
            debt.write({
                'payment_status': 'forgiven',
                'state': 'closed',
            })
            # Registramos constancia en la deuda
            debt.message_post(
                body=_(
                    "The debt has been <b>forgiven</b>.<br/>Reason: <b>%s</b>"
                ) % (wizard.description or '')
            )
            origin_transaction = False
            if debt.debt_type == 'receive':
                origin_transaction = self.env['wallet.transaction'].search([('debt_id', '=', debt.id),('amount', '<', 0.00)])
            else:
                origin_transaction = self.env['wallet.transaction'].search([('debt_id', '=', debt.id),('amount', '>', 0.00)])
            # Registramos constancia en la transacción de origen
            if origin_transaction:
                old_desc = origin_transaction.description or ""
                new_desc = _("%s | Debt forgiven: %s") % (
                    old_desc,
                    wizard.description or _("No reason provided")
                )
                origin_transaction.write({
                    'description': new_desc
                })
                # dejamos constancia en el chatter tambien
                origin_transaction.message_post(
                    body=_("Debt forgiven: %s") % (wizard.description or _("No reason provided"))
                )

        return {'type': 'ir.actions.act_window_close'}

    def action_settle_debt(self):
        for wizard in self:
            debt = wizard.debt_id
            self._validate_settlement(wizard, debt)
            transaction = self._get_or_create_transaction(wizard, debt)
            self._update_debt_status(debt)
            self._log_messages(wizard, debt, transaction)

        return {'type': 'ir.actions.act_window_close'}

    # ---------------------------
    # Métodos privados auxiliares
    # ---------------------------

    def _validate_settlement(self, wizard, debt):
        """Valida que la deuda y los datos del wizard sean correctos para liquidación."""
        if wizard.transaction_id and wizard.payment_amount <= 0:
            wizard.payment_amount = wizard.transaction_id.amount
        validations = [
            (debt.payment_status not in ['pending', 'partial'],
             _("You can only settle debts that are pending or partially paid.")),
            (abs(wizard.payment_amount) <= 0,
             _("The payment amount must be greater than zero.")),
            (abs(wizard.payment_amount) > abs(debt.amount),
             _("The payment amount cannot exceed the debt amount.")),
            ((wizard.amount_residual < 0 and wizard.debt_type == 'income') or (wizard.amount_residual > 0 and wizard.debt_type == 'expense'),
             _("The payment amount cannot exceed the residual amount of the debt.")),
            (not wizard.wallet_account_id,
             _("You must select a wallet account to settle the debt.")),
        ]
        for condition, error_msg in validations:
            if condition:
                raise UserError(error_msg)

    def _get_or_create_transaction(self, wizard, debt):
        """Obtiene transacción existente o crea una nueva para la liquidación."""
        if wizard.exist_transaction and wizard.transaction_id:
            transaction = wizard.transaction_id
            extra_validations = [
                (abs(transaction.amount) > wizard.payment_amount,
                 _("The transaction amount cannot exceed the payment amount.")),
                (wizard.amount_residual > 0 and abs(transaction.amount) > wizard.amount_residual,
                 _("The transaction amount cannot exceed the residual amount of the debt."))
            ]
            for condition, error_msg in extra_validations:
                if condition:
                    raise UserError(error_msg)
            transaction.debt_id = debt.id
            return transaction
        else:
            return debt.create_debt_transaction({
                'description': wizard.description or _("Debt Settlement"),
                'date': wizard.date,
                'amount': wizard.payment_amount,
                'wallet_account': wizard.wallet_account_id.id,
            })

    def _update_debt_status(self, debt):
        """Actualiza el estado y el pago de la deuda."""
        is_fully_paid = abs(debt.amount) == abs(debt.amount_paid)
        debt.write({
            'payment_status': 'liquidated' if is_fully_paid else 'partial',
            'state': 'closed' if is_fully_paid else 'active',
        })

    def _log_messages(self, wizard, debt, transaction):
        """Registra mensajes en la transacción y la deuda."""
        transaction.message_post(
            body=_("Debt settled with an amount of %s.") % (wizard.payment_amount)
        )
        debt.message_post(
            body=_("The debt has been settled with an amount of %s. With transaction %s")
            % (wizard.payment_amount, transaction.name)
        )
