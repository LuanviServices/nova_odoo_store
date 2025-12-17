/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
import { onWillStart, useState } from "@odoo/owl"
import { _t } from "@web/core/l10n/translation";
import { GraficCard } from './grafic_card/grafic_card'
import { ChartRender } from './chart_render/chart_render'

const { Component } = owl

export class WalletDashboard extends Component {
    setup() { 
        this.orm = useService("orm")
        // Obtener mes y año actuales
        const today = new Date();
        const currentMonth = today.getMonth() + 1; // (0-11) => +1
        const currentYear = today.getFullYear();
        this.state = useState({
            summary: {
                transactions: 0,
                expenses: 0,
                revenue: 0,
                accounts: 0,
            },
            selectedMonth: currentMonth,
            selectedYear: currentYear,
            availableYears: [],
            top_expenses: [],
            top_expenses_accounts: [],
            top_expenses_transactions: [],
            top_incomes: [],
            top_incomes_accounts: [],
            top_incomes_transactions: [],
            top_pays: [],
            top_receives: [],
            txt_1: _t("Transactions"),
            txt_2: _t("Expenses"),
            txt_3: _t("Revenue"),
            txt_4: _t("General"),
            // Ingresos
            txt_5: _t("Top Incomes Report"),
            txt_6: _t("Accounts Report"),
            txt_7: _t("Monthly Transactions Report"),
            txt_8: _t("Debts Report"),
            // Gastos
            txt_9: _t("Top Expenses Report"),
        })
        // Funcion para formatear los montos
        function formatAmount(value) {
            // Redondear el valor a dos decimales
            const roundedValue = value.toFixed(2);
            // Convertir el número en una cadena con comas como separadores de miles
            return parseFloat(roundedValue).toLocaleString();
        }
        // Carga de resumen
        const loadSummaryData = async (month, year) => {
            const summary = await this.orm.call("wallet.transaction","get_summary_data", [month, year])
            this.state.summary = {
                transactions: summary.transactions,
                expenses: formatAmount(summary.expenses),
                revenue: formatAmount(summary.revenue),
                accounts: formatAmount(summary.accounts),
            }
        }
        // Carga de datos de graficos
        const loadTopChatsData = async (month, year) => {
            const result = await this.orm.call("wallet.transaction","get_top_chart_data", [month, year]);
            // Gastos
            this.state.topExpenses = result.top_expenses;
            this.state.topExpensesAccounts = result.top_expenses_accounts;
            this.state.topExpensesTransactions = result.top_expenses_transactions;
            // Ingresos
            this.state.topIncomes = result.top_incomes;
            this.state.topIncomnesAccounts = result.top_incomes_accounts;
            this.state.topIncomesTransactions = result.top_incomes_transactions;
            // Deudas
            const result_debts = await this.orm.call("wallet.debts","get_top_chart_data", [month, year]);
            this.state.topPays = result_debts.top_pays;
            this.state.topReceives = result_debts.top_receives;
        }
        // Iniciar el componente
        onWillStart(async () => {
            // Generamos lista de años (ultimos 5 años y el actual)
            this.state.availableYears = Array.from({ length: 6 }, (_, i) => currentYear - 5 + i);
            // cargamos los datos iniciales
            loadSummaryData(this.state.selectedMonth, this.state.selectedYear)  
            loadTopChatsData(this.state.selectedMonth, this.state.selectedYear)
        })
        // Evento para actualizar los graficos al cambiar mes o año
        this.updatePeriod = (event) => {
            // Recargamos los datos
            loadSummaryData(this.state.selectedMonth, this.state.selectedYear)
            loadTopChatsData(this.state.selectedMonth, this.state.selectedYear)
        }
    }
}

WalletDashboard.template = "lv_personal_wallet.LvNovaWalletDashboard"
WalletDashboard.components = { GraficCard, ChartRender }

registry.category("actions").add("lv_personal_wallet.wallet_dashboard", WalletDashboard)