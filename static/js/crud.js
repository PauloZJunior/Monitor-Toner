// crud.js — Gerenciamento de impressoras (CRUD)

// ─── Modal ───────────────────────────────────────────
function abrirGerenciador() {
  if (!_isAutenticado) { exigirAuth(abrirGerenciador); return; }
  document.getElementById('modalBackdrop').classList.remove('hidden');
  mudarTab('lista');
  carregarLista();
}

function fecharModal() {
  document.getElementById('modalBackdrop').classList.add('hidden');
  esconderAlerta();
}

function fecharSeClicouFora(e) {
  if (e.target === document.getElementById('modalBackdrop')) fecharModal();
}

function mudarTab(tab) {
  tabAtual = tab;
  document.querySelectorAll('.modal-tab').forEach((t, i) => {
    t.classList.toggle('active', (i===0 && tab==='lista') || (i===1 && tab==='form'));
  });
  document.getElementById('tab-lista').classList.toggle('active', tab==='lista');
  document.getElementById('tab-form').classList.toggle('active',  tab==='form');
  esconderAlerta();
  if (tab === 'lista') carregarLista();
  if (tab === 'form' && !document.getElementById('formId').value) limparForm();
}

// ─── Lista ───────────────────────────────────────────
async function carregarLista() {
  const list = document.getElementById('printerList');
  list.innerHTML = '<div style="padding:1rem;text-align:center;color:var(--text3);font-size:.8rem">Carregando...</div>';
  try {
    const res  = await fetch('/gerenciar/impressoras');
    const data = await res.json();
    const imps = data.impressoras;
    document.getElementById('listEmpty').classList.toggle('hidden', imps.length > 0);
    if (!imps.length) { list.innerHTML = ''; return; }
    list.innerHTML = imps.map(imp => `
      <div class="printer-row">
        <div class="pr-info">
          <div class="pr-name">
            ${imp.ativo == 0 ? '<span style="color:var(--text3);font-size:.65rem;margin-right:.3rem">[INATIVO]</span>' : ''}
            ${imp.nome}
          </div>
          <div class="pr-sub">
            <span>${imp.ip}</span>
            ${imp.modelo?`<span>${imp.modelo}</span>`:''}
            ${imp.setor?`<span>${imp.setor}</span>`:''}
            ${imp.empresa?`<span class="pr-empresa">${imp.empresa}</span>`:''}
            ${imp.tipo==='etiqueta'?'<span style="color:var(--accent)">🏷️ Etiqueta</span>':''}
          </div>
        </div>
        <div class="pr-actions">
          <button class="btn btn-ghost" style="font-size:.72rem;padding:.28rem .6rem"
                  onclick="editarImpressora(${imp.id})">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg> Editar
          </button>
          <button class="btn btn-danger" style="font-size:.72rem;padding:.28rem .6rem"
                  onclick="confirmarExclusao(${imp.id},'${imp.nome.replace(/'/g,"\\'").replace(/"/g,'\\"')}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
            </svg> Excluir
          </button>
        </div>
      </div>`).join('');
  } catch(e) {
    list.innerHTML = `<div style="padding:1rem;color:var(--critico);font-size:.8rem">Erro: ${e.message}</div>`;
  }
}

// ─── Formulário ──────────────────────────────────────
function limparForm() {
  document.getElementById('formId').value      = '';
  document.getElementById('fNome').value       = '';
  document.getElementById('fIp').value         = '';
  document.getElementById('fModelo').value     = '';
  document.getElementById('fCommunity').value  = 'public';
  document.getElementById('fSetor').value      = '';
  document.getElementById('fEmpresa').value    = '';
  document.getElementById('fSerial').value     = '';
  document.getElementById('fMac').value        = '';
  document.getElementById('fTipo').value       = 'toner';
  _atualizarHintsTipo('toner');
  document.getElementById('btnSalvar').innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">' +
    '<path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>' +
    '<polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Salvar';
  document.getElementById('modalTitle').textContent = 'Gerenciar Impressoras';
}

function _atualizarHintsTipo(tipo) {
  const isEtiq = tipo === 'etiqueta';
  const ch = document.getElementById('communityHint');
  const th = document.getElementById('tipoHint');
  if (ch) ch.style.display = isEtiq ? 'block' : 'none';
  if (th) th.textContent = isEtiq
    ? '⚠️ Etiqueta: apenas verifica online/offline, sem leitura de toner'
    : 'Toner/Tinta: lê nível via SNMP automaticamente';
}

