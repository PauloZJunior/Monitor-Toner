// theme.js — Alternância de tema claro/escuro

function alternarTema() {
  const html = document.documentElement;
  const novo  = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', novo);
  localStorage.setItem('tema', novo);
  _atualizarIconeTema(novo);
}

function _atualizarIconeTema(tema) {
  document.querySelector('.icon-moon').style.display = tema === 'dark'  ? 'block' : 'none';
  document.querySelector('.icon-sun').style.display  = tema === 'light' ? 'block' : 'none';
}

// Aplica tema salvo ao carregar
(function () {
  const t = localStorage.getItem('tema') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
  // Ícones são inicializados após DOM carregar
  document.addEventListener('DOMContentLoaded', () => _atualizarIconeTema(t));
})();
