/* StudyFlow — reordenação dos conteúdos por arrastar e soltar. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var tabela = document.getElementById('tabela-conteudos');
  if (!tabela) { return; }
  var corpo = tabela.tBodies[0];
  var arrastada = null;
  var ordemOriginal = null;

  function limparMarcas() {
    corpo.querySelectorAll('.alvo-acima, .alvo-abaixo').forEach(function (tr) {
      tr.classList.remove('alvo-acima', 'alvo-abaixo');
    });
  }
  function ids() {
    return Array.from(corpo.querySelectorAll('tr[data-id]')).map(function (tr) { return parseInt(tr.dataset.id, 10); });
  }
  function renumerar() {
    corpo.querySelectorAll('tr[data-id]').forEach(function (tr, i) {
      tr.querySelector('.ordem-num').textContent = i + 1;
    });
  }

  corpo.addEventListener('dragstart', function (ev) {
    var linha = ev.target.closest('tr[data-id]');
    if (!linha) { return; }
    arrastada = linha;
    ordemOriginal = Array.from(corpo.children);
    linha.classList.add('arrastando');
    ev.dataTransfer.effectAllowed = 'move';
    ev.dataTransfer.setData('text/plain', linha.dataset.id);
  });

  corpo.addEventListener('dragover', function (ev) {
    if (!arrastada) { return; }
    ev.preventDefault();
    var alvo = ev.target.closest('tr[data-id]');
    limparMarcas();
    if (!alvo || alvo === arrastada) { return; }
    var caixa = alvo.getBoundingClientRect();
    var acima = ev.clientY < caixa.top + caixa.height / 2;
    alvo.classList.add(acima ? 'alvo-acima' : 'alvo-abaixo');
  });

  corpo.addEventListener('drop', async function (ev) {
    if (!arrastada) { return; }
    ev.preventDefault();
    var alvo = ev.target.closest('tr[data-id]');
    if (alvo && alvo !== arrastada) {
      var caixa = alvo.getBoundingClientRect();
      var acima = ev.clientY < caixa.top + caixa.height / 2;
      corpo.insertBefore(arrastada, acima ? alvo : alvo.nextSibling);
    }
    limparMarcas();
    arrastada.classList.remove('arrastando');
    var linha = arrastada;
    arrastada = null;
    renumerar();
    var r = await window.api(tabela.dataset.urlReordenar, { method: 'POST', corpo: { ids: ids() } });
    if (r.ok) {
      window.toast('Nova ordem salva.', 'success');
    } else if (ordemOriginal) {            // desfaz visualmente em caso de erro
      ordemOriginal.forEach(function (tr) { corpo.appendChild(tr); });
      renumerar();
    }
    linha.classList.remove('arrastando');
  });

  corpo.addEventListener('dragend', function () {
    limparMarcas();
    if (arrastada) { arrastada.classList.remove('arrastando'); arrastada = null; }
  });
});
