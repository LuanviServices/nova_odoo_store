/** @odoo-module */

const { Component } = owl

export class GraficCard extends Component {
    static props = {
        name: String,
        value: [String, Number],
        color: { type: String, optional: true },
        dynamic_color: { type: Boolean, optional: true },
    };

    setup() {
        // Define la función dentro del contexto del componente
        this.toFloat = (value) => parseFloat(value) || 0;
    }
}

GraficCard.template = "lv_personal_wallet.GraficCard"