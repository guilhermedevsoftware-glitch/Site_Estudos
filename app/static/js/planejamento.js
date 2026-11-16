/* StudyFlow — calendário de planejamento (JavaScript puro).
 * Visões: dia, semana e mês. Criar (clique), editar (clique na atividade),
 * reorganizar (arrastar), ajustar duração (borda inferior) e excluir. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var wrap = document.getElementById('cal');
  if (!wrap) { return; }

  var URL_BASE = wrap.dataset.url;                 // /planejamento/api/atividades
  var HP = 52;                                     // pixels por hora
  var SNAP = 15;                                   // minutos
  var NOMES_DIA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  var visao = 'semana';
  try { visao = localStorage.getItem('studyflow.cal.visao') || 'semana'; } catch (e) { /* ignora */ }
  if (['dia', 'semana', 'mes'].indexOf(visao) < 0) { visao = 'semana'; }
  var cursor = new Date();
  var eventos = [];
  var ctx = null;                                  // arrasto em andamento (grade)
  var idEditando = null;

  /* ---------- datas ---------- */
  function zerar(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  function somar(d, n) { var x = new Date(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes()); x.setDate(x.getDate() + n); return x; }
  function inicioSemana(d) { var x = zerar(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x; }
  function mesmoDia(a, b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
  function parse(s) { var p = s.split(/[-T:]/).map(Number); return new Date(p[0], p[1] - 1, p[2], p[3], p[4]); }
  function minDia(d) { return d.getHours() * 60 + d.getMinutes(); }
  function hhmm(min) { return pad2(Math.floor(min / 60)) + ':' + pad2(min % 60); }
  function limitar(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function dataHoraMin(dia, min) { return isoData(dia) + 'T' + hhmm(min) + ':00'; }

  function intervalo() {
    if (visao === 'dia') { var i = zerar(cursor); return [i, somar(i, 1)]; }
    if (visao === 'semana') { var s = inicioSemana(cursor); return [s, somar(s, 7)]; }
    var s2 = inicioSemana(new Date(cursor.getFullYear(), cursor.getMonth(), 1));
    return [s2, somar(s2, 42)];
  }

  function el(tag, classe, texto) {
    var e = document.createElement(tag);
    if (classe) { e.className = classe; }
    if (texto !== undefined) { e.textContent = texto; }
    return e;
  }

  /* ---------- carregamento ---------- */
  async function carregar() {
    var r0 = intervalo();
    var url = URL_BASE + '?inicio=' + encodeURIComponent(isoLocal(r0[0])) + '&fim=' + encodeURIComponent(isoLocal(r0[1]));
    var filtro = document.getElementById('cal-filtro').value;
    if (filtro) { url += '&materia_id=' + filtro; }
    var r = await window.api(url);
    eventos = r.ok && Array.isArray(r.dados) ? r.dados : [];
    eventos.forEach(function (e) { e._ini = parse(e.inicio); e._fim = parse(e.fim); });
    desenhar();
  }

  function atualizarTitulo() {
    var t = document.getElementById('cal-titulo');
    if (visao === 'dia') {
      t.textContent = cursor.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    } else if (visao === 'semana') {
      var s = inicioSemana(cursor), f = somar(s, 6);
      t.textContent = s.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }) + ' – ' +
        f.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
    } else {
      t.textContent = cursor.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
    }
    document.querySelectorAll('[data-visao]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.visao === visao);
    });
  }

  function desenhar() {
    atualizarTitulo();
    var rolagem = wrap.scrollTop;
    var mesmaVisao = wrap.dataset.visaoAtual === visao;
    wrap.innerHTML = '';
    if (visao === 'mes') { desenharMes(); } else { desenharGrade(visao === 'dia' ? 1 : 7); }
    wrap.dataset.visaoAtual = visao;
    wrap.scrollTop = (visao !== 'mes' && !mesmaVisao) ? 6.5 * HP : rolagem;
  }

  /* ---------- visão dia/semana ---------- */
  function disporSobrepostos(lista) {
    var fins = [], grupo = [];
    function fechar() { grupo.forEach(function (e) { e._cols = fins.length; }); grupo = []; fins = []; }
    lista.sort(function (a, b) { return a._ini - b._ini; }).forEach(function (e) {
      var ini = minDia(e._ini), fim = minDia(e._fim);
      if (grupo.length && ini >= Math.max.apply(null, fins)) { fechar(); }
      var c = 0;
      while (c < fins.length && fins[c] > ini) { c++; }
      fins[c] = fim; e._col = c; grupo.push(e);
    });
    fechar();
  }

  function desenharGrade(ndias) {
    var ini = ndias === 1 ? zerar(cursor) : inicioSemana(cursor);
    var colunas = '56px repeat(' + ndias + ', minmax(' + (ndias === 1 ? '240px' : '120px') + ', 1fr))';
    var hoje = new Date();
    var cabecalho = el('div', 'cal-head');
    cabecalho.style.gridTemplateColumns = colunas;
    cabecalho.appendChild(el('div', 'cal-hcell'));
    var corpo = el('div', 'cal-body');
    corpo.style.gridTemplateColumns = colunas;

    var horas = el('div', 'cal-horas');
    horas.style.height = (24 * HP) + 'px';
    for (var h = 1; h < 24; h++) {
      var rot = el('div', 'cal-hora', pad2(h) + ':00');
      rot.style.top = (h * HP) + 'px';
      horas.appendChild(rot);
    }
    corpo.appendChild(horas);

    for (var i = 0; i < ndias; i++) {
      var dia = somar(ini, i);
      var ehHoje = mesmoDia(dia, hoje);
      var cab = el('div', 'cal-hcell' + (ehHoje ? ' hoje' : ''));
      cab.appendChild(document.createTextNode(NOMES_DIA[dia.getDay()]));
      cab.appendChild(el('span', 'dia-num', String(dia.getDate())));
      cabecalho.appendChild(cab);

      var col = el('div', 'cal-col' + (ehHoje ? ' hoje' : ''));
      col.style.setProperty('--hp', HP + 'px');
      col.style.height = (24 * HP) + 'px';
      col.dataset.data = isoData(dia);

      var doDia = eventos.filter(function (e) { return mesmoDia(e._ini, dia); });
      disporSobrepostos(doDia);
      doDia.forEach(function (e) { col.appendChild(criarEvento(e)); });

      if (ehHoje) {
        var linha = el('div', 'cal-agora');
        linha.style.top = (minDia(hoje) / 60 * HP) + 'px';
        col.appendChild(linha);
      }
      corpo.appendChild(col);
    }
    wrap.appendChild(cabecalho);
    wrap.appendChild(corpo);
  }

  function criarEvento(e) {
    var ini = minDia(e._ini), fim = minDia(e._fim);
    var d = el('div', 'cal-evento ' + (e.status === 'Concluída' ? 'concluida' : (e.status === 'Cancelada' ? 'cancelada' : '')));
    var largura = 100 / (e._cols || 1);
    d.style.top = (ini / 60 * HP) + 'px';
    d.style.height = Math.max((fim - ini) / 60 * HP - 1, 22) + 'px';
    d.style.left = 'calc(' + (e._col * largura) + '% + 2px)';
    d.style.width = 'calc(' + largura + '% - 4px)';
    d.style.background = e.cor;
    d.dataset.id = e.id;
    d.title = e.titulo + ' · ' + e.materia + '\n' + hhmm(ini) + ' – ' + hhmm(fim) + ' (' + formatarMin(e.duracao_min) + ')';
    d.appendChild(el('div', 'cal-hora-ev', hhmm(ini) + ' – ' + hhmm(fim)));
    d.appendChild(el('div', '', e.titulo));
    d.appendChild(el('div', 'opacity-75', e.materia));
    d.appendChild(el('div', 'cal-resize'));
    return d;
  }

  /* ---------- visão mês ---------- */
  function desenharMes() {
    var r = intervalo(), ini = r[0], hoje = new Date();
    var grade = el('div', 'cal-mes');
    ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'].forEach(function (n) { grade.appendChild(el('div', 'cal-mes-head', n)); });
    for (var i = 0; i < 42; i++) {
      var dia = somar(ini, i);
      var cel = el('div', 'cal-celula' + (dia.getMonth() !== cursor.getMonth() ? ' outro-mes' : '') + (mesmoDia(dia, hoje) ? ' hoje' : ''));
      cel.dataset.data = isoData(dia);
      cel.appendChild(el('span', 'num', String(dia.getDate())));
      var doDia = eventos.filter(function (e) { return mesmoDia(e._ini, dia); });
      doDia.slice(0, 3).forEach(function (e) {
        var chip = el('span', 'cal-chip ' + (e.status === 'Concluída' ? 'concluida' : ''), hhmm(minDia(e._ini)) + ' ' + e.titulo);
        chip.style.background = e.cor;
        chip.draggable = true;
        chip.dataset.id = e.id;
        chip.title = e.titulo + ' · ' + e.materia;
        cel.appendChild(chip);
      });
      if (doDia.length > 3) { cel.appendChild(el('span', 'cal-mais', '+' + (doDia.length - 3) + ' mais')); }
      grade.appendChild(cel);
    }
    wrap.appendChild(grade);
  }

  /* ---------- salvar movimentos ---------- */
  async function mover(evento, inicio, fim) {
    var r = await window.api(URL_BASE + '/' + evento.id + '/mover', { method: 'PATCH', corpo: { inicio: inicio, fim: fim } });
    if (r.ok) { window.toast('Atividade reorganizada.', 'success'); }
    carregar();
  }
  function porId(id) { return eventos.filter(function (e) { return String(e.id) === String(id); })[0]; }

  /* ---------- interação: grade (ponteiro) ---------- */
  wrap.addEventListener('pointerdown', function (ev) {
    if (visao === 'mes') { return; }
    if (ev.pointerType === 'mouse' && ev.button !== 0) { return; }
    var alvo = ev.target.closest('.cal-evento');
    if (!alvo) { return; }
    var evento = porId(alvo.dataset.id);
    if (!evento) { return; }
    var colunas = Array.from(wrap.querySelectorAll('.cal-col'));
    var idx = colunas.indexOf(alvo.parentElement);
    ctx = {
      el: alvo, evento: evento, redim: !!ev.target.closest('.cal-resize'),
      x: ev.clientX, y: ev.clientY, moveu: false, colunas: colunas, idxOrig: idx, idxNovo: idx,
      ini: minDia(evento._ini), fim: minDia(evento._fim)
    };
    ctx.novoIni = ctx.ini; ctx.novoFim = ctx.fim;
    try { alvo.setPointerCapture(ev.pointerId); } catch (e) { /* ignora */ }
    ev.preventDefault();
  });

  wrap.addEventListener('pointermove', function (ev) {
    if (!ctx) { return; }
    var dx = ev.clientX - ctx.x, dy = ev.clientY - ctx.y;
    if (!ctx.moveu && Math.abs(dx) < 4 && Math.abs(dy) < 4) { return; }
    ctx.moveu = true;
    ctx.el.classList.add('movendo');
    var delta = Math.round(dy / HP * 60 / SNAP) * SNAP;
    if (ctx.redim) {
      ctx.novoFim = limitar(ctx.fim + delta, ctx.ini + SNAP, 1439);
      ctx.el.style.height = Math.max((ctx.novoFim - ctx.ini) / 60 * HP - 1, 22) + 'px';
    } else {
      var dur = ctx.fim - ctx.ini;
      ctx.novoIni = limitar(ctx.ini + delta, 0, 1439 - dur);
      ctx.novoFim = ctx.novoIni + dur;
      ctx.el.style.top = (ctx.novoIni / 60 * HP) + 'px';
      ctx.colunas.forEach(function (c, i) {
        var rc = c.getBoundingClientRect();
        if (ev.clientX >= rc.left && ev.clientX < rc.right) { ctx.idxNovo = i; }
      });
      var deslocamento = ctx.colunas[ctx.idxNovo].getBoundingClientRect().left - ctx.colunas[ctx.idxOrig].getBoundingClientRect().left;
      ctx.el.style.transform = 'translateX(' + deslocamento + 'px)';
    }
  });

  function finalizarArrasto(cancelar) {
    if (!ctx) { return; }
    var c = ctx;
    ctx = null;
    c.el.classList.remove('movendo');
    if (cancelar) { desenhar(); return; }
    if (!c.moveu) { abrirEdicao(c.evento); return; }
    var dia = parse(c.colunas[c.idxNovo].dataset.data + 'T00:00');
    var mudou = c.novoIni !== c.ini || c.novoFim !== c.fim || c.idxNovo !== c.idxOrig;
    if (!mudou) { desenhar(); return; }
    mover(c.evento, dataHoraMin(dia, c.novoIni), dataHoraMin(dia, c.novoFim));
  }
  wrap.addEventListener('pointerup', function () { finalizarArrasto(false); });
  wrap.addEventListener('pointercancel', function () { finalizarArrasto(true); });

  /* ---------- interação: clique em espaço vazio / chips ---------- */
  wrap.addEventListener('click', function (ev) {
    if (ctx) { return; }
    var chip = ev.target.closest('.cal-chip');
    if (chip) { var e = porId(chip.dataset.id); if (e) { abrirEdicao(e); } return; }
    if (ev.target.closest('.cal-evento')) { return; }
    var col = ev.target.closest('.cal-col');
    if (col) {
      var y = ev.clientY - col.getBoundingClientRect().top;
      var min = limitar(Math.floor(y / HP * 2) * 30, 0, 22 * 60);
      abrirNovo(col.dataset.data, min, min + 60);
      return;
    }
    var cel = ev.target.closest('.cal-celula');
    if (cel) { abrirNovo(cel.dataset.data, 9 * 60, 10 * 60); }
  });

  /* ---------- interação: arrastar chips no mês (HTML5 DnD) ---------- */
  var chipArrastado = null;
  wrap.addEventListener('dragstart', function (ev) {
    var chip = ev.target.closest('.cal-chip');
    if (!chip) { return; }
    chipArrastado = chip;
    ev.dataTransfer.effectAllowed = 'move';
    ev.dataTransfer.setData('text/plain', chip.dataset.id);
  });
  wrap.addEventListener('dragover', function (ev) {
    var cel = ev.target.closest('.cal-celula');
    wrap.querySelectorAll('.cal-celula.alvo').forEach(function (c) { c.classList.remove('alvo'); });
    if (chipArrastado && cel) { ev.preventDefault(); cel.classList.add('alvo'); }
  });
  wrap.addEventListener('drop', function (ev) {
    var cel = ev.target.closest('.cal-celula');
    wrap.querySelectorAll('.cal-celula.alvo').forEach(function (c) { c.classList.remove('alvo'); });
    if (!chipArrastado || !cel) { return; }
    ev.preventDefault();
    var e = porId(chipArrastado.dataset.id);
    chipArrastado = null;
    if (!e || cel.dataset.data === isoData(e._ini)) { return; }
    mover(e, cel.dataset.data + 'T' + hhmm(minDia(e._ini)) + ':00', cel.dataset.data + 'T' + hhmm(minDia(e._fim)) + ':00');
  });
  wrap.addEventListener('dragend', function () { chipArrastado = null; });

  /* ---------- modal ---------- */
  var modalEl = document.getElementById('modal-atividade');
  var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  var form = document.getElementById('form-atividade');
  var btnExcluir = document.getElementById('atv-excluir');
  var rotuloDuracao = document.getElementById('atv-duracao');

  function atualizarDuracao() {
    var a = form.elements.hora_inicio.value, b = form.elements.hora_fim.value;
    if (!a || !b) { rotuloDuracao.textContent = '—'; return; }
    var ma = parseInt(a.slice(0, 2), 10) * 60 + parseInt(a.slice(3, 5), 10);
    var mb = parseInt(b.slice(0, 2), 10) * 60 + parseInt(b.slice(3, 5), 10);
    rotuloDuracao.textContent = mb > ma ? formatarMin(mb - ma) : 'o término deve ser depois do início';
  }
  form.elements.hora_inicio.addEventListener('input', atualizarDuracao);
  form.elements.hora_fim.addEventListener('input', atualizarDuracao);

  function abrirNovo(dataIso, minIni, minFim) {
    idEditando = null;
    form.reset();
    form.classList.remove('was-validated');
    document.getElementById('atv-modal-titulo').textContent = 'Nova atividade';
    form.elements.data.value = dataIso;
    form.elements.hora_inicio.value = hhmm(minIni);
    form.elements.hora_fim.value = hhmm(Math.min(minFim, 1439));
    form.elements.status.value = 'Planejada';
    var filtro = document.getElementById('cal-filtro').value;
    if (filtro) { form.elements.materia_id.value = filtro; }
    btnExcluir.classList.add('d-none');
    atualizarDuracao();
    modal.show();
  }

  function abrirEdicao(e) {
    idEditando = e.id;
    form.reset();
    form.classList.remove('was-validated');
    document.getElementById('atv-modal-titulo').textContent = 'Editar atividade';
    form.elements.titulo.value = e.titulo;
    form.elements.materia_id.value = e.materia_id;
    form.elements.status.value = e.status;
    form.elements.descricao.value = e.descricao;
    form.elements.data.value = isoData(e._ini);
    form.elements.hora_inicio.value = hhmm(minDia(e._ini));
    form.elements.hora_fim.value = hhmm(minDia(e._fim));
    btnExcluir.classList.remove('d-none');
    atualizarDuracao();
    modal.show();
  }

  form.addEventListener('submit', async function (ev) {
    ev.preventDefault();
    form.classList.add('was-validated');
    if (!form.checkValidity()) { return; }
    var f = form.elements;
    var corpo = {
      titulo: f.titulo.value, materia_id: f.materia_id.value, status: f.status.value,
      descricao: f.descricao.value,
      inicio: f.data.value + 'T' + f.hora_inicio.value + ':00',
      fim: f.data.value + 'T' + f.hora_fim.value + ':00'
    };
    var url = idEditando ? URL_BASE + '/' + idEditando : URL_BASE;
    var r = await window.api(url, { method: idEditando ? 'PUT' : 'POST', corpo: corpo });
    if (r.ok) {
      modal.hide();
      window.toast(r.dados.mensagem || 'Atividade salva.', 'success');
      var dia = parse(corpo.inicio.slice(0, 16));
      if (dia < intervalo()[0] || dia >= intervalo()[1]) { cursor = dia; }
      carregar();
    }
  });

  btnExcluir.addEventListener('click', async function () {
    if (!idEditando || !window.confirm('Excluir esta atividade? Esta ação não pode ser desfeita.')) { return; }
    var r = await window.api(URL_BASE + '/' + idEditando, { method: 'DELETE' });
    if (r.ok) { modal.hide(); window.toast('Atividade excluída.', 'success'); carregar(); }
  });

  /* ---------- barra de ferramentas ---------- */
  function navegar(sentido) {
    if (visao === 'dia') { cursor = somar(cursor, sentido); }
    else if (visao === 'semana') { cursor = somar(cursor, 7 * sentido); }
    else { cursor = new Date(cursor.getFullYear(), cursor.getMonth() + sentido, 1); }
    carregar();
  }
  document.getElementById('cal-prev').addEventListener('click', function () { navegar(-1); });
  document.getElementById('cal-prox').addEventListener('click', function () { navegar(1); });
  document.getElementById('cal-hoje').addEventListener('click', function () { cursor = new Date(); carregar(); });
  document.getElementById('cal-filtro').addEventListener('change', carregar);
  document.getElementById('cal-nova').addEventListener('click', function () {
    var agora = new Date();
    var min = Math.min((agora.getHours() + 1) * 60, 22 * 60);
    abrirNovo(isoData(visao === 'mes' ? agora : cursor), min, min + 60);
  });
  document.querySelectorAll('[data-visao]').forEach(function (b) {
    b.addEventListener('click', function () {
      visao = b.dataset.visao;
      try { localStorage.setItem('studyflow.cal.visao', visao); } catch (e) { /* ignora */ }
      carregar();
    });
  });

  carregar();
});
