// render.js — Renderização de cards

function renderizar() {
  const busca = document.getElementById('searchBox').value.toLowerCase();
  const dados = todosOsDados.filter(d => {
    const mS = filtroStatus==='todos' ? true :
               filtroStatus==='offline' ? d.status==='offline' :
               filtroStatus==='ok' ? d.cor_status==='ok' :
               d.cor_status===filtroStatus;
    const mE = !filtroEmpresa || d.empresa===filtroEmpresa;
    const mT = !filtroTipo    || d.tipo===filtroTipo;
    const mB = !busca ||
      [d.nome,d.ip,d.setor,d.modelo,d.empresa,d.serial,d.mac,d.tipo]
        .some(v => (v||'').toLowerCase().includes(busca));
    return mS && mE && mT && mB;
  });

  const grid = document.getElementById('grid');
  grid.innerHTML = dados.length
    ? dados.map(criarCard).join('')
    : '<div class="empty-state">Nenhuma impressora encontrada.</div>';
  setTimeout(desenharSparklines, 80);
}

function criarCard(d) {
  const st  = d.cor_status || 'offline';
  const lbl = STATUS_LABEL[st] || st;
  const isEtiqueta = d.tipo === 'etiqueta';

  // Toner / tinta / etiqueta
  let tonerHtml;
  if (isEtiqueta) {
    tonerHtml = `<div class="toner-nd" style="background:var(--accent-dim);border-color:var(--accent)">
      <svg viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.5" width="15" height="15">
        <rect x="2" y="6" width="20" height="12" rx="2"/>
        <path d="M6 10h.01M6 14h.01M10 10h8M10 14h5"/>
      </svg>
      <div class="toner-nd-text" style="color:var(--accent)">
        <strong style="color:var(--accent)">Impressora de Etiqueta</strong><br>
        <span style="opacity:.8">Monitorando apenas conectividade</span>
      </div>
    </div>`;
  } else if (d.tintas && d.tintas.length > 0) {
    tonerHtml = `<div class="ink-section"><div class="ink-title">Nível de Tinta</div>` +
      d.tintas.map(t => `<div class="ink-row">
        <span class="ink-label">${t.label}</span>
        <div class="ink-track"><div class="ink-fill" style="width:${t.pct}%;background:${t.hex}"></div></div>
        <span class="ink-pct ${t.pct<=10?'low':t.pct<=25?'warn':''}">${t.pct}%</span>
      </div>`).join('') + `</div>`;
  } else if (d.percentual !== null && d.percentual !== undefined) {
    const cls = `p-${st==='sem_dados'?'ok':st}`;
    tonerHtml = `<div class="toner-section">
      <div class="toner-label">
        <span class="toner-title">Nível de Toner</span>
        <span class="toner-pct ${cls}">${d.percentual}%</span>
      </div>
      <div class="bar-track"><div class="bar-fill ${cls}" style="width:${d.percentual}%"></div></div>
    </div>`;
  } else if (d.status==='online' && d.cor_status==='sem_dados') {
    tonerHtml = `<div class="toner-nd">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="15" height="15">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <div class="toner-nd-text"><strong>Nível não disponível</strong><br>Modelo não reporta via SNMP</div>
    </div>`;
  } else {
    tonerHtml = `<div class="toner-offline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="15" height="15">
        <circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/>
      </svg>
      ${d.status==='offline'?'Impressora offline':'Dados SNMP indisponíveis'}
    </div>`;
  }

  const sparklineHtml = d.sparkline && d.sparkline.length > 1 ? `
    <div class="sparkline-wrap">
      <div class="sparkline-lbl"><span>Histórico</span><span>${d.sparkline.length} leituras</span></div>
      <canvas class="sparkline" id="sp_${d.id}" width="280" height="32"
        onclick="abrirHistorico(${d.id},'${(d.nome||'').replace(/'/g,"\\'")}','${(d.modelo||'').replace(/'/g,"\\'")}')"
        style="cursor:pointer" title="Clique para ver histórico completo"></canvas>
    </div>` : '';

  const tempoHtml = d.tempo_resposta !== null && d.tempo_resposta !== undefined ? `
    <div class="resp-time ${d.tempo_resposta<200?'fast':d.tempo_resposta<800?'slow':'vslow'}">
      ⏱ ${d.tempo_resposta} ms
    </div>` : '';

  return `<div class="card ${st}">
    <div class="card-header">
      <div class="card-title">
        <div class="card-name">${esc(d.nome)}</div>
        ${d.empresa?`<div class="card-empresa">🏢 ${esc(d.empresa)}</div>`:''}
        <div class="card-ip">${esc(d.ip)}</div>
      </div>
      <div class="card-header-right">
        ${isEtiqueta?'<span class="badge" style="background:var(--accent-dim);color:var(--accent);margin-bottom:.2rem">🏷️ Etiqueta</span>':''}
        <span class="badge badge-${st}">${lbl}</span>
        ${d.id?`<div class="card-actions">
          <button class="card-btn edit" onclick="editarImpressora(${d.id})" title="Editar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="card-btn del" onclick="confirmarExclusao(${d.id},'${(d.nome||'').replace(/'/g,"\\'")}')" title="Excluir">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
              <path d="M10 11v6M14 11v6"/>
            </svg>
          </button>
        </div>`:''}
      </div>
    </div>
    ${tonerHtml}
    ${sparklineHtml}
    ${tempoHtml}
    <div class="card-meta">
      <div class="meta-item">
        <span class="meta-lbl">Nº Série</span>
        <span class="meta-val ${d.serial?'':'empty'}">${d.serial||'—'}</span>
      </div>
      <div class="meta-item">
        <span class="meta-lbl">MAC</span>
        <span class="meta-val ${d.mac?'':'empty'}">${d.mac||'—'}</span>
      </div>
    </div>
    <div class="card-footer">
      <span class="card-model">${d.modelo||'—'}</span>
      ${d.setor?`<span class="card-setor">${esc(d.setor)}</span>`:''}
    </div>
  </div>`;
}
