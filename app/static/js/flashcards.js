/* StudyFlow — modo de estudo dos flashcards: virar, navegar, embaralhar e avaliar. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var raiz = document.getElementById('estudo');
  if (!raiz) { return; }

  var cartoes = (window.CARTOES || []).slice();
  var i = 0;
  var cartao = document.getElementById('fc-card');
  var CORES = { 'Fácil': 'success', 'Médio': 'warning', 'Difícil': 'danger', 'Não avaliado': 'secondary' };

  function el(id) { return document.getElementById(id); }

  function mostrar() {
    var c = cartoes[i];
    cartao.classList.remove('virado');
    el('fc-frente').textContent = c.pergunta;
    el('fc-verso').textContent = c.resposta;
    el('fc-materia').textContent = c.materia;
    el('fc-pos').textContent = (i + 1) + ' / ' + cartoes.length;
    var dif = el('fc-dif');
    dif.className = 'badge text-bg-' + (CORES[c.dificuldade] || 'secondary');
    dif.textContent = c.dificuldade;
    el('fc-prev').disabled = i === 0;
    el('fc-next').disabled = i === cartoes.length - 1;
  }
  function virar() { cartao.classList.toggle('virado'); }
  function ir(delta) {
    var novo = i + delta;
    if (novo < 0 || novo >= cartoes.length) { return; }
    i = novo;
    mostrar();
  }

  cartao.addEventListener('click', virar);
  el('fc-virar').addEventListener('click', virar);
  el('fc-prev').addEventListener('click', function () { ir(-1); });
  el('fc-next').addEventListener('click', function () { ir(1); });
  el('fc-embaralhar').addEventListener('click', function () {
    for (var k = cartoes.length - 1; k > 0; k--) {       // Fisher–Yates
      var j = Math.floor(Math.random() * (k + 1));
      var t = cartoes[k]; cartoes[k] = cartoes[j]; cartoes[j] = t;
    }
    i = 0;
    mostrar();
    window.toast('Cartões embaralhados.', 'info');
  });

  document.querySelectorAll('.fc-avaliar').forEach(function (botao) {
    botao.addEventListener('click', async function () {
      var c = cartoes[i];
      var url = raiz.dataset.urlAvaliar.replace('/0/', '/' + c.id + '/');
      var r = await window.api(url, { method: 'POST', corpo: { dificuldade: botao.dataset.dif } });
      if (!r.ok) { return; }
      c.dificuldade = botao.dataset.dif;
      if (i < cartoes.length - 1) {
        window.toast('Marcado como ' + c.dificuldade + '.', 'success');
        ir(1);
      } else {
        mostrar();
        window.toast('Marcado como ' + c.dificuldade + '. Você chegou ao último cartão!', 'success');
      }
    });
  });

  document.addEventListener('keydown', function (ev) {
    var alvo = ev.target.tagName;
    if (alvo === 'INPUT' || alvo === 'TEXTAREA' || alvo === 'SELECT' || document.querySelector('.modal.show')) { return; }
    if (ev.key === 'ArrowRight') { ir(1); }
    else if (ev.key === 'ArrowLeft') { ir(-1); }
    else if (ev.key === ' ' || ev.key === 'Enter') { ev.preventDefault(); virar(); }
  });

  mostrar();
});