async function editarImpressora(id) {
  if (!_isAutenticado) { exigirAuth(() => editarImpressora(id)); return; }
  document.getElementById('modalBackdrop').classList.remove('hidden');
  try {
    const res = await fetch(`/gerenciar/impressoras/${id}`);
    if (!res.ok) throw new Error('Não encontrada');
    const imp = await res.json();
    document.getElementById('formId').value      = imp.id;
    document.getElementById('fNome').value       = imp.nome || '';
    document.getElementById('fIp').value         = imp.ip || '';
    document.getElementById('fModelo').value     = imp.modelo || '';
    document.getElementById('fCommunity').value  = imp.community || 'public';
    document.getElementById('fSetor').value      = imp.setor || '';
    document.getElementById('fEmpresa').value    = imp.empresa || '';
    document.getElementById('fSerial').value     = imp.serial || '';
    document.getElementById('fMac').value        = imp.mac || '';
    document.getElementById('fTipo').value       = imp.tipo || 'toner';
    _atualizarHintsTipo(imp.tipo || 'toner');
    document.getElementById('modalTitle').textContent = `✏️ Editando: ${imp.nome}`;
    tabAtual = 'form';
    document.querySelectorAll('.modal-tab').forEach((t, i) => t.classList.toggle('active', i===1));
    document.getElementById('tab-lista').classList.remove('active');
    document.getElementById('tab-form').classList.add('active');
    esconderAlerta();
  } catch(e) {
    mostrarAlerta('danger', `Erro ao carregar: ${e.message}`);
  }
}

function cancelarForm() {
  limparForm();
  mudarTab('lista');
}

async function salvarImpressora() {
  const id    = document.getElementById('formId').value;
  const dados = {
    nome:      document.getElementById('fNome').value.trim(),
    ip:        document.getElementById('fIp').value.trim(),
    modelo:    document.getElementById('fModelo').value.trim(),
    community: document.getElementById('fCommunity').value.trim() || 'public',
    setor:     document.getElementById('fSetor').value.trim(),
    empresa:   document.getElementById('fEmpresa').value.trim(),
    serial:    document.getElementById('fSerial').value.trim(),
    mac:       document.getElementById('fMac').value.trim(),
    tipo:      document.getElementById('fTipo').value || 'toner',
    ativo:     1,
  };
  const btn = document.getElementById('btnSalvar');
  btn.classList.add('loading');
  esconderAlerta();
  try {
    const url    = id ? `/gerenciar/impressoras/${id}` : '/gerenciar/impressoras';
    const method = id ? 'PUT' : 'POST';
    const res    = await fetch(url, {
      method,
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(dados),
    });
    if (res.status === 401) {
      _isAutenticado = false;
      document.getElementById('authBadge').classList.remove('visible');
      mostrarAlerta('danger', '⚠️ Sessão expirada. Faça login novamente.');
      setTimeout(() => exigirAuth(salvarImpressora), 800);
      return;
    }
    const data = await res.json();
    if (!res.ok) { mostrarAlerta('danger', data.erro || 'Erro ao salvar'); return; }
    mostrarAlerta('success', id ? '✅ Impressora atualizada!' : '✅ Impressora cadastrada!');
    limparForm();
    setTimeout(() => { mudarTab('lista'); carregarDados(); }, 1200);
  } catch(e) {
    mostrarAlerta('danger', `Erro: ${e.message}`);
  } finally {
    btn.classList.remove('loading');
  }
}

// ─── Exclusão ─────────────────────────────────────────
function confirmarExclusao(id, nome) {
  if (!_isAutenticado) { exigirAuth(() => confirmarExclusao(id, nome)); return; }
  _idParaExcluir = id;
  document.getElementById('confirmMsg').textContent = `Remover "${nome}" permanentemente?`;
  document.getElementById('confirmModal').classList.remove('hidden');
}

function fecharConfirm() {
  _idParaExcluir = null;
  document.getElementById('confirmModal').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btnConfirmOk').addEventListener('click', async () => {
    if (!_idParaExcluir) return;
    const id = _idParaExcluir;
    fecharConfirm();
    try {
      const res  = await fetch(`/gerenciar/impressoras/${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (res.status === 401) {
        _isAutenticado = false;
        mostrarAlerta('danger', '⚠️ Sessão expirada. Faça login novamente.');
        return;
      }
      if (res.ok) { mostrarAlerta('success', '✅ Impressora removida!'); carregarLista(); carregarDados(); }
      else         mostrarAlerta('danger', data.erro || 'Erro ao excluir');
    } catch(e) {
      mostrarAlerta('danger', `Erro: ${e.message}`);
    }
  });

  const fTipo = document.getElementById('fTipo');
  if (fTipo) fTipo.addEventListener('change', e => _atualizarHintsTipo(e.target.value));
});

// ─── Alertas do modal ─────────────────────────────────
function mostrarAlerta(tipo, msg) {
  const el = document.getElementById('modalAlert');
  el.className = `alert alert-${tipo}`;
  document.getElementById('modalAlertMsg').textContent = msg;
  el.classList.remove('hidden');
  if (tipo === 'success') setTimeout(esconderAlerta, 3000);
}

function esconderAlerta() {
  document.getElementById('modalAlert').classList.add('hidden');
}
