/**
 * events.js
 * ─────────────────────────────────────────────────────────────
 * Centraliza TODOS os addEventListener do projeto.
 * Substitui os atributos onclick/onchange/onkeydown removidos do HTML.
 *
 * Carregado por ÚLTIMO no index.html (após todos os outros scripts),
 * garantindo que as funções dos demais módulos já estejam disponíveis.
 * ─────────────────────────────────────────────────────────────
 */

document.addEventListener('DOMContentLoaded', function () {

  /* ══════════════════════════════════════════
     HEADER — botões principais
  ══════════════════════════════════════════ */

  const btnWake = document.getElementById('btnWake');
  if (btnWake) btnWake.addEventListener('click', despertarTodas);

  const btnRefresh = document.getElementById('btnRefresh');
  if (btnRefresh) btnRefresh.addEventListener('click', () => carregarDados(true));

  const btnLogout = document.getElementById('btnLogout');
  if (btnLogout) btnLogout.addEventListener('click', fazerLogout);

  const btnNotificacoes = document.getElementById('btnNotificacoes');
  if (btnNotificacoes) btnNotificacoes.addEventListener('click', abrirNotificacoes);

  const btnGerenciar = document.getElementById('btnGerenciar');
  if (btnGerenciar) btnGerenciar.addEventListener('click', abrirGerenciador);

  const btnTema = document.getElementById('btnTema');
  if (btnTema) btnTema.addEventListener('click', alternarTema);

  /* ══════════════════════════════════════════
     TOOLBAR — filtros e busca
  ══════════════════════════════════════════ */

  const selStatus = document.getElementById('selStatus');
  if (selStatus) selStatus.addEventListener('change', function () {
    filtrarStatus(this.value);
  });

  const selEmpresa = document.getElementById('selEmpresa');
  if (selEmpresa) selEmpresa.addEventListener('change', function () {
    filtrarEmpresa(this.value || null);
  });

  const selTipo = document.getElementById('selTipo');
  if (selTipo) selTipo.addEventListener('change', function () {
    filtrarTipo(this.value || null);
  });

  /* ══════════════════════════════════════════
     WAKE TOAST
  ══════════════════════════════════════════ */

  const btnWakeToastClose = document.getElementById('btnWakeToastClose');
  if (btnWakeToastClose) btnWakeToastClose.addEventListener('click', function () {
    document.getElementById('wakeToast').classList.add('hidden');
  });

  /* ══════════════════════════════════════════
     MODAL GERENCIADOR
  ══════════════════════════════════════════ */

  const modalBackdrop = document.getElementById('modalBackdrop');
  if (modalBackdrop) modalBackdrop.addEventListener('click', fecharSeClicouFora);

  const btnFecharModal = document.getElementById('btnFecharModal');
  if (btnFecharModal) btnFecharModal.addEventListener('click', fecharModal);

  // Tabs do modal — usa data-tab para identificar qual aba abrir
  document.querySelectorAll('.modal-tab[data-tab]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      mudarTab(this.dataset.tab);
    });
  });

  const btnCancelarForm = document.getElementById('btnCancelarForm');
  if (btnCancelarForm) btnCancelarForm.addEventListener('click', cancelarForm);

  const btnSalvar = document.getElementById('btnSalvar');
  if (btnSalvar) btnSalvar.addEventListener('click', salvarImpressora);

  /* ══════════════════════════════════════════
     CONFIRM DIALOG
  ══════════════════════════════════════════ */

  const btnFecharConfirm = document.getElementById('btnFecharConfirm');
  if (btnFecharConfirm) btnFecharConfirm.addEventListener('click', fecharConfirm);

  /* ══════════════════════════════════════════
     MODAL DE SENHA (Auth)
  ══════════════════════════════════════════ */

  const authSenha = document.getElementById('authSenha');
  if (authSenha) authSenha.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') confirmarSenha();
  });

  const authToggle = document.getElementById('authToggle');
  if (authToggle) authToggle.addEventListener('click', toggleSenha);

  const btnFecharAuth = document.getElementById('btnFecharAuth');
  if (btnFecharAuth) btnFecharAuth.addEventListener('click', fecharAuth);

  const btnConfirmarSenha = document.getElementById('btnConfirmarSenha');
  if (btnConfirmarSenha) btnConfirmarSenha.addEventListener('click', confirmarSenha);

  /* ══════════════════════════════════════════
     MODAL HISTÓRICO
  ══════════════════════════════════════════ */

  const histModalBackdrop = document.getElementById('histModalBackdrop');
  if (histModalBackdrop) histModalBackdrop.addEventListener('click', function (e) {
    if (e.target === this) fecharHistorico();
  });

  const btnFecharHistorico = document.getElementById('btnFecharHistorico');
  if (btnFecharHistorico) btnFecharHistorico.addEventListener('click', fecharHistorico);

  // Botões de seleção de período (7 / 15 / 30 / 60 dias)
  document.querySelectorAll('.dias-btn[data-dias]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      mudarDias(parseInt(this.dataset.dias, 10), this);
    });
  });

  /* ══════════════════════════════════════════
     MODAL NOTIFICAÇÕES
  ══════════════════════════════════════════ */

  const notifModalBackdrop = document.getElementById('notifModalBackdrop');
  if (notifModalBackdrop) notifModalBackdrop.addEventListener('click', function (e) {
    if (e.target === this) fecharNotificacoes();
  });

  const btnFecharNotificacoes = document.getElementById('btnFecharNotificacoes');
  if (btnFecharNotificacoes) btnFecharNotificacoes.addEventListener('click', fecharNotificacoes);

  const btnCancelarNotificacoes = document.getElementById('btnCancelarNotificacoes');
  if (btnCancelarNotificacoes) btnCancelarNotificacoes.addEventListener('click', fecharNotificacoes);

  const nEmailAtivo = document.getElementById('nEmailAtivo');
  if (nEmailAtivo) nEmailAtivo.addEventListener('change', toggleEmailFields);

  const btnTestarEmail = document.getElementById('btnTestarEmail');
  if (btnTestarEmail) btnTestarEmail.addEventListener('click', testarEmail);

  const btnTestarWebhook = document.getElementById('btnTestarWebhook');
  if (btnTestarWebhook) btnTestarWebhook.addEventListener('click', testarWebhook);

  const btnSalvarNotificacoes = document.getElementById('btnSalvarNotificacoes');
  if (btnSalvarNotificacoes) btnSalvarNotificacoes.addEventListener('click', salvarNotificacoes);

});
