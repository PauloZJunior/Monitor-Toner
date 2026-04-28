// filters.js — Filtros e busca

function filtrarStatus(v)  { filtroStatus  = v;       renderizar(); }
function filtrarEmpresa(v) { filtroEmpresa = v || null; renderizar(); }
function filtrarTipo(v)    { filtroTipo    = v || null; renderizar(); }

function popularEmpresas(dados) {
  const empresas = [...new Set(dados.map(d => d.empresa).filter(Boolean))].sort();
  const sel = document.getElementById('selEmpresa');
  const atual = sel.value;
  sel.innerHTML = '<option value="">Todas</option>' +
    empresas.map(e => `<option value="${e}" ${atual===e?'selected':''}>${e}</option>`).join('');
}
