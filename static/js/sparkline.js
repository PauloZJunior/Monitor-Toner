// sparkline.js — Mini gráficos de histórico nos cards

function desenharSparklines() {
  todosOsDados.forEach(d => {
    if (!d.sparkline || d.sparkline.length < 2 || !d.id) return;
    const canvas = document.getElementById('sp_' + d.id);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w   = canvas.offsetWidth || 280;
    const h   = 32;
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const data  = d.sparkline;
    const stepX = w / (data.length - 1);
    const cor   = d.cor_status === 'critico' ? '#ff2d55' :
                  d.cor_status === 'baixo'   ? '#ff8c00' :
                  d.cor_status === 'medio'   ? '#f0c040' : '#00c87a';

    // Linha
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = i * stepX;
      const y = h - (v / 100) * h;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = cor;
    ctx.lineWidth   = 1.5;
    ctx.stroke();

    // Área preenchida
    ctx.lineTo((data.length - 1) * stepX, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, cor + '55');
    grad.addColorStop(1, cor + '00');
    ctx.fillStyle = grad;
    ctx.fill();
  });
}
