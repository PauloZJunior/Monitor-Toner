// state.js — Estado global da aplicação
let todosOsDados  = [];
let filtroStatus  = 'todos';
let filtroEmpresa = null;
let filtroTipo    = null;
let countdown     = 300;
let countdownTimer;
let tabAtual      = 'lista';
let _isAutenticado = false;
let _authCallback  = null;
let _histImpId = null, _histDias = 7, _histChart = null;
let _idParaExcluir = null;

const STATUS_LABEL = {
  ok:       'Normal',
  medio:    'Médio',
  baixo:    'Baixo',
  critico:  'Crítico',
  offline:  'Offline',
  sem_dados:'Sem dados'
};

// Sanitização XSS — escapa HTML em dados vindos do servidor
function esc(str) {
  if (!str && str !== 0) return '';
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}
