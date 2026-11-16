/* StudyFlow — Kanban de tarefas com arrastar e soltar. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var quadro = document.getElementById('kanban');
  if (!quadro) { return; }
  var arrastado = null;
  var origem = null;
  var proximoIrmao = null;

  function atualizarColunas() {
    quadro.querySelectorAll('.kanban-col').forEach(function (coluna) {
      var corpo = coluna.querySelector('.kanban-col-body');
      var qtd = corpo.querySelectorAll('.kanban-card').length;
      coluna.querySelector('.kanban-count').textContent = qtd;
      corpo.querySelector('.kanban-vazio').classList.toggle('d-none', qtd > 0);
    });
  }

  quadro.addEventListener('dragstart', function (ev) {
    var cartao = ev.target.closest('.kanban-card');
    if (!cartao) { return; }
    arrastado = cartao;
    origem = cartao.parentElement;
    proximoIrmao = cartao.nextElementSibling;
    cartao.classList.add('dragging');
    ev.dataTransfer.effectAllowed = 'move';
    ev.dataTransfer.setData('text/plain', cartao.dataset.id);
  });

  quadro.addEventListener('dragend', function () {
    quadro.querySelectorAll('.kanban-col-body.over').forEach(function (c) { c.classList.remove('over'); });
    if (arrastado) { arrastado.classList.remove('dragging'); }
    arrastado = null;
  });

  quadro.addEventListener('dragover', function (ev) {
    var corpo = ev.target.closest('.kanban-col-body');
    if (!arrastado || !corpo) { return; }
    ev.preventDefault();
    quadro.querySelectorAll('.kanban-col-body.over').forEach(function (c) { if (c !== corpo) { c.classList.remove('over'); } });
    corpo.classList.add('over');
  });

  quadro.addEventListener('dragleave', function (ev) {
    var corpo = ev.target.closest('.kanban-col-body');
    if (corpo && !corpo.contains(ev.relatedTarget)) { corpo.classList.remove('over'); }
  });

  quadro.addEventListener('drop', async function (ev) {
    var corpo = ev.target.closest('.kanban-col-body');
    if (!arrastado || !corpo) { return; }
    ev.preventDefault();
    corpo.classList.remove('over');
    var cartao = arrastado;
    arrastado = null;
    cartao.classList.remove('dragging');
    if (corpo === origem) { return; }

    corpo.insertBefore(cartao, corpo.querySelector('.kanban-vazio'));
    atualizarColunas();

    var novoStatus = corpo.dataset.status;
    var r = await window.api(cartao.dataset.url, { method: 'POST', corpo: { status: novoStatus } });
    if (r.ok) {
      window.toast('Tarefa movida para “' + novoStatus + '”.', 'success');
      if (novoStatus === 'Concluída' || origem.dataset.status === 'Concluída') {
        window.location.reload();   // reordena e recalcula "atrasada"
      }
    } else {                         // desfaz o movimento na tela
      origem.insertBefore(cartao, proximoIrmao && proximoIrmao.parentElement === origem ? proximoIrmao : origem.querySelector('.kanban-vazio'));
      atualizarColunas();
    }
  });
});
