// static/js/monitor_informe.js
// Lógica de la vista de informe: gráfico de evolución + descarga .md
// Los datos llegan vía window.MONITOR_* (inyectados por Jinja2 en el HTML)

(function () {
  'use strict';

  // -------------------------- Gráfico de evolución --------------------------
  function initChart() {
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js no disponible');
      return;
    }
    var chartData = window.MONITOR_CHART_DATA;
    var canvas = document.getElementById('chartInforme');
    if (!chartData || !canvas) return;

    new Chart(canvas, {
      type: 'line',
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { callback: function (v) { return v + '%'; } }
          }
        },
        plugins: { legend: { position: 'bottom' } }
      }
    });
  }

  // -------------------------- Descarga .md --------------------------
  function descargarMarkdown() {
    var contenido = window.MONITOR_INFORME_MD;
    var ruta = window.MONITOR_INFORME_RUTA || 'informe.md';
    if (!contenido) {
      console.warn('No hay contenido de informe para descargar');
      return;
    }
    var blob = new Blob([contenido], { type: 'text/markdown;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = ruta;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  // Exponer la función globalmente (para el onclick del botón)
  window.descargarMarkdown = descargarMarkdown;

  // -------------------------- Init --------------------------
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChart);
  } else {
    initChart();
  }
})();