/* StudyFlow — cronômetro de estudos e Pomodoro.
 *
 * O estado fica no localStorage e o tempo é SEMPRE recalculado a partir de
 * horários guardados (não de contagens em memória). Por isso o cronômetro
 * continua correto ao navegar entre páginas, recarregar ou fechar o navegador.
 *
 * Campos do estado:
 *   estado         'parado' | 'rodando' | 'pausado'
 *   modo           'livre' | 'pomodoro'
 *   fase           'foco' | 'pausa' | 'pausa_longa'
 *   sessao_inicio  ISO local do primeiro "Iniciar"
 *   fase_inicio_ts instante (ms) em que o trecho atual começou a correr
 *   acumulado_ms   tempo já acumulado na fase atual antes do trecho corrente
 *   foco_acum_ms   foco total das fases de foco já concluídas na sessão
 *   ciclo          quantidade de focos concluídos (define a pausa longa)
 */
(function () {
  'use strict';
  var CHAVE = 'studyflow.timer';
  var tituloOriginal = document.title;
  var audioCtx = null;

  function padrao() {
    return {
      estado: 'parado', modo: 'livre', fase: 'foco',
      materia_id: '', conteudo_id: '', observacoes: '',
      sessao_inicio: null, fase_inicio_ts: 0, acumulado_ms: 0, foco_acum_ms: 0, ciclo: 0
    };
  }
  function ler() {
    try {
      var bruto = localStorage.getItem(CHAVE);
      return Object.assign(padrao(), bruto ? JSON.parse(bruto) : {});
    } catch (e) { return padrao(); }
  }
  function gravar(s) {
    try { localStorage.setItem(CHAVE, JSON.stringify(s)); } catch (e) { /* ignora */ }
  }
  function configPomodoro() {
    var p = {};
    try { p = JSON.parse(document.body.dataset.pomodoro || '{}'); } catch (e) { p = {}; }
    return {
      foco: Math.max(1, p.foco || 25), pausa: Math.max(1, p.pausa || 5),
      longa: Math.max(1, p.longa || 15), ciclos: Math.max(2, p.ciclos || 4)
    };
  }
  function duracaoFase(s) {
    var p = configPomodoro();
    var min = s.fase === 'foco' ? p.foco : (s.fase === 'pausa' ? p.pausa : p.longa);
    return min * 60000;
  }
  function decorrido(s, agora) {
    return s.acumulado_ms + (s.estado === 'rodando' ? Math.max(0, agora - s.fase_inicio_ts) : 0);
  }
  function proximaFase(s) {
    if (s.fase === 'foco') {
      s.ciclo += 1;
      s.fase = (s.ciclo % configPomodoro().ciclos === 0) ? 'pausa_longa' : 'pausa';
    } else {
      s.fase = 'foco';
    }
  }
  /* Avança as fases do Pomodoro que já terminaram (inclusive enquanto a página estava fechada). */
  function normalizar(s, agora) {
    var mudancas = [];
    if (s.modo !== 'pomodoro' || s.estado !== 'rodando') { return mudancas; }
    for (var guarda = 0; guarda < 500; guarda++) {
      var dur = duracaoFase(s), dec = decorrido(s, agora);
      if (dec < dur) { break; }
      if (s.fase === 'foco') { s.foco_acum_ms += dur; }
      proximaFase(s);
      s.acumulado_ms = 0;
      s.fase_inicio_ts = agora - (dec - dur);
      mudancas.push(s.fase);
    }
    return mudancas;
  }
  function focoTotal(s, agora) {
    return s.foco_acum_ms + (s.fase === 'foco' ? decorrido(s, agora) : 0);
  }

  /* ---------- Ações ---------- */
  var Timer = {
    ler: ler,
    gravar: gravar,
    focoTotal: focoTotal,
    decorrido: decorrido,
    duracaoFase: duracaoFase,
    iniciar: function (opcoes) {
      var s = padrao(), agora = Date.now();
      s.modo = opcoes.modo === 'pomodoro' ? 'pomodoro' : 'livre';
      s.materia_id = opcoes.materia_id || '';
      s.conteudo_id = opcoes.conteudo_id || '';
      s.observacoes = opcoes.observacoes || '';
      s.estado = 'rodando';
      s.sessao_inicio = isoLocal(new Date(agora));
      s.fase_inicio_ts = agora;
      gravar(s);
      return s;
    },
    pausar: function () {
      var s = ler(), agora = Date.now();
      if (s.estado !== 'rodando') { return s; }
      normalizar(s, agora);
      s.acumulado_ms = decorrido(s, agora);
      s.estado = 'pausado';
      gravar(s);
      return s;
    },
    continuar: function () {
      var s = ler();
      if (s.estado !== 'pausado') { return s; }
      s.estado = 'rodando';
      s.fase_inicio_ts = Date.now();
      gravar(s);
      return s;
    },
    pular: function () {
      var s = ler(), agora = Date.now();
      if (s.modo !== 'pomodoro' || s.estado === 'parado') { return s; }
      if (s.fase === 'foco') { s.foco_acum_ms += decorrido(s, agora); }
      proximaFase(s);
      s.acumulado_ms = 0;
      s.fase_inicio_ts = agora;
      gravar(s);
      return s;
    },
    atualizarCampos: function (campos) {
      var s = ler();
      Object.assign(s, campos);
      gravar(s);
    },
    descartar: function () { gravar(padrao()); }
  };
  window.StudyTimer = Timer;

  /* ---------- Avisos de fim de fase ---------- */
  function bip() {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      [0, 0.25, 0.5].forEach(function (atraso) {
        var osc = audioCtx.createOscillator(), ganho = audioCtx.createGain();
        osc.frequency.value = 880;
        ganho.gain.value = 0.15;
        osc.connect(ganho); ganho.connect(audioCtx.destination);
        osc.start(audioCtx.currentTime + atraso);
        osc.stop(audioCtx.currentTime + atraso + 0.15);
      });
    } catch (e) { /* som indisponível */ }
  }
  var NOMES_FASE = { foco: 'Hora de focar!', pausa: 'Descanse um pouco (pausa curta).', pausa_longa: 'Pausa longa: você merece!' };
  function avisarFase(fase) {
    bip();
    if (window.toast) { window.toast(NOMES_FASE[fase], fase === 'foco' ? 'info' : 'success'); }
    if ('Notification' in window && Notification.permission === 'granted') {
      try { new Notification('StudyFlow · Pomodoro', { body: NOMES_FASE[fase] }); } catch (e) { /* ignora */ }
    }
  }

  /* ---------- Atualização periódica (mini-relógio + tela do cronômetro) ---------- */
  var mini = document.getElementById('mini-timer');
  var miniTxt = document.getElementById('mini-timer-txt');
  var aoAtualizar = [];
  Timer.aoAtualizar = function (fn) { aoAtualizar.push(fn); };

  function textoPrincipal(s, agora) {
    if (s.modo === 'pomodoro') { return formatarMs(duracaoFase(s) - decorrido(s, agora)); }
    return formatarMs(decorrido(s, agora));
  }

  function tick() {
    var s = ler(), agora = Date.now();
    if (s.estado === 'rodando') {
      var mudancas = normalizar(s, agora);
      if (mudancas.length) {
        gravar(s);
        avisarFase(mudancas[mudancas.length - 1]);
      }
    }
    if (mini) {
      if (s.estado === 'parado') {
        mini.classList.add('d-none');
        document.title = tituloOriginal;
      } else {
        var texto = textoPrincipal(s, agora);
        mini.classList.remove('d-none');
        mini.classList.toggle('pausado', s.estado === 'pausado');
        mini.classList.toggle('descanso', s.estado === 'rodando' && s.fase !== 'foco');
        miniTxt.textContent = texto + (s.estado === 'pausado' ? ' (pausado)' : '');
        document.title = (s.estado === 'rodando' ? '⏱ ' + texto + ' · ' : '⏸ ') + tituloOriginal;
      }
    }
    aoAtualizar.forEach(function (fn) { fn(s, agora); });
  }

  window.addEventListener('storage', function (ev) { if (ev.key === CHAVE) { tick(); } });
  document.addEventListener('DOMContentLoaded', function () {
    if (!mini) { return; }
    mini.addEventListener('click', function () { /* link normal para o cronômetro */ });
    tick();
    setInterval(tick, 250);
  });

  /* ============================================================
   *  Tela completa do cronômetro (somente em /cronometro)
   * ============================================================ */
  document.addEventListener('DOMContentLoaded', function () {
    var app = document.getElementById('timer-app');
    if (!app) { return; }

    var el = function (id) { return document.getElementById(id); };
    var display = el('t-display'), faseEl = el('t-fase'), cartao = el('t-card');
    var selMateria = el('t-materia'), selConteudo = el('t-conteudo'), obs = el('t-obs');
    var btnIniciar = el('t-iniciar'), btnPausar = el('t-pausar'), btnContinuar = el('t-continuar');
    var btnPular = el('t-pular'), btnFinalizar = el('t-finalizar'), btnDescartar = el('t-descartar');
    var barra = el('t-barra'), barraBox = el('t-barra-box'), infoCiclo = el('t-ciclo'), focoInfo = el('t-foco-info');
    var radiosModo = document.querySelectorAll('input[name="t-modo"]');
    var NOMES = { foco: 'Foco', pausa: 'Pausa curta', pausa_longa: 'Pausa longa' };

    var popular = window.vincularConteudos(selMateria, selConteudo);

    function modoEscolhido() {
      var marcado = document.querySelector('input[name="t-modo"]:checked');
      return marcado ? marcado.value : 'livre';
    }

    // Restaura os campos se já existe uma sessão em andamento.
    var inicial = ler();
    if (inicial.estado !== 'parado') {
      selMateria.value = inicial.materia_id;
      popular(inicial.conteudo_id);
      obs.value = inicial.observacoes || '';
      radiosModo.forEach(function (r) { r.checked = (r.value === inicial.modo); });
    } else if (app.dataset.materiaInicial) {
      selMateria.value = app.dataset.materiaInicial;
      popular(app.dataset.conteudoInicial || '');
    }

    function aplicarEstado(s, agora) {
      var parado = s.estado === 'parado', rodando = s.estado === 'rodando', pausado = s.estado === 'pausado';
      display.textContent = parado
        ? (modoEscolhido() === 'pomodoro' ? formatarMs(configPomodoro().foco * 60000) : '00:00')
        : textoPrincipal(s, agora);
      var descanso = !parado && s.modo === 'pomodoro' && s.fase !== 'foco';
      cartao.classList.toggle('foco', !descanso);
      cartao.classList.toggle('descanso', descanso);
      faseEl.className = 'timer-fase ' + (descanso ? 'descanso' : 'foco');
      faseEl.textContent = parado ? 'Pronto para começar'
        : (s.modo === 'pomodoro' ? NOMES[s.fase] : 'Cronômetro livre') + (pausado ? ' · pausado' : '');
      btnIniciar.classList.toggle('d-none', !parado);
      btnPausar.classList.toggle('d-none', !rodando);
      btnContinuar.classList.toggle('d-none', !pausado);
      btnFinalizar.classList.toggle('d-none', parado);
      btnDescartar.classList.toggle('d-none', parado);
      btnPular.classList.toggle('d-none', parado || s.modo !== 'pomodoro');
      selMateria.disabled = !parado; selConteudo.disabled = !parado;
      radiosModo.forEach(function (r) { r.disabled = !parado; });
      barraBox.classList.toggle('d-none', parado || s.modo !== 'pomodoro');
      if (!parado && s.modo === 'pomodoro') {
        var pct = Math.min(100, decorrido(s, agora) / duracaoFase(s) * 100);
        barra.style.width = pct + '%';
        infoCiclo.textContent = 'Ciclos de foco concluídos: ' + s.ciclo;
      }
      focoInfo.textContent = parado ? '' : 'Tempo de estudo acumulado: ' + formatarMin(focoTotal(s, agora) / 60000);
    }
    Timer.aoAtualizar(aplicarEstado);
    aplicarEstado(ler(), Date.now());
    radiosModo.forEach(function (r) { r.addEventListener('change', function () { aplicarEstado(ler(), Date.now()); }); });

    btnIniciar.addEventListener('click', function () {
      if (!selMateria.value) {
        window.toast('Selecione a matéria que você vai estudar.', 'warning');
        selMateria.focus();
        return;
      }
      if ('Notification' in window && Notification.permission === 'default') {
        try { Notification.requestPermission(); } catch (e) { /* ignora */ }
      }
      Timer.iniciar({
        modo: modoEscolhido(), materia_id: selMateria.value,
        conteudo_id: selConteudo.value, observacoes: obs.value
      });
      aplicarEstado(ler(), Date.now());
    });
    btnPausar.addEventListener('click', function () { Timer.pausar(); aplicarEstado(ler(), Date.now()); });
    btnContinuar.addEventListener('click', function () { Timer.continuar(); aplicarEstado(ler(), Date.now()); });
    btnPular.addEventListener('click', function () { Timer.pular(); aplicarEstado(ler(), Date.now()); });
    obs.addEventListener('input', function () {
      if (ler().estado !== 'parado') { Timer.atualizarCampos({ observacoes: obs.value }); }
    });
    btnDescartar.addEventListener('click', function () {
      if (window.confirm('Descartar esta sessão sem salvar? O tempo registrado será perdido.')) {
        Timer.descartar();
        aplicarEstado(ler(), Date.now());
      }
    });

    /* ---------- Finalizar sessão ---------- */
    var modalEl = el('modal-finalizar');
    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    var campoDuracao = el('f-duracao'), campoObs = el('f-obs'), resumo = el('f-resumo');
    var btnSalvar = el('f-salvar');
    var fimSessao = null;

    btnFinalizar.addEventListener('click', function () {
      Timer.pausar();                       // congela a contagem enquanto confirma
      var s = ler(), agora = Date.now();
      fimSessao = new Date(agora);
      var minutos = Math.max(1, Math.round(focoTotal(s, agora) / 60000));
      campoDuracao.value = minutos;
      campoObs.value = obs.value;
      var mat = selMateria.options[selMateria.selectedIndex];
      var con = selConteudo.options[selConteudo.selectedIndex];
      resumo.textContent = (mat ? mat.textContent : '') + (con && con.value ? ' · ' + con.textContent : '');
      modal.show();
    });
    modalEl.addEventListener('hidden.bs.modal', function () { aplicarEstado(ler(), Date.now()); });

    btnSalvar.addEventListener('click', async function () {
      var s = ler();
      var duracao = parseInt(campoDuracao.value, 10);
      if (!duracao || duracao < 1 || duracao > 1440) {
        window.toast('Informe uma duração entre 1 e 1440 minutos.', 'warning');
        return;
      }
      btnSalvar.disabled = true;
      var r = await window.api(app.dataset.urlSalvar, {
        method: 'POST',
        corpo: {
          materia_id: s.materia_id, conteudo_id: s.conteudo_id,
          inicio: s.sessao_inicio, fim: isoLocal(fimSessao || new Date()),
          duracao_min: duracao, observacoes: campoObs.value
        }
      });
      btnSalvar.disabled = false;
      if (r.ok) {
        Timer.descartar();
        modal.hide();
        window.location.reload();   // a mensagem de sucesso (flash) aparece após o recarregamento
      }
    });

    /* ---------- Intervalos do Pomodoro (salvos automaticamente) ---------- */
    var campos = ['p-foco', 'p-pausa', 'p-longa', 'p-ciclos'].map(el);
    var salvarIntervalos = async function () {
      var corpo = {
        foco: campos[0].value, pausa: campos[1].value,
        longa: campos[2].value, ciclos: campos[3].value
      };
      var r = await window.api(app.dataset.urlIntervalos, { method: 'POST', corpo: corpo });
      if (r.ok && r.dados) {
        document.body.dataset.pomodoro = JSON.stringify(r.dados.pomodoro);
        window.toast('Intervalos do Pomodoro atualizados.', 'success');
        aplicarEstado(ler(), Date.now());
      }
    };
    campos.forEach(function (c) { c.addEventListener('change', salvarIntervalos); });
  });
})();
