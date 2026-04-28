// historico.js — Modal de histórico de toner com gráfico

function abrirHistorico(id, nome) {
  _histImpId = id;
  _histDias  = 7;
  document.getElementById('histTitle').textContent = `📊 ${nome}`;
  document.getElementById('histModalBackdrop').classList.remove('hidden');
  document.querySelectorAll('.dias-btn').forEach((b, i) => b.classList.toggle('active', i===0));
  carregarHistorico();
}

function fecharHistorico() {
  document.getElementById('histModalBackdrop').classList.add('hidden');
  if (_histChart) { _histChart.destroy(); _histChart = null; }
}

function mudarDias(dias, btn) {
  _histDias = dias;
  document.querySelectorAll('.dias-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  carregarHistorico();
}

async function carregarHistorico() {
  try {
    const res  = await fetch(`/historico/impressoras/${_histImpId}?dias=${_histDias}`);
    const data = await res.json();
    const leituras = (data.leituras || []).filter(l => l.percentual !== null).reverse();

    document.getElementById('histEmpty').classList.toggle('hidden', leituras.length > 1);

    if (leituras.length > 0) {
      const vals = leituras.map(l => l.percentual);
      document.getElementById('hStatAtual').textContent    = vals[vals.length-1] + '%';
      document.getElementById('hStatMin').textContent      = Math.min(...vals) + '%';
      document.getElementById('hStatMedio').textContent    = Math.round(vals.reduce((a,b) => a+b, 0) / vals.length) + '%';
      document.getElementById('hStatPrevisao').textContent = data.previsao_dias ? `~${data.previsao_dias} dias` : '—';
    }

    if (leituras.length < 2) return;

    const labels = leituras.map(l => {
      const d = new Date(l.registrado_em.replace(' ', 'T'));
      return d.toLocaleDateString('pt-BR', {day:'2-digit', month:'2-digit'}) + ' ' +
             d.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
    });

    const isDark   = document.documentElement.getAttribute('data-theme') === 'dark';
    const gridCol  = isDark ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.08)';
    const textCol  = isDark ? '#6b7f94' : '#4a6080';

    if (_histChart) _histChart.destroy();

    _histChart = new Chart(document.getElementById('histChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Toner (%)',
          data:  leituras.map(l => l.percentual),
          borderColor:     '#0080ff',
          backgroundColor: 'rgba(0,128,255,.1)',
          borderWidth: 2,
          pointRadius: leituras.length > 50 ? 0 : 3,
          fill: true,
          tension: 0.3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min:0, max:100, grid:{color:gridCol}, ticks:{color:textCol, callback:v=>v+'%'} },
          x: { grid:{color:gridCol}, ticks:{color:textCol, maxTicksLimit:8, maxRotation:30} }
        },
        plugins: {
          legend: {display:false},
          tooltip: {callbacks:{label:ctx=>ctx.parsed.y+'%'}}
        }
      }
    });
  } catch(e) {
    console.error('Erro ao carregar histórico:', e);
  }
}
