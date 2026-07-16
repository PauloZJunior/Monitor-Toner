// wake.js — Despertar impressoras em standby

async function despertarTodas() {
  const btn   = document.getElementById('btnWake');
  const toast = document.getElementById('wakeToast');
  btn.classList.add('loading');
  document.getElementById('wtTitle').textContent      = 'Acordando impressoras...';
  document.getElementById('wtAcordaram').textContent  = '—';
  document.getElementById('wtFalhas').textContent     = '—';
  document.getElementById('wtTotal').textContent      = '—';
  document.getElementById('wtBar').style.cssText      = 'width:0%;background:var(--ok)';
  toast.classList.remove('hidden');

  let prog = 0;
  const pt = setInterval(() => {
    prog = Math.min(prog + 3, 85);
    document.getElementById('wtBar').style.width = prog + '%';
  }, 150);

  try {
    const res  = await fetch('/api/despertar', { method: 'POST' });
    const data = await res.json();
    clearInterval(pt);
    document.getElementById('wtBar').style.width        = '100%';
    document.getElementById('wtTitle').textContent      = '✅ Sinal enviado!';
    document.getElementById('wtAcordaram').textContent  = data.acordaram + ' impressora(s)';
    document.getElementById('wtFalhas').textContent     = data.falhas + ' impressora(s)';
    document.getElementById('wtTotal').textContent      = data.total + ' impressora(s)';
    setTimeout(() => {
      document.getElementById('wtTitle').textContent = '🔄 Verificando...';
      carregarDados(true);
    }, 8000);
  } catch(e) {
    clearInterval(pt);
    document.getElementById('wtTitle').textContent      = '❌ Erro ao enviar sinal';
    document.getElementById('wtBar').style.cssText      = 'width:100%;background:var(--critico)';
  } finally {
    btn.classList.remove('loading');
  }
}
