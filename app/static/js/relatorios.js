/* StudyFlow — filtros e gráficos da página de relatórios (Chart.js). */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';

  /* ---------- Filtros: mostra só os campos de data relevantes ---------- */
  var periodo = document.getElementById('r-periodo');
  function ajustarCampos() {
    var p = periodo.value;
    document.querySelectorAll('.grupo-ref').forEach(function (e) { e.classList.toggle('d-none', p === 'personalizado' || p === 'tudo'); });
    document.querySelectorAll('.grupo-pers').forEach(function (e) { e.classList.toggle('d-none', p !== 'personalizado'); });
  }
  periodo.addEventListener('change', ajustarCampos);
  ajustarCampos();

  if (!window.Chart) {
    document.querySelectorAll('.chart-box').forEach(function (b) {
      b.innerHTML = '<div class="text-body-secondary small p-3">Não foi possível carregar a biblioteca de gráficos (verifique a conexão com a internet).</div>';
    });
    return;
  }
  configurarChart();
  var R = window.REL;
  var msg = 'Sem dados de estudo neste período.';
  function vazio(v) { return !v.some(function (x) { return x > 0; }); }
  var fmt = function (c) { var v = c.parsed.y !== undefined ? c.parsed.y : c.parsed; return ' ' + formatarMin(v * 60); };

  /* ---------- Série principal (por período / acumulado) ---------- */
  var cSerie = document.getElementById('r-serie');
  if (vazio(R.serie.valores)) { graficoVazio(cSerie, msg); } else {
    var acumulado = [];
    R.serie.valores.reduce(function (s, v, i) { s += v; acumulado[i] = Math.round(s * 100) / 100; return s; }, 0);
    var grafico = new Chart(cSerie, {
      type: 'bar',
      data: { labels: R.serie.labels, datasets: [{ label: 'Horas', data: R.serie.valores, backgroundColor: PALETA[0], borderRadius: 4 }] },
      options: { interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: fmt } } },
        scales: { y: { beginAtZero: true, title: { display: true, text: 'Horas' } }, x: { ticks: { maxTicksLimit: 16 } } } }
    });
    document.querySelectorAll('[data-modo-serie]').forEach(function (b) {
      b.addEventListener('click', function () {
        document.querySelectorAll('[data-modo-serie]').forEach(function (x) { x.classList.toggle('active', x === b); });
        var acum = b.dataset.modoSerie === 'acumulado';
        grafico.config.type = acum ? 'line' : 'bar';
        grafico.data.datasets[0].data = acum ? acumulado : R.serie.valores;
        grafico.data.datasets[0].label = acum ? 'Horas acumuladas' : 'Horas';
        grafico.data.datasets[0].fill = acum;
        grafico.data.datasets[0].tension = .25;
        grafico.data.datasets[0].borderColor = PALETA[0];
        grafico.data.datasets[0].backgroundColor = acum ? 'rgba(37,99,235,.15)' : PALETA[0];
        grafico.update();
      });
    });
  }

  /* ---------- Matérias (rosca) ---------- */
  var cMat = document.getElementById('r-materias');
  if (vazio(R.materias.valores)) { graficoVazio(cMat, msg); } else {
    new Chart(cMat, { type: 'doughnut',
      data: { labels: R.materias.labels, datasets: [{ data: R.materias.valores, backgroundColor: PALETA, borderWidth: 2 }] },
      options: { cutout: '58%', plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: function (c) { return ' ' + c.label + ': ' + formatarMin(c.parsed * 60); } } } } } });
  }

  /* ---------- Dia da semana ---------- */
  var cSem = document.getElementById('r-semana');
  if (vazio(R.semana.valores)) { graficoVazio(cSem, msg); } else {
    new Chart(cSem, { type: 'bar',
      data: { labels: R.semana.labels, datasets: [{ label: 'Horas', data: R.semana.valores, backgroundColor: PALETA[1], borderRadius: 6 }] },
      options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: fmt } } }, scales: { y: { beginAtZero: true, title: { display: true, text: 'Horas' } } } } });
  }

  /* ---------- Categorias ---------- */
  var cCat = document.getElementById('r-categorias');
  if (vazio(R.categorias.valores)) { graficoVazio(cCat, msg); } else {
    new Chart(cCat, { type: 'bar',
      data: { labels: R.categorias.labels, datasets: [{ label: 'Horas', data: R.categorias.valores, backgroundColor: PALETA, borderRadius: 6 }] },
      options: { indexAxis: 'y', plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return ' ' + formatarMin(c.parsed.x * 60); } } } }, scales: { x: { beginAtZero: true, title: { display: true, text: 'Horas' } } } } });
  }
});
