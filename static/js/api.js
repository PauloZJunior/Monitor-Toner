// api.js — Chamadas fetch para o servidor

async function carregarDados() {
  document.getElementById('btnRefresh').classList.add('loading');
  document.getElementById('loadingOverlay').classList.remove('hidden');
  try {
    const res = await fetch('/api/impressoras');
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const err = await res.json(); msg += ': ' + (err.erro || err.message || ''); } catch(_) {}
      throw new Error(msg);
    }
    const data = await res.json();
    if (!data.impressoras) throw new Error('Resposta inválida do servidor');
    todosOsDados = data.impressoras;
    document.getElementById('s-total').textContent   = data.resumo.total;
    document.getElementById('s-online').textContent  = data.resumo.online;
    document.getElementById('s-critico').textContent = data.resumo.criticas + data.resumo.baixas;
    document.getElementById('s-offline').textContent = data.resumo.offline;
    document.getElementById('lastUpdate').textContent = data.atualizado_em;
    popularEmpresas(todosOsDados);
    renderizar();
    clearInterval(countdownTimer);
    countdown = 300;
    iniciarCountdown();
  } catch(e) {
    console.error('Erro ao carregar dados:', e);
    document.getElementById('grid').innerHTML =
      `<div class="empty-state">
        ❌ Erro ao conectar com o servidor.<br>
        <span style="font-size:.75rem;color:var(--text3);font-family:monospace">${e.message}</span><br>
        <button class="btn btn-ghost" style="margin-top:1rem" onclick="carregarDados()">
          Tentar novamente
        </button>
      </div>`;
  } finally {
    document.getElementById('btnRefresh').classList.remove('loading');
    document.getElementById('loadingOverlay').classList.add('hidden');
  }
}

function iniciarCountdown() {
  countdownTimer = setInterval(() => {
    countdown--;
    const m = Math.floor(countdown / 60);
    const s = String(countdown % 60).padStart(2, '0');
    document.getElementById('nextRefresh').textContent = `Próxima atualização em ${m}:${s}`;
    if (countdown <= 0) { clearInterval(countdownTimer); carregarDados(); }
  }, 1000);
}
