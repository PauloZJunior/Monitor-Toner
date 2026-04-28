// main.js — Inicialização da aplicação

document.addEventListener('DOMContentLoaded', () => {
  // Busca
  document.getElementById('searchBox').addEventListener('input', renderizar);

  // Verifica autenticação e inicia
  verificarAuth();
  setInterval(verificarAuth, 5 * 60 * 1000);

  // Carrega dados iniciais
  carregarDados();
});
