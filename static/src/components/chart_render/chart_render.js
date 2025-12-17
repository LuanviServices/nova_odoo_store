/** @odoo-module */

import { loadJS } from "@web/core/assets"
const { Component, useRef, onMounted, onWillStart, onWillUpdateProps } = owl;

export class ChartRender extends Component {
  setup() {
    this.chartRef = useRef("chart");
    this.chartInstance = null; // Guardamos la instancia del gráfico

    onWillStart(async () => {
      await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js");
    });

    onMounted(() => this.renderChart());

    onWillUpdateProps((nextProps) => {
      if (nextProps.data !== this.props.data) {
        this.renderChart(nextProps);
      }
    });
  }
  // Función para renderizar el gráfico
  renderChart(props = this.props) {
    const chartElement = this.chartRef.el;
    const ctx = chartElement.getContext("2d");
  
    // Si no hay datos, aún renderizamos el gráfico vacío
    if (!props.data || !Array.isArray(props.data) || props.data.length === 0) {
      const labels = ['']; // Un solo espacio para etiquetas vacías
      let values = [0];   // Valor vacío para datos
      if (props.type === "pie" || props.type === "doughnut") {
        values = [100]; // Para gráficos de tipo "pie" o "doughnut", aseguramos que haya un valor
      }
  
      // Destruir el gráfico anterior si existe
      if (this.chartInstance) {
        this.chartInstance.destroy();
      }
  
      this.chartInstance = new Chart(this.chartRef.el, {
        type: props.type, // Puede ser 'line', 'bar', 'pie', etc.
        data: {
          labels,
          datasets: [{
            label: props.title || "No data",  // Título del gráfico
            data: values,
            backgroundColor: "#d3d3d3",  // Color gris para mostrar vacío
            borderColor: "#999",  // Gris para las líneas
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom' },
            title: { display: true, text: props.title || "No data", position: 'bottom' }
          }
        },
      });
  
      return; // Salir de la función, ya que no hay datos
    }
  
    // Destruir el gráfico anterior si existe
    if (this.chartInstance) {
      this.chartInstance.destroy();
    }
  
    // Mapeamos las etiquetas y los valores directamente desde `label` y `value`
    const labels = props.data.map(item => item.label || "Unknown Label");
    const values = props.data.map(item => Math.abs(item.value || 0)); // Asegúrate de que `value` es el valor correcto
  
    const colors = [
      "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
      "#FF9F40", "#00A6A6", "#C9CBCF", "#FF6384", "#36A2EB"
    ];
  
    this.chartInstance = new Chart(this.chartRef.el, {
      type: props.type,
      data: {
        labels,
        datasets: [{
          label: props.title,
          data: values,
          backgroundColor: colors.slice(0, labels.length),
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
          title: { display: true, text: props.title, position: 'bottom' }
        }
      },
    });
  }
  
}

ChartRender.template = "lv_personal_wallet.ChartRender";
