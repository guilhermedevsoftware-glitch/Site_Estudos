/* StudyFlow — gráficos do dashboard (Chart.js). Dados vêm de window.DASH. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  if (!window.Chart) {
    document.querySelectorAll('.chart-box').forEach(function (b) {
      b.innerHTML = '<div class="text-body-secondary small p-3">Não foi possível carregar a biblioteca de gráficos (verifique a conexão com a internet).</div>';
    });
    return;
  }
  configurarChart();
  var D = window.DASH;
  var msgVazio = 'Nenhuma sessão de estudo registrada ainda.<br>Use o cronômetro para começar!';

  function semDados(valores) { return !valores.some(function (v) { return v > 0; }); }
  function eixoHoras() {
    return { beginAtZero: true, title: { display: true, text: 'Horas' }, ticks: { precision: 1 } };
  }

  // 1) Horas por dia da semana
  var c1 = document.getElementById('g-semana');
  if (semDados(D.semana.valores)) { graficoVazio(c1, 'Sem horas registradas nesta semana.'); } else {
    new Chart(c1, {
      type: 'bar',
      data: { labels: D.semana.labels, datasets: [{ label: 'Horas', data: D.semana.valores, backgroundColor: PALETA[0], borderRadius: 6 }] },
      options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: rotuloHoras } } }, scales: { y: eixoHoras() } }
    });
  }

  // 2) Horas por matéria
  var c2 = document.getElementById('g-materias');
  if (semDados(D.materias.valores)) { graficoVazio(c2, msgVazio); } else {
    new Chart(c2, {
      type: 'bar',
      data: { labels: D.materias.labels, datasets: [{ label: 'Horas', data: D.materias.valores, backgroundColor: PALETA, borderRadius: 6 }] },
      options: { indexAxis: 'y', plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return ' ' + formatarMin(c.parsed.x * 60); } } } },
        scales: { x: { beginAtZero: true, title: { display: true, text: 'Horas' } } } }
    });
  }

  // 3) Evolução mensal
  var c3 = document.getElementById('g-mensal');
  if (semDados(D.mensal.valores)) { graficoVazio(c3, msgVazio); } else {
    new Chart(c3, {
      type: 'line',
      data: { labels: D.mensal.labels, datasets: [{ label: 'Horas', data: D.mensal.valores, borderColor: PALETA[0], backgroundColor: 'rgba(37,99,235,.15)', fill: true, tension: .3, pointRadius: 4, pointHoverRadius: 6 }] },
      options: { interaction: { mode: 'index', intersect: false }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: rotuloHoras } } }, scales: { y: eixoHoras() } }
    });
  }

  // 4) Categorias
  var c4 = document.getElementById('g-categorias');
  if (semDados(D.categorias.valores)) { graficoVazio(c4, msgVazio); } else {
    new Chart(c4, {
      type: 'doughnut',
      data: { labels: D.categorias.labels, datasets: [{ data: D.categorias.valores, backgroundColor: PALETA, borderWidth: 2 }] },
      options: { cutout: '60%', plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: function (c) { return ' ' + c.label + ': ' + formatarMin(c.parsed * 60); } } } } }
    });
  }
});
