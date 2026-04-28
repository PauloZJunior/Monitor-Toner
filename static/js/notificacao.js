// notificacao.js — Modal de configuração de alertas/notificações

async function abrirNotificacoes() {
  document.getElementById('notifModalBackdrop').classList.remove('hidden');
  document.getElementById('notifAlert').classList.add('hidden');
  try {
    const cfg = await (await fetch('/notificacao/config')).json();
    document.getElementById('nEmailAtivo').checked   = cfg.email_ativo === '1';
    document.getElementById('nSmtp').value           = cfg.email_smtp || '';
    document.getElementById('nPorta').value          = cfg.email_porta || '587';
    document.getElementById('nUsuario').value        = cfg.email_usuario || '';
    document.getElementById('nSenha').value          = '';
    document.getElementById('nTls').checked          = cfg.email_tls !== '0';
    document.getElementById('nDestinos').value       = cfg.email_destinos || '';
    document.getElementById('nWebhookAtivo').checked = cfg.webhook_ativo === '1';
    document.getElementById('nWebhookUrl').value     = cfg.webhook_url || '';
    document.getElementById('nWebhookTipo').value    = cfg.webhook_tipo || 'generic';
    document.getElementById('nNivel').value          = cfg.nivel_alerta || 'critico';
    document.getElementById('nIntervalo').value      = cfg.intervalo_horas || '4';
  } catch(e) {
    console.error('Erro ao carregar config notificações:', e);
  }
}

function fecharNotificacoes() {
  document.getElementById('notifModalBackdrop').classList.add('hidden');
}

// Chamada pelo HTML quando o toggle de e-mail muda
// Poderia mostrar/esconder campos — por enquanto só registra a mudança
function toggleEmailFields() {
  const ativo = document.getElementById('nEmailAtivo').checked;
  const fields = document.getElementById('emailFields');
  if (fields) {
    fields.style.opacity = ativo ? '1' : '0.5';
    fields.style.pointerEvents = ativo ? '' : 'none';
  }
}

async function salvarNotificacoes() {
  if (!_isAutenticado) { exigirAuth(salvarNotificacoes); return; }
  const cfg = {
    email_ativo:     document.getElementById('nEmailAtivo').checked ? '1' : '0',
    email_smtp:      document.getElementById('nSmtp').value.trim(),
    email_porta:     document.getElementById('nPorta').value.trim(),
    email_usuario:   document.getElementById('nUsuario').value.trim(),
    email_tls:       document.getElementById('nTls').checked ? '1' : '0',
    email_destinos:  document.getElementById('nDestinos').value.trim(),
    webhook_ativo:   document.getElementById('nWebhookAtivo').checked ? '1' : '0',
    webhook_url:     document.getElementById('nWebhookUrl').value.trim(),
    webhook_tipo:    document.getElementById('nWebhookTipo').value,
    nivel_alerta:    document.getElementById('nNivel').value,
    intervalo_horas: document.getElementById('nIntervalo').value,
  };
  const senha = document.getElementById('nSenha').value;
  if (senha) cfg.email_senha = senha;

  const res  = await fetch('/notificacao/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(cfg),
  });
  if (res.status === 401) { _isAutenticado = false; exigirAuth(salvarNotificacoes); return; }
  const data = await res.json();
  _mostrarAlertaNotif(res.ok ? 'success' : 'danger', data.mensagem || data.erro);
  if (res.ok) setTimeout(() => document.getElementById('notifAlert').classList.add('hidden'), 3000);
}

async function testarEmail() {
  if (!_isAutenticado) { exigirAuth(testarEmail); return; }
  const cfg = {
    email_smtp:      document.getElementById('nSmtp').value,
    email_porta:     document.getElementById('nPorta').value,
    email_usuario:   document.getElementById('nUsuario').value,
    email_tls:       document.getElementById('nTls').checked ? '1' : '0',
    email_destinos:  document.getElementById('nDestinos').value,
  };
  const senha = document.getElementById('nSenha').value;
  if (senha) cfg.email_senha = senha;
  const res  = await fetch('/notificacao/testar/email', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cfg),
  });
  const data = await res.json();
  _mostrarAlertaNotif(data.sucesso ? 'success' : 'danger', data.mensagem);
}

async function testarWebhook() {
  if (!_isAutenticado) { exigirAuth(testarWebhook); return; }
  const cfg = {
    webhook_url:  document.getElementById('nWebhookUrl').value,
    webhook_tipo: document.getElementById('nWebhookTipo').value,
  };
  const res  = await fetch('/notificacao/testar/webhook', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cfg),
  });
  const data = await res.json();
  _mostrarAlertaNotif(data.sucesso ? 'success' : 'danger', data.mensagem);
}

function _mostrarAlertaNotif(tipo, msg) {
  const el = document.getElementById('notifAlert');
  el.className = `alert alert-${tipo}`;
  document.getElementById('notifAlertMsg').textContent = msg;
  el.classList.remove('hidden');
}
