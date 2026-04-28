// auth.js — Autenticação de administrador

async function verificarAuth() {
  try {
    const res  = await fetch('/auth/status');
    const data = await res.json();
    _isAutenticado = data.autenticado;
    document.getElementById('authBadge').classList.toggle('visible', _isAutenticado);
  } catch(e) {
    _isAutenticado = false;
  }
}

function exigirAuth(callback) {
  if (_isAutenticado) { callback(); return; }
  _authCallback = callback;
  document.getElementById('authSenha').value = '';
  document.getElementById('authError').classList.add('hidden');
  document.getElementById('authModal').classList.remove('hidden');
  setTimeout(() => document.getElementById('authSenha').focus(), 100);
}

function fecharAuth() {
  document.getElementById('authModal').classList.add('hidden');
  _authCallback = null;
}

function toggleSenha() {
  const input = document.getElementById('authSenha');
  input.type = input.type === 'password' ? 'text' : 'password';
}

async function confirmarSenha() {
  const senha = document.getElementById('authSenha').value;
  const btn   = document.getElementById('btnConfirmarSenha');
  if (!senha) { mostrarErroAuth('Digite a senha'); return; }
  btn.classList.add('loading');
  try {
    const res  = await fetch('/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ senha }),
    });
    const data = await res.json();
    if (res.ok) {
      _isAutenticado = true;
      document.getElementById('authBadge').classList.add('visible');
      document.getElementById('authModal').classList.add('hidden');
      document.getElementById('authError').classList.add('hidden');
      if (_authCallback) { const cb = _authCallback; _authCallback = null; cb(); }
    } else if (res.status === 429) {
      // Rate limit atingido
      mostrarErroAuth(data.erro || 'Muitas tentativas. Aguarde antes de tentar novamente.');
      document.getElementById('btnConfirmarSenha').disabled = true;
      setTimeout(() => {
        document.getElementById('btnConfirmarSenha').disabled = false;
      }, 30000);
    } else {
      mostrarErroAuth(data.erro || 'Senha incorreta');
      document.getElementById('authSenha').select();
    }
  } catch(e) {
    mostrarErroAuth('Erro de conexão');
  } finally {
    btn.classList.remove('loading');
  }
}

function mostrarErroAuth(msg) {
  document.getElementById('authErrorMsg').textContent = msg;
  document.getElementById('authError').classList.remove('hidden');
}

async function fazerLogout() {
  await fetch('/auth/logout', { method: 'POST' });
  _isAutenticado = false;
  document.getElementById('authBadge').classList.remove('visible');
}

// Fecha com ESC
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') fecharAuth();
});
