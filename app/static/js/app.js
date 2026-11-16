/* StudyFlow — JavaScript global: toasts, API, menu, modais, validação e confirmações. */
(function () {
  'use strict';

  /* ---------- Toasts ---------- */
  window.toast = function (mensagem, tipo) {
    tipo = tipo || 'success';
    var container = document.getElementById('toasts');
    if (!container || !window.bootstrap) { return; }
    var cores = { success: 'text-bg-success', danger: 'text-bg-danger', warning: 'text-bg-warning', info: 'text-bg-primary' };
    var el = document.createElement('div');
    el.className = 'toast align-items-center border-0 ' + (cores[tipo] || cores.info);
    el.setAttribute('role', 'alert');
    el.innerHTML = '<div class="d-flex"><div class="toast-body"></div>' +
      '<button type="button" class="btn-close ' + (tipo === 'warning' ? '' : 'btn-close-white') +
      ' me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button></div>';
    el.querySelector('.toast-body').textContent = mensagem;
    container.appendChild(el);
    el.addEventListener('hidden.bs.toast', function () { el.remove(); });
    new bootstrap.Toast(el, { delay: tipo === 'danger' ? 7000 : 4000 }).show();
  };

  /* ---------- Chamadas à API (JSON + CSRF) ---------- */
  window.csrfToken = function () {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  };

  window.api = async function (url, opcoes) {
    opcoes = opcoes || {};
    var cabecalhos = {
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': window.csrfToken()
    };
    var config = { method: opcoes.method || 'GET', headers: cabecalhos, credentials: 'same-origin' };
    if (opcoes.corpo !== undefined) {
      cabecalhos['Content-Type'] = 'application/json';
      config.body = JSON.stringify(opcoes.corpo);
    }
    try {
      var resposta = await fetch(url, config);
      var dados = null;
      try { dados = await resposta.json(); } catch (e) { dados = null; }
      if (resposta.status === 401) {               // sessão expirada: volta ao login
        window.toast('Sua sessão expirou. Entre novamente.', 'warning');
        setTimeout(function () { window.location.href = '/entrar?next=' + encodeURIComponent(window.location.pathname); }, 1500);
        return { ok: false, status: 401, dados: dados };
      }
      if (!resposta.ok && !opcoes.silencioso) {
        var erros = (dados && dados.erros) || [(dados && dados.mensagem) || 'Não foi possível concluir a operação.'];
        erros.forEach(function (m) { window.toast(m, 'danger'); });
      }
      return { ok: resposta.ok, status: resposta.status, dados: dados };
    } catch (e) {
      if (!opcoes.silencioso) { window.toast('Falha de comunicação com o servidor.', 'danger'); }
      return { ok: false, status: 0, dados: null };
    }
  };

  /* ---------- Utilidades de data ---------- */
  window.pad2 = function (n) { return String(n).padStart(2, '0'); };
  window.isoData = function (d) { return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); };
  window.isoLocal = function (d) { return isoData(d) + 'T' + pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds()); };
  window.formatarMs = function (ms) {
    var s = Math.max(0, Math.floor(ms / 1000));
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60;
    return (h ? h + ':' + pad2(m) : pad2(m)) + ':' + pad2(seg);
  };
  window.formatarMin = function (min) {
    min = Math.round(min);
    var h = Math.floor(min / 60), m = min % 60;
    if (h && m) { return h + 'h ' + pad2(m) + 'min'; }
    return h ? h + 'h' : m + 'min';
  };

  document.addEventListener('DOMContentLoaded', function () {
    /* ---------- Data no topo ---------- */
    var dataEl = document.getElementById('data-atual');
    if (dataEl) {
      dataEl.textContent = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });
    }

    /* ---------- Menu lateral ---------- */
    var corpo = document.body;
    var botaoMenu = document.getElementById('btn-menu');
    var fundo = document.getElementById('sidebar-backdrop');
    var ehMovel = function () { return window.matchMedia('(max-width: 991.98px)').matches; };
    try {
      var salvo = localStorage.getItem('studyflow.menu');
      if (salvo !== null && !ehMovel()) { corpo.classList.toggle('sidebar-collapsed', salvo === '1'); }
    } catch (e) { /* localStorage indisponível */ }
    if (botaoMenu) {
      botaoMenu.addEventListener('click', function () {
        if (ehMovel()) { corpo.classList.toggle('sidebar-open'); return; }
        var recolhido = corpo.classList.toggle('sidebar-collapsed');
        try { localStorage.setItem('studyflow.menu', recolhido ? '1' : '0'); } catch (e) { /* ignora */ }
      });
    }
    if (fundo) { fundo.addEventListener('click', function () { corpo.classList.remove('sidebar-open'); }); }

    /* ---------- Validação de formulários (Bootstrap) ---------- */
    document.addEventListener('submit', function (ev) {
      var form = ev.target;
      if (form.classList && form.classList.contains('needs-validation')) {
        if (!form.checkValidity()) {
          ev.preventDefault();
          ev.stopPropagation();
        }
        form.classList.add('was-validated');
      }
    }, true);

    /* ---------- Confirmação de exclusão ---------- */
    var modalConfirmar = document.getElementById('modal-confirmar');
    var formPendente = null;
    if (modalConfirmar) {
      var instancia = bootstrap.Modal.getOrCreateInstance(modalConfirmar);
      document.addEventListener('submit', function (ev) {
        var form = ev.target;
        if (form.classList && form.classList.contains('form-excluir') && !form.dataset.confirmado) {
          ev.preventDefault();
          formPendente = form;
          document.getElementById('modal-confirmar-texto').textContent =
            form.dataset.mensagem || 'Deseja realmente excluir este registro?';
          instancia.show();
        }
      });
      document.getElementById('modal-confirmar-ok').addEventListener('click', function () {
        if (formPendente) {
          formPendente.dataset.confirmado = '1';
          instancia.hide();
          formPendente.submit();
        }
      });
    }

    /* ---------- Modais de cadastro/edição preenchidos via data-* ---------- */
    document.addEventListener('click', function (ev) {
      var botao = ev.target.closest('[data-form-modal]');
      if (!botao) { return; }
      var modal = document.querySelector(botao.dataset.formModal);
      if (!modal) { return; }
      var form = modal.querySelector('form');
      form.reset();
      form.classList.remove('was-validated');
      form.action = botao.dataset.action;
      var valores = {};
      if (botao.dataset.valores) {
        try { valores = JSON.parse(botao.dataset.valores); } catch (e) { valores = {}; }
      }
      Object.keys(valores).forEach(function (nome) {
        var campo = form.elements[nome];
        if (campo) { campo.value = valores[nome] === null ? '' : valores[nome]; }
      });
      var titulo = modal.querySelector('.modal-title');
      if (titulo) { titulo.textContent = botao.dataset.titulo || ''; }
      form.dispatchEvent(new CustomEvent('formpreenchido', { detail: { valores: valores } }));
      bootstrap.Modal.getOrCreateInstance(modal).show();
    });

    /* ---------- Envio automático de seletores/filtros ---------- */
    document.querySelectorAll('[data-auto-submit]').forEach(function (el) {
      el.addEventListener('change', function () { el.form.submit(); });
    });
  });

  /* ---------- Seletores dependentes: matéria → conteúdo ---------- */
  window.vincularConteudos = function (selMateria, selConteudo) {
    var dadosEl = document.getElementById('dados-conteudos');
    var mapa = {};
    try { mapa = JSON.parse(dadosEl.textContent); } catch (e) { mapa = {}; }
    function popular(selecionado) {
      var lista = mapa[selMateria.value] || [];
      selConteudo.innerHTML = '';
      var vazio = document.createElement('option');
      vazio.value = '';
      vazio.textContent = lista.length ? '— Nenhum conteúdo específico —' : '— Matéria sem conteúdos —';
      selConteudo.appendChild(vazio);
      lista.forEach(function (c) {
        var op = document.createElement('option');
        op.value = c.id;
        op.textContent = c.nome;
        selConteudo.appendChild(op);
      });
      if (selecionado) { selConteudo.value = String(selecionado); }
    }
    selMateria.addEventListener('change', function () { popular(''); });
    if (selMateria.form) {
      selMateria.form.addEventListener('formpreenchido', function (ev) {
        popular(ev.detail && ev.detail.valores ? ev.detail.valores.conteudo_id : '');
      });
    }
    popular(selConteudo.dataset.inicial || '');
    return popular;
  };

  /* ---------- Cores e opções padrão dos gráficos ---------- */
  window.PALETA = ['#2563eb', '#0ea5e9', '#6366f1', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b', '#22c55e', '#ec4899'];
  window.configurarChart = function () {
    if (!window.Chart) { return; }
    var estilo = getComputedStyle(document.documentElement);
    Chart.defaults.color = getComputedStyle(document.body).getPropertyValue('--bs-secondary-color').trim() || '#6b7280';
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.borderColor = (document.documentElement.dataset.bsTheme === 'dark') ? '#2b3345' : '#e5e9f0';
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    return estilo;
  };
  window.graficoVazio = function (canvas, mensagem) {
    var caixa = canvas.parentElement;
    caixa.innerHTML = '<div class="d-flex h-100 align-items-center justify-content-center text-body-secondary text-center small px-3">' +
      '<div><i class="bi bi-bar-chart fs-2 d-block mb-1 opacity-50"></i>' + mensagem + '</div></div>';
  };
  window.rotuloHoras = function (ctx) {
    var valor = ctx.parsed.y !== undefined && ctx.parsed.y !== null ? ctx.parsed.y : ctx.parsed;
    return ' ' + formatarMin(valor * 60);
  };
})();
