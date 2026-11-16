/* StudyFlow — comportamentos das telas de acesso e de "Minha conta":
 * mostrar/ocultar senha, aviso de Caps Lock, medidor de força, confirmação de senha
 * e ações da tela de códigos de recuperação (copiar, baixar, imprimir). */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';

  /* ---------- Mostrar / ocultar senha ---------- */
  document.querySelectorAll('[data-toggle-senha]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      var campo = document.getElementById(botao.dataset.toggleSenha);
      var mostrar = campo.type === 'password';
      campo.type = mostrar ? 'text' : 'password';
      botao.querySelector('i').className = mostrar ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
  });

  /* ---------- Aviso de Caps Lock ---------- */
  document.querySelectorAll('input[type="password"]').forEach(function (campo) {
    var aviso = campo.closest('.mb-3') && campo.closest('.mb-3').querySelector('.caps-aviso');
    if (!aviso) { return; }
    function checar(ev) {
      if (ev.getModifierState) { aviso.classList.toggle('d-none', !ev.getModifierState('CapsLock')); }
    }
    campo.addEventListener('keydown', checar);
    campo.addEventListener('keyup', checar);
    campo.addEventListener('blur', function () { aviso.classList.add('d-none'); });
  });

  /* ---------- Medidor de força ---------- */
  document.querySelectorAll('input[data-forca]').forEach(function (campo) {
    var barra = document.getElementById(campo.id + '-forca');
    var dica = document.getElementById(campo.id + '-dica');
    var niveis = [
      { txt: 'Muito fraca', cor: '#dc3545', pct: 20 }, { txt: 'Fraca', cor: '#fd7e14', pct: 40 },
      { txt: 'Razoável', cor: '#f59e0b', pct: 60 }, { txt: 'Boa', cor: '#22c55e', pct: 80 },
      { txt: 'Forte', cor: '#16a34a', pct: 100 }
    ];
    campo.addEventListener('input', function () {
      var s = campo.value, pontos = 0;
      if (s.length >= 8) { pontos++; }
      if (s.length >= 12) { pontos++; }
      if (/[a-z]/.test(s) && /[A-Z]/.test(s)) { pontos++; }
      if (/\d/.test(s) && /[A-Za-z]/.test(s)) { pontos++; }
      if (/[^A-Za-z0-9]/.test(s)) { pontos++; }
      if (!s) { barra.style.width = '0'; dica.textContent = 'Mínimo de 8 caracteres, com letras e números.'; return; }
      var n = niveis[Math.max(0, Math.min(4, pontos - 1))];
      if (s.length < 8 || !/\d/.test(s) || !/[A-Za-z]/.test(s)) { n = niveis[0]; }
      barra.style.width = n.pct + '%';
      barra.style.backgroundColor = n.cor;
      dica.textContent = 'Força: ' + n.txt + (n === niveis[0] ? ' — use 8+ caracteres com letras e números.' : '');
    });
  });

  /* ---------- Confirmação de senha (validação nativa + Bootstrap) ---------- */
  document.querySelectorAll('input[data-confirma]').forEach(function (campo) {
    var original = document.getElementById(campo.dataset.confirma);
    function comparar() {
      campo.setCustomValidity(campo.value && campo.value !== original.value ? 'As senhas não conferem.' : '');
    }
    campo.addEventListener('input', comparar);
    original.addEventListener('input', comparar);
  });

  /* ---------- Tela de códigos de recuperação ---------- */
  var area = document.getElementById('area-codigos');
  if (!area) { return; }
  var codigos = Array.from(area.querySelectorAll('[data-codigo]')).map(function (e) { return e.textContent.trim(); });

  var confirmou = document.getElementById('confirmou');
  var continuar = document.getElementById('btn-continuar');
  confirmou.addEventListener('change', function () {
    continuar.classList.toggle('disabled', !confirmou.checked);
    continuar.setAttribute('aria-disabled', confirmou.checked ? 'false' : 'true');
  });

  document.getElementById('btn-copiar').addEventListener('click', async function () {
    var texto = codigos.join('\n');
    try {
      await navigator.clipboard.writeText(texto);
      window.toast('Códigos copiados. Cole em um local seguro.', 'success');
    } catch (e) {
      var area2 = document.createElement('textarea');
      area2.value = texto; document.body.appendChild(area2); area2.select();
      try { document.execCommand('copy'); window.toast('Códigos copiados.', 'success'); } catch (e2) { /* ignora */ }
      area2.remove();
    }
  });

  document.getElementById('btn-baixar').addEventListener('click', function () {
    var linhas = ['StudyFlow — códigos de recuperação', 'Usuário: ' + area.dataset.usuario,
      'Gerados em: ' + new Date().toLocaleString('pt-BR'), '',
      'Cada código funciona uma única vez. Guarde este arquivo fora do computador.', ''];
    codigos.forEach(function (c, i) { linhas.push((i + 1) + '. ' + c); });
    var blob = new Blob([linhas.join('\r\n')], { type: 'text/plain;charset=utf-8' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'studyflow-codigos-de-recuperacao.txt';
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
  });

  document.getElementById('btn-imprimir').addEventListener('click', function () { window.print(); });
});
