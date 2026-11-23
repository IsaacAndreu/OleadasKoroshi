/* Mapa NAU-2 · prototipo v1 (23/11/2026). Solo visor: la geometría sale de datos.json.
 *
 * Tres niveles: nave (una celda por posición, en metros) → lineal en alzado (posiciones × C1–C4) → hueco
 * (contenedores: DATOS DE EJEMPLO). Una medida cada vez con escala de color que filtra; encima, solo
 * contornos (límite de zona) y flechas (ejemplo). Antes/después con zoom sincronizado y botón de diferencia.
 */
'use strict';

// ------------------------------------------------------------------------------------------------ medidas
const COL_ZONA = { '0': '#2563eb', 'Z': '#ea580c', 'M': '#7c3aed', 'vacía': '#d4d8de' };
const COL_PLAN = {
  '0': '#2563eb', '0 libre': '#bfdbfe', 'Z': '#ea580c', 'Z libre': '#fed7aa',
  'libre': '#86d99b', 'muelle': '#ca8a04', 'muelle vacío': '#fef3c7', 'sin dato': '#ffffff',
};
const NOM_ZONA = { '0': 'Zona 0 (I27+V27)', 'Z': 'Zona Z (outlet)', 'M': 'Mezclada', 'vacía': 'Vacía hoy' };
const NOM_PLAN = {
  '0': 'Zona 0', '0 libre': 'Zona 0, vacía hoy', 'Z': 'Zona Z', 'Z libre': 'Zona Z, vacía hoy',
  'libre': 'Libre', 'muelle': 'Muelle', 'muelle vacío': 'Muelle, vacío hoy', 'sin dato': 'Sin dato',
};
// Escala secuencial (claro = poco, oscuro = mucho); se lee igual en pantalla y en PNG.
const SECUENCIAL = ['#f3e27a', '#a8d98f', '#4fb3b8', '#2b7fb8', '#253494', '#0b1a4d'];

const pct = v => (v == null ? '—' : (v * 100).toFixed(0) + ' %');
const ent = v => (v == null ? '—' : Math.round(v).toLocaleString('es-ES'));
const dec = v => (v == null ? '—' : v.toLocaleString('es-ES', { maximumFractionDigits: 1 }));

const MEDIDAS = [
  { id: 'zona', nombre: 'Zona hoy · por posición', tipo: 'cat', orden: ['0', 'Z', 'M', 'vacía'],
    colores: COL_ZONA, nombres: NOM_ZONA, valor: p => p.zona },
  { id: 'plan', nombre: 'Zona en el plan Z5+01 · por posición', tipo: 'cat',
    orden: ['0', '0 libre', 'Z', 'Z libre', 'libre', 'muelle', 'muelle vacío'],
    colores: COL_PLAN, nombres: NOM_PLAN, valor: p => p.plan },
  { id: 'pct_ocupacion', nombre: '% posiciones ocupadas · por lineal', tipo: 'num', fmt: pct },
  { id: 'uds', nombre: 'Unidades · por lineal', tipo: 'num', fmt: ent },
  { id: 'pct_z', nombre: '% unidades de zona Z · por lineal', tipo: 'num', fmt: pct },
  { id: 'pct_0', nombre: '% unidades de zona 0 · por lineal', tipo: 'num', fmt: pct },
  { id: 'uds_por_pos_ocupada', nombre: 'Uds por posición ocupada · por lineal (calculado)', tipo: 'num', fmt: dec },
  { id: 'sku', nombre: 'SKU distintos · por lineal', tipo: 'num', fmt: ent },
  { id: 'modelos_color', nombre: 'Modelos-color distintos · por lineal', tipo: 'num', fmt: ent },
  { id: 'litros', nombre: 'Litros estimados · por lineal', tipo: 'num', fmt: ent },
  { id: 'mover_p2', nombre: 'Uds a mover con la propuesta 2 · por lineal', tipo: 'num', fmt: ent },
];

// ------------------------------------------------------------------------------------------------ estado
const E = {
  datos: null,
  medida: MEDIDAS[0],
  contorno: false,
  flechas: false,
  comparar: false,
  diferencia: false,
  resaltar: null,        // Set de índices de posición, o null
  resaltarEjemplo: false,
  vista: 'nave',         // 'nave' | 'lineal'
  lineal: null,
  hueco: null,           // {p, nivel}
};
let POS = [];             // posiciones de datos.json, con índice
let IDX = new Map();      // 'L03|5' -> índice
let LIN = {};             // datos por lineal
let EXT = null;           // extensión de la nave en metros
let nave, alzado;

const $ = s => document.querySelector(s);

// ------------------------------------------------------------------------------------------------ carga
fetch('datos.json', { cache: 'no-store' })
  .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  .then(iniciar)
  .catch(e => { $('#estado').textContent = 'No se ha podido leer datos.json: ' + e.message +
    '. Arranca el servidor local (README.md) y ejecuta antes extraer_datos.py.'; });

function iniciar(d) {
  E.datos = d;
  POS = d.posiciones.map((p, i) => Object.assign({ i }, p));
  POS.forEach(p => IDX.set(p.l + '|' + p.p, p.i));
  LIN = d.lineales;
  EXT = {
    x0: Math.min(d.geometria.base[0] - 6, ...POS.map(p => p.x0)) - 1,
    x1: Math.max(...POS.map(p => p.x1)) + 1,
    y0: -3, y1: Math.max(...POS.map(p => p.y1)) + 3,
  };
  precalcularContornos();

  const sel = $('#medida');
  MEDIDAS.forEach((m, k) => sel.add(new Option(m.nombre, k)));
  sel.onchange = () => { E.medida = MEDIDAS[+sel.value]; pintar(); };

  nave = echarts.init($('#nave'), null, { renderer: 'canvas' });
  alzado = echarts.init($('#alzado'), null, { renderer: 'canvas' });
  nave.on('click', clicNave);
  alzado.on('click', clicAlzado);
  // El plano se reajusta si cambia la ventana o la barra de arriba pasa a dos líneas.
  new ResizeObserver(() => { nave.resize(); alzado.resize(); pintar(); }).observe($('#zona'));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') subir(); });

  conmutador('#b-contorno', 'contorno');
  conmutador('#b-flechas', 'flechas');
  conmutador('#b-comparar', 'comparar', () => {
    $('#b-diferencia').disabled = !E.comparar;
    if (!E.comparar) { E.diferencia = false; $('#b-diferencia').setAttribute('aria-pressed', 'false'); }
    sel.disabled = E.comparar;
  });
  conmutador('#b-diferencia', 'diferencia');
  $('#buscar').addEventListener('input', buscar);
  $('#b-ajustar').onclick = () => { if (E.vista !== 'nave') irANave(); encuadrar(null); };
  $('#b-png').onclick = guardarPNG;

  $('#estado').textContent = `Datos reales: ${d.fuente} — ${d.fecha_datos}. ${POS.length} posiciones. ` +
    'Rueda = zoom, arrastrar = mover, clic en un lineal = alzado, Esc = volver.';
  migas();
  pintar();
}

function conmutador(sel, clave, despues) {
  $(sel).onclick = () => {
    E[clave] = !E[clave];
    $(sel).setAttribute('aria-pressed', String(E[clave]));
    if (despues) despues();
    pintar(clave === 'comparar');
  };
}

// ------------------------------------------------------------------------------------------------ valores
function valorNum(p, m) {
  const l = LIN[p.l];
  return l ? l[m.id] : null;
}

/** Categoría para la diferencia hoy → plan. */
function normPlan(c) {
  if (c === '0' || c === '0 libre') return '0';
  if (c === 'Z' || c === 'Z libre') return 'Z';
  if (c === 'muelle' || c === 'muelle vacío') return 'muelle';
  return c;
}
function transicion(p) {
  const a = p.zona, b = normPlan(p.plan);
  if (a === b || (a === 'vacía' && b === 'libre')) return 'igual';
  return a + ' → ' + b;
}
let CATS_DIF = null;
function catsDiferencia() {
  if (CATS_DIF) return CATS_DIF;
  const n = {};
  POS.forEach(p => { const t = transicion(p); n[t] = (n[t] || 0) + 1; });
  const orden = Object.keys(n).sort((a, b) => (a === 'igual') - (b === 'igual') || n[b] - n[a]);
  const paleta = ['#16a34a', '#2563eb', '#ea580c', '#9333ea', '#ca8a04', '#0891b2', '#db2777', '#65a30d', '#475569'];
  CATS_DIF = orden.map((t, k) => ({ t, n: n[t], color: t === 'igual' ? '#e5e7eb' : paleta[k % paleta.length] }));
  return CATS_DIF;
}

// ------------------------------------------------------------------------------------------------ geometría de la pantalla
const MARGEN = { titulo: 24, leyenda: 40, lado: 10, entre: 18 };

/** Rectángulos de los planos. Con antes/después se ponen lado a lado o uno encima del otro, lo que deje
 *  más píxeles por metro (la nave es más ancha que alta: en un portátil suele ganar uno encima del otro). */
function rectangulos() {
  const W = nave.getWidth(), H = nave.getHeight();
  const bloque = (left, top, w, h) => ({ left, top: top + MARGEN.titulo, width: w,
    height: h - MARGEN.titulo - MARGEN.leyenda });
  if (!E.comparar) return [bloque(MARGEN.lado, 0, W - 2 * MARGEN.lado, H)];
  const dx = EXT.x1 - EXT.x0, dy = EXT.y1 - EXT.y0;
  const escala = r => Math.min(r.width / dx, r.height / dy);
  const anchoLado = (W - 2 * MARGEN.lado - MARGEN.entre) / 2;
  const ladoALado = [bloque(MARGEN.lado, 0, anchoLado, H),
    bloque(MARGEN.lado + anchoLado + MARGEN.entre, 0, anchoLado, H)];
  const altoMitad = H / 2;
  const encima = [bloque(MARGEN.lado, 0, W - 2 * MARGEN.lado, altoMitad),
    bloque(MARGEN.lado, altoMitad, W - 2 * MARGEN.lado, altoMitad)];
  return escala(encima[0]) > escala(ladoALado[0]) ? encima : ladoALado;
}

/** Rango de ejes con la misma escala en x y en y (1 m = 1 m), centrado en la nave. */
function ejesIguales(r) {
  const dx = EXT.x1 - EXT.x0, dy = EXT.y1 - EXT.y0;
  const s = Math.min(r.width / dx, r.height / dy);
  const ax = r.width / s, ay = r.height / s;
  const cx = (EXT.x0 + EXT.x1) / 2, cy = (EXT.y0 + EXT.y1) / 2;
  return { x: [cx - ax / 2, cx + ax / 2], y: [cy - ay / 2, cy + ay / 2] };
}

// ------------------------------------------------------------------------------------------------ series de la nave
function datosCeldas(lado) {
  // lado: 'hoy' | 'plan' | 'dif'
  const m = E.medida;
  return POS.map(p => {
    let v;
    if (lado === 'plan') v = MEDIDAS[1].orden.indexOf(p.plan);
    else if (lado === 'dif') v = catsDiferencia().findIndex(c => c.t === transicion(p));
    else if (E.comparar || m.tipo === 'cat') {
      const mm = E.comparar ? MEDIDAS[0] : m;
      v = mm.orden.indexOf(mm.valor(p));
    } else {
      v = valorNum(p, m);
      if (v == null) v = '-';
    }
    return [p.x0, p.x1, p.y0, p.y1, v, p.i];
  });
}

function renderCelda(lado) {
  return function (params, api) {
    const a = api.coord([api.value(0), api.value(3)]);
    const b = api.coord([api.value(1), api.value(2)]);
    const i = api.value(5);
    const p = POS[i];
    const sinDato = isNaN(api.value(4));
    let opacidad = 1;
    if (E.resaltar && !E.resaltar.has(i)) opacidad = 0.12;
    if (E.diferencia && lado === 'hoy' && transicion(p) === 'igual') opacidad = Math.min(opacidad, 0.15);
    const w = Math.max(b[0] - a[0], 0.6), h = Math.max(b[1] - a[1], 0.6);
    const resaltada = E.resaltar && E.resaltar.has(i);
    return {
      type: 'rect',
      shape: { x: a[0], y: a[1], width: w, height: h },
      style: {
        fill: sinDato ? '#ffffff' : api.visual('color'),
        opacity: opacidad * (api.visual('opacity') ?? 1),
        stroke: resaltada ? '#111827' : (sinDato ? '#c4cad2' : null),
        lineWidth: resaltada ? 1.5 : 0.5,
      },
    };
  };
}

function seriePasillos(g) {
  // Pasillo central y transversales (CRUCES) y el contorno de la nave. Solo de fondo.
  const d = E.datos.geometria;
  const xs = POS.filter(p => !p.muelle);
  const x0 = Math.min(...xs.map(p => p.x0)) - 0.6, x1 = Math.max(...xs.map(p => p.x1)) + 0.6;
  const yTop = Math.max(...xs.map(p => p.y1)) + 0.6;
  // Ancho de cada transversal: del final de la posición de antes al principio de la de después.
  const bandas = [
    { y0: 6.5, y1: 9.0, t: 'Transversal 7,75 m' },
    { y0: 29.0, y1: 31.0, t: 'Pasillo central 30 m' },
    { y0: 43.0, y1: 45.5, t: 'Transversal 44,25 m' },
  ];
  return [{
    type: 'custom', xAxisIndex: g, yAxisIndex: g, silent: true, z: 0, clip: true,
    data: [0],
    renderItem: (params, api) => {
      const hijos = [];
      const n0 = api.coord([x0, yTop]), n1 = api.coord([x1, -0.6]);
      hijos.push({ type: 'rect', shape: { x: n0[0], y: n0[1], width: n1[0] - n0[0], height: n1[1] - n0[1] },
        style: { fill: '#fbfbfc', stroke: '#9aa3ae', lineWidth: 1 } });
      bandas.forEach(b => {
        const a = api.coord([x0, b.y1]), c = api.coord([x1, b.y0]);
        hijos.push({ type: 'rect', shape: { x: a[0], y: a[1], width: c[0] - a[0], height: c[1] - a[1] },
          style: { fill: '#eef1f5' } });
        hijos.push({ type: 'text', x: c[0] - 4, y: (a[1] + c[1]) / 2,
          style: { text: b.t, fill: '#8a94a1', font: '11px system-ui', align: 'right', verticalAlign: 'middle' } });
      });
      // Muelle: aparte (sin geometría en kpi.py)
      const mu = POS.filter(p => p.muelle);
      if (mu.length) {
        const m0 = api.coord([Math.min(...mu.map(p => p.x0)) - 0.6, Math.max(...mu.map(p => p.y1)) + 0.6]);
        const m1 = api.coord([Math.max(...mu.map(p => p.x1)) + 0.6, Math.min(...mu.map(p => p.y0)) - 0.6]);
        hijos.push({ type: 'rect', shape: { x: m0[0], y: m0[1], width: m1[0] - m0[0], height: m1[1] - m0[1] },
          style: { fill: 'none', stroke: '#b9a26a', lineWidth: 1, lineDash: [4, 3] } });
        hijos.push({ type: 'text', x: m0[0], y: m0[1] - 4,
          style: { text: 'Muelle MU-00…14\n(sitio aproximado:\nkpi.py no lo sitúa)', fill: '#8a7440',
            font: '11px system-ui', verticalAlign: 'bottom', lineHeight: 13 } });
      }
      // Expedición (BASE)
      const bp = api.coord(d.base);
      hijos.push({ type: 'circle', shape: { cx: bp[0], cy: bp[1], r: 5 }, style: { fill: '#111827' } });
      hijos.push({ type: 'text', x: bp[0], y: bp[1] + 8,
        style: { text: 'Expedición', fill: '#111827', font: '600 11px system-ui', align: 'center', verticalAlign: 'top' } });
      return { type: 'group', children: hijos };
    },
  }];
}

function serieEtiquetas(g) {
  // Nombre de lineal abajo y arriba; se espacian según el zoom para que no se pisen.
  const lineales = {};
  POS.forEach(p => { if (!p.muelle) (lineales[p.l] = lineales[p.l] || []).push(p); });
  const nav = POS.filter(p => !p.muelle);
  const yTope = Math.max(...nav.map(p => p.y1)) + 0.6;
  const xIzq = Math.min(...nav.map(p => p.x0)) - 0.8;
  const datos = Object.keys(lineales).map(l => {
    const ps = lineales[l];
    return [(ps[0].x0 + ps[0].x1) / 2, yTope, parseInt(l.slice(1), 10)];
  });
  const pos = [[1, 'P01'], [4, 'P04'], [17, 'P17'], [18, 'P18'], [24, 'P24'], [25, 'P25'], [36, 'P36'], [42, 'P42']]
    .filter(([n]) => POS.some(q => q.p === n && !q.muelle));
  return [{
    type: 'custom', xAxisIndex: g, yAxisIndex: g, silent: true, z: 3, clip: false,
    data: datos,
    renderItem: (params, api) => {
      const pxPorLineal = Math.abs(api.size([2, 0])[0]) / 2;
      const n = api.value(2);
      const cada = pxPorLineal > 22 ? 1 : pxPorLineal > 9 ? 5 : 10;
      if (n !== 1 && n % cada) return null;
      const abajo = api.coord([api.value(0), -0.7]);
      const arriba = api.coord([api.value(0), api.value(1) + 0.4]);
      const t = 'L' + String(n).padStart(2, '0');
      const estilo = { text: t, fill: '#4b5563', font: '10px system-ui', align: 'center' };
      return { type: 'group', children: [
        { type: 'text', x: abajo[0], y: abajo[1], style: Object.assign({ verticalAlign: 'top' }, estilo) },
        { type: 'text', x: arriba[0], y: arriba[1], style: Object.assign({ verticalAlign: 'bottom' }, estilo) },
      ] };
    },
  }, {
    type: 'custom', xAxisIndex: g, yAxisIndex: g, silent: true, z: 3, clip: true,
    data: pos.map(([n, t]) => {
      const p = POS.find(q => q.p === n && !q.muelle);
      return p ? [xIzq, (p.y0 + p.y1) / 2, t] : null;
    }).filter(Boolean),
    renderItem: (params, api) => {
      const c = api.coord([api.value(0), api.value(1)]);
      return { type: 'text', x: c[0], y: c[1],
        style: { text: E.datos ? pos[params.dataIndex][1] : '', fill: '#6b7280', font: '10px system-ui',
          align: 'right', verticalAlign: 'middle' } };
    },
  }];
}

// Contornos: líneas entre posiciones que se tocan y son de zona distinta (0 frente a Z).
let CONTORNOS = { hoy: [], plan: [] };
function precalcularContornos() {
  const zonaHoy = p => (p.zona === '0' || p.zona === 'Z' ? p.zona : null);
  const zonaPlan = p => { const z = normPlan(p.plan); return z === '0' || z === 'Z' ? z : null; };
  const porLineal = {};
  POS.forEach(p => { if (!p.muelle) (porLineal[p.l] = porLineal[p.l] || []).push(p); });
  for (const [lado, f] of [['hoy', zonaHoy], ['plan', zonaPlan]]) {
    const seg = [];
    // a lo largo del lineal (posiciones seguidas, por y)
    Object.values(porLineal).forEach(ps => {
      const o = ps.slice().sort((a, b) => a.y0 - b.y0);
      for (let k = 1; k < o.length; k++) {
        const a = o[k - 1], b = o[k];
        if (b.y0 - a.y1 > 0.5) continue;
        const za = f(a), zb = f(b);
        if (za && zb && za !== zb) {
          const y = (a.y1 + b.y0) / 2;
          seg.push([[a.x0, y], [a.x1, y]]);
        }
      }
    });
    // entre lineales vecinos (Ln con Ln+1), misma posición: espalda con espalda (impar-par) o frente a frente
    // al otro lado del pasillo (par-impar). La línea va por el medio del hueco entre los dos.
    Object.keys(porLineal).forEach(l => {
      const n = parseInt(l.slice(1), 10);
      const vec = 'L' + String(n + 1).padStart(2, '0');
      porLineal[l].forEach(a => {
        const j = IDX.get(vec + '|' + a.p);
        if (j == null) return;
        const b = POS[j];
        const za = f(a), zb = f(b);
        if (za && zb && za !== zb) { const x = (a.x1 + b.x0) / 2; seg.push([[x, a.y0 - 0.05], [x, a.y1 + 0.05]]); }
      });
    });
    CONTORNOS[lado] = seg;
  }
}

function serieContorno(g, lado) {
  return {
    type: 'lines', coordinateSystem: 'cartesian2d', xAxisIndex: g, yAxisIndex: g, silent: true, z: 4,
    polyline: false, lineStyle: { color: '#111827', width: 2.2, opacity: 0.9 },
    data: CONTORNOS[lado === 'plan' ? 'plan' : 'hoy'].map(c => ({ coords: c })),
  };
}

function centro(l, p) {
  const j = IDX.get(l + '|' + p);
  if (j == null) return null;
  const q = POS[j];
  return [(q.x0 + q.x1) / 2, (q.y0 + q.y1) / 2];
}

function serieFlechas(g) {
  const fl = E.datos.ejemplo.flechas.map(f => {
    const a = centro(f.de[0], f.de[1]), b = centro(f.a[0], f.a[1]);
    return a && b ? { coords: [a, b], nombre: `${f.de[0]} P${pad(f.de[1])} → ${f.a[0]} P${pad(f.a[1])}` } : null;
  }).filter(Boolean);
  return {
    type: 'lines', coordinateSystem: 'cartesian2d', xAxisIndex: g, yAxisIndex: g, z: 5,
    symbol: ['circle', 'arrow'], symbolSize: [6, 12],
    lineStyle: { color: '#b45309', width: 2.5, curveness: 0.18, type: 'dashed' },
    tooltip: { formatter: x => `<b>DATOS DE EJEMPLO</b><br>Mover de ${x.data.nombre}<br>` +
      '<span style="color:#6b7280">No es un plan: enseña cómo se verían los movimientos.</span>' },
    label: { show: true, position: 'end', formatter: '', },
    data: fl,
  };
}

const pad = n => String(n).padStart(2, '0');

// ------------------------------------------------------------------------------------------------ pintar la nave
function mapaVisual(m, serieIdx, rect, lado) {
  // lado: 'hoy' | 'plan' | 'dif'
  const comun = { seriesIndex: serieIdx, dimension: 4, orient: 'horizontal', top: rect.top + rect.height + 10,
    left: rect.left, textStyle: { fontSize: 11, color: '#374151' } };
  if (lado === 'dif') {
    const cats = catsDiferencia();
    return Object.assign(comun, { type: 'piecewise', itemWidth: 14, itemHeight: 12, itemGap: 8,
      pieces: cats.map((c, k) => ({ value: k, label: `${c.t} (${c.n})`, color: c.color })),
      outOfRange: { color: '#dfe3e8', opacity: 0.35 } });
  }
  if (lado === 'plan' || m.tipo === 'cat') {
    const mm = lado === 'plan' ? MEDIDAS[1] : m;
    const n = {};
    POS.forEach(p => { const c = mm.valor(p); n[c] = (n[c] || 0) + 1; });
    return Object.assign(comun, { type: 'piecewise', itemWidth: 14, itemHeight: 12, itemGap: 10,
      pieces: mm.orden.map((c, k) => ({ value: k, label: `${mm.nombres[c]} (${n[c] || 0})`, color: mm.colores[c] })),
      outOfRange: { color: '#dfe3e8', opacity: 0.35 } });
  }
  const vals = Object.values(LIN).map(l => l[m.id]).filter(v => v != null);
  const min = Math.min(...vals), max = Math.max(...vals);
  return Object.assign(comun, {
    type: 'continuous', min, max, calculable: true, realtime: true, itemWidth: 12, itemHeight: 320,
    text: [m.fmt(max), m.fmt(min)], formatter: v => m.fmt(v), precision: 3,
    inRange: { color: SECUENCIAL, opacity: 1 }, outOfRange: { color: '#dfe3e8', opacity: 0.35 },
  });
}

function pintar(reencuadrar) {
  if (!E.datos) return;
  if (E.vista === 'lineal') { pintarAlzado(); return; }
  const rects = rectangulos();
  const lados = E.comparar ? ['hoy', E.diferencia ? 'dif' : 'plan'] : ['hoy'];
  const titulos = E.comparar
    ? ['Hoy (06/11) · zona por posición', E.diferencia ? 'Diferencia hoy → plan Z5+01' : 'Plan Z5+01 · zona por posición']
    : [E.medida.nombre];

  const series = [], visual = [], grid = [], xAxis = [], yAxis = [], title = [];
  rects.forEach((r, g) => {
    const ej = ejesIguales(r);
    grid.push(Object.assign({ containLabel: false }, r));
    xAxis.push({ type: 'value', gridIndex: g, min: ej.x[0], max: ej.x[1], show: false });
    yAxis.push({ type: 'value', gridIndex: g, min: ej.y[0], max: ej.y[1], show: false });
    title.push({ text: titulos[g], left: r.left, top: r.top - MARGEN.titulo + 4, textStyle: { fontSize: 12, fontWeight: 600, color: '#1f2933' } });

    series.push(...seriePasillos(g));
    const idxCeldas = series.length;
    series.push({
      type: 'custom', name: 'celdas-' + lados[g], xAxisIndex: g, yAxisIndex: g, z: 2, clip: true,
      progressive: 0, renderItem: renderCelda(lados[g]),
      encode: { x: [0, 1], y: [2, 3], tooltip: [4] },
      data: datosCeldas(lados[g]),
    });
    visual.push(mapaVisual(E.medida, idxCeldas, r, lados[g]));
    series.push(...serieEtiquetas(g));
    if (E.contorno) series.push(serieContorno(g, lados[g] === 'hoy' ? 'hoy' : 'plan'));
    if (E.flechas) series.push(serieFlechas(g));
  });

  const opcion = {
    animation: false,
    title, grid, xAxis, yAxis, series, visualMap: visual,
    tooltip: { trigger: 'item', confine: true, formatter: textoCelda, backgroundColor: 'rgba(255,255,255,.97)',
      borderColor: '#cbd2da', textStyle: { fontSize: 12, color: '#1f2933' } },
    dataZoom: [
      { type: 'inside', xAxisIndex: rects.map((r, g) => g), filterMode: 'none' },
      { type: 'inside', yAxisIndex: rects.map((r, g) => g), filterMode: 'none' },
    ],
  };
  // Al cambiar de una a dos vistas cambian grids y ejes: se rehace la opción entera pero se guarda el zoom.
  const zoomAntes = reencuadrar ? null : zoomActual();
  nave.setOption(opcion, { notMerge: true });
  if (zoomAntes) {
    nave.dispatchAction({ type: 'dataZoom', batch: [
      { dataZoomIndex: 0, start: zoomAntes[0].start, end: zoomAntes[0].end },
      { dataZoomIndex: 1, start: zoomAntes[1].start, end: zoomAntes[1].end },
    ] });
  }
  marcaEjemplo();
}

function zoomActual() {
  const o = nave.getOption();
  if (!o || !o.dataZoom || o.dataZoom.length < 2) return null;
  return o.dataZoom.map(z => ({ start: z.start, end: z.end }));
}

/** Encuadra una caja en metros (o la nave entera si es null), con la misma escala en x y en y. */
function encuadrar(caja) {
  const o = nave.getOption();
  if (!caja) {
    nave.dispatchAction({ type: 'dataZoom', batch: [
      { dataZoomIndex: 0, start: 0, end: 100 }, { dataZoomIndex: 1, start: 0, end: 100 }] });
    return;
  }
  const r = rectangulos()[0];
  const xa = o.xAxis[0], ya = o.yAxis[0];
  let w = caja.x1 - caja.x0 + 8, h = caja.y1 - caja.y0 + 8;
  const asp = r.width / r.height;
  if (w / h < asp) w = h * asp; else h = w / asp;
  const cx = (caja.x0 + caja.x1) / 2, cy = (caja.y0 + caja.y1) / 2;
  const px = v => ((v - xa.min) / (xa.max - xa.min)) * 100;
  const py = v => ((v - ya.min) / (ya.max - ya.min)) * 100;
  nave.dispatchAction({ type: 'dataZoom', batch: [
    { dataZoomIndex: 0, start: px(cx - w / 2), end: px(cx + w / 2) },
    { dataZoomIndex: 1, start: py(cy - h / 2), end: py(cy + h / 2) },
  ] });
}

// ------------------------------------------------------------------------------------------------ texto al pasar el ratón
function textoCelda(x) {
  if (!x.seriesName || !x.seriesName.startsWith('celdas')) return '';
  const p = POS[x.data[5]];
  const l = LIN[p.l] || {};
  const filas = [
    `<b>${p.l} P${pad(p.p)}</b>${p.muelle ? ' <span style="color:#8a7440">(muelle)</span>' : ''}`,
    `Zona hoy (posición): <b>${NOM_ZONA[p.zona] || p.zona}</b>`,
    `Plan Z5+01 (posición): <b>${NOM_PLAN[p.plan] || p.plan}</b>`,
  ];
  if (E.diferencia) filas.push(`Cambio: <b>${transicion(p)}</b>`);
  filas.push('<hr style="border:0;border-top:1px solid #e5e7eb;margin:4px 0">');
  filas.push(`<span style="color:#6b7280">Del lineal entero (hoja Por lineal):</span>`);
  filas.push(`Ocupadas ${ent(l.ocupadas)} de ${ent(l.posiciones)} posiciones (${pct(l.pct_ocupacion)})`);
  filas.push(`${ent(l.uds)} uds · ${pct(l.pct_0)} zona 0 · ${pct(l.pct_z)} zona Z`);
  filas.push(`${ent(l.sku)} SKU · ${ent(l.modelos_color)} modelos-color · ${ent(l.litros)} L est.`);
  if (l.temporadas) filas.push(`<span style="color:#6b7280">${l.temporadas}</span>`);
  if (E.medida.tipo === 'num' && !E.comparar) {
    filas.push(`<b>${E.medida.nombre.split(' · ')[0]}: ${E.medida.fmt(l[E.medida.id])}</b>`);
  }
  return filas.join('<br>');
}

// ------------------------------------------------------------------------------------------------ buscador
function buscar() {
  const t = $('#buscar').value.trim().toUpperCase();
  const res = $('#resultado-busqueda');
  E.resaltar = null; E.resaltarEjemplo = false; res.innerHTML = '';
  if (!t) { pintar(); return; }
  let m, set = new Set(), texto = '';
  if ((m = t.match(/^L?\s*(\d{1,3})(?:\s*[- ]\s*P?\s*(\d{1,2}))?$/))) {
    const l = 'L' + pad(parseInt(m[1], 10));
    POS.forEach(p => { if (p.l === l && (m[2] == null || p.p === parseInt(m[2], 10))) set.add(p.i); });
    texto = set.size ? `${l}${m[2] != null ? ' P' + pad(+m[2]) : ''}: ${set.size} posiciones` : `${l}: no está`;
  } else if ((m = t.match(/^MU-?(\d{1,2})$/))) {
    const l = 'MU-' + pad(+m[1]);
    POS.forEach(p => { if (p.l === l) set.add(p.i); });
    texto = `${l}: ${set.size} posiciones`;
  } else if (/^[IV]\d{2}$/.test(t)) {
    // Temporada: dato REAL pero solo por lineal (las 4 temporadas con más uds de cada lineal).
    const ls = Object.keys(LIN).filter(l => (LIN[l].temporadas || '').split(' ').some(s => s.startsWith(t + ':')));
    POS.forEach(p => { if (ls.includes(p.l)) set.add(p.i); });
    texto = `${t}: entre las 4 temporadas principales de ${ls.length} lineales (dato por lineal)`;
  } else {
    const modelos = E.datos.ejemplo.modelos;
    const k = Object.keys(modelos).find(x => x.includes(t));
    if (k) {
      modelos[k].forEach(([l, p]) => { const j = IDX.get(l + '|' + p); if (j != null) set.add(j); });
      E.resaltarEjemplo = true;
      texto = `${k}: ${set.size} posiciones <span class="marca-ejemplo">DATOS DE EJEMPLO</span>`;
    } else {
      texto = 'Sin resultados (prueba L45, L45 P05, MU-03, I16 o MODELO-EJEMPLO-A)';
    }
  }
  E.resaltar = set.size ? set : null;
  res.innerHTML = texto;
  pintar();
  if (set.size && E.vista === 'nave') {
    const ps = [...set].map(i => POS[i]);
    encuadrar({ x0: Math.min(...ps.map(p => p.x0)), x1: Math.max(...ps.map(p => p.x1)),
      y0: Math.min(...ps.map(p => p.y0)), y1: Math.max(...ps.map(p => p.y1)) });
  }
}

function marcaEjemplo() {
  const partes = [];
  if (E.flechas) partes.push('flechas');
  if (E.resaltarEjemplo) partes.push('modelo buscado');
  const base = $('#estado').dataset.base || $('#estado').textContent;
  $('#estado').dataset.base = base;
  $('#estado').innerHTML = (partes.length
    ? `<span class="marca-ejemplo">DATOS DE EJEMPLO: ${partes.join(' y ')}</span> ` : '') + base;
}

// ------------------------------------------------------------------------------------------------ niveles de zoom
function clicNave(x) {
  if (!x.seriesName || !x.seriesName.startsWith('celdas')) return;
  const p = POS[x.data[5]];
  E.vista = 'lineal'; E.lineal = p.l; E.hueco = null;
  $('#nave').classList.add('oculto');
  $('#vista-lineal').classList.remove('oculto');
  alzado.resize();
  migas();
  pintarAlzado();
  pintarHueco();
}

function irANave() {
  E.vista = 'nave'; E.lineal = null; E.hueco = null;
  $('#vista-lineal').classList.add('oculto');
  $('#nave').classList.remove('oculto');
  nave.resize();
  migas();
  pintar();
}

function subir() {
  if (E.vista === 'lineal' && E.hueco) { E.hueco = null; migas(); pintarAlzado(); pintarHueco(); }
  else if (E.vista === 'lineal') irANave();
}

function migas() {
  const n = $('#migas');
  n.innerHTML = '';
  const enlace = (t, f) => { const a = document.createElement('a'); a.textContent = t; a.onclick = f; return a; };
  const txt = t => { const s = document.createElement('span'); s.textContent = t; return s; };
  if (E.vista === 'nave') { n.append(txt('Nave')); return; }
  n.append(enlace('Nave', irANave), txt('›'));
  if (!E.hueco) { n.append(txt(`${E.lineal} en alzado`)); return; }
  n.append(enlace(`${E.lineal} en alzado`, () => { E.hueco = null; migas(); pintarAlzado(); pintarHueco(); }),
    txt('›'), txt(`P${pad(E.hueco.p)} C${E.hueco.nivel}`));
}

// ------------------------------------------------------------------------------------------------ alzado de un lineal
const NIVELES = [1, 2, 3, 4];

function pintarAlzado() {
  const ps = POS.filter(p => p.l === E.lineal).sort((a, b) => a.p - b.p);
  const usarPlan = E.medida.id === 'plan' || (E.comparar && E.diferencia);
  const izq = ps.filter(p => p.p <= 17), der = ps.filter(p => p.p >= 18);
  const tramos = [];
  if (der.length) tramos.push({ t: 'Derecha del pasillo central (P18 en adelante)', ps: der });
  if (izq.length) tramos.push({ t: 'Izquierda del pasillo central (P00–P17)', ps: izq });
  if (!tramos.length) tramos.push({ t: '', ps });

  const W = alzado.getWidth(), H = alzado.getHeight();
  const arriba = 80, abajo = 54, entre = 40;
  const alto = (H - arriba - abajo - entre * (tramos.length - 1)) / tramos.length;
  const l = LIN[E.lineal] || {};
  const grid = [], xAxis = [], yAxis = [], series = [], title = [{
    text: `${E.lineal} en alzado · ${usarPlan ? 'zona en el plan Z5+01' : 'zona hoy'} por posición`,
    subtext: `${ent(l.ocupadas)} de ${ent(l.posiciones)} posiciones ocupadas (${pct(l.pct_ocupacion)}) · ` +
      `${ent(l.ubicaciones)} ubicaciones en Odoo · ${ent(l.uds)} uds · ${ent(l.sku)} SKU · ${ent(l.modelos_color)} modelos-color` +
      `\nLos niveles C1–C4 se pintan con la zona de su posición: el Excel no trae datos por nivel.`,
    left: 12, top: 6, textStyle: { fontSize: 14 }, subtextStyle: { fontSize: 12, color: '#5f6b7a', lineHeight: 16 },
  }];
  const mm = usarPlan ? MEDIDAS[1] : MEDIDAS[0];
  tramos.forEach((tr, g) => {
    const top = arriba + g * (alto + entre) + 18;
    grid.push({ left: 44, right: 16, top, height: alto - 18 });
    xAxis.push({ type: 'category', gridIndex: g, data: tr.ps.map(p => 'P' + pad(p.p)),
      axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 11, color: '#374151' } });
    yAxis.push({ type: 'category', gridIndex: g, data: NIVELES.map(n => 'C' + n),
      axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 11, color: '#374151' } });
    title.push({ text: tr.t, left: 44, top: top - 18, textStyle: { fontSize: 12, fontWeight: 500, color: '#5f6b7a' } });
    const datos = [];
    tr.ps.forEach((p, k) => NIVELES.forEach((n, j) => {
      datos.push([k, j, mm.orden.indexOf(mm.valor(p)), p.i, n]);
    }));
    series.push({
      type: 'custom', name: 'alzado', xAxisIndex: g, yAxisIndex: g, data: datos, encode: { x: 0, y: 1 },
      renderItem: (params, api) => {
        const c = api.coord([api.value(0), api.value(1)]);
        const s = api.size([1, 1]);
        const p = POS[api.value(3)], n = api.value(4);
        const sel = E.hueco && E.hueco.p === p.p && E.hueco.nivel === n;
        const busc = E.resaltar && !E.resaltar.has(p.i);
        const color = api.visual('color');
        const oscuro = ['0', 'Z', 'M', 'muelle'].includes(usarPlan ? p.plan : p.zona);
        return { type: 'group', children: [
          { type: 'rect', shape: { x: c[0] - s[0] / 2 + 1.5, y: c[1] - s[1] / 2 + 1.5, width: s[0] - 3, height: s[1] - 3, r: 2 },
            style: { fill: color, opacity: busc ? 0.2 : 1, stroke: sel ? '#111827' : null, lineWidth: sel ? 3 : 0 } },
          s[0] > 34 ? { type: 'text', x: c[0], y: c[1], silent: true,
            style: { text: `P${pad(p.p)} C${n}`, align: 'center', verticalAlign: 'middle',
              font: '10px system-ui', fill: oscuro ? '#ffffff' : '#374151', opacity: busc ? 0.3 : 1 } } : null,
        ].filter(Boolean) };
      },
    });
  });
  const n = {};
  ps.forEach(p => { const c = mm.valor(p); n[c] = (n[c] || 0) + 1; });
  alzado.setOption({
    animation: false, title, grid, xAxis, yAxis, series,
    visualMap: [{ type: 'piecewise', seriesIndex: series.map((s, k) => k), dimension: 2, orient: 'horizontal',
      left: 44, bottom: 10, itemWidth: 14, itemHeight: 12, textStyle: { fontSize: 11 },
      pieces: mm.orden.map((c, k) => ({ value: k, label: `${mm.nombres[c]} (${n[c] || 0} pos.)`, color: mm.colores[c] })) }],
    tooltip: { trigger: 'item', confine: true, formatter: x => {
      const p = POS[x.data[3]];
      return `<b>${p.l} P${pad(p.p)} C${x.data[4]}</b><br>Zona hoy (posición): ${NOM_ZONA[p.zona] || p.zona}` +
        `<br>Plan Z5+01 (posición): ${NOM_PLAN[p.plan] || p.plan}` +
        '<br><span style="color:#6b7280">Nivel sin datos propios. Clic = contenedores (ejemplo)</span>';
    } },
  }, { notMerge: true });
}

function clicAlzado(x) {
  if (x.seriesName !== 'alzado') return;
  const p = POS[x.data[3]];
  E.hueco = { p: p.p, nivel: x.data[4], i: p.i };
  migas();
  pintarAlzado();
  pintarHueco();
}

// ------------------------------------------------------------------------------------------------ hueco (contenedores: ejemplo)
function pintarHueco() {
  const caja = $('#hueco');
  if (!E.hueco) {
    caja.innerHTML = `<h2>${E.lineal}</h2>
      <p class="suave">Toca un hueco del alzado para ver qué hay dentro.</p>
      <div class="caja-real"><b>Datos reales del lineal</b> (hoja Por lineal)<br>${resumenLineal(E.lineal)}</div>`;
    return;
  }
  const p = POS[E.hueco.i];
  const ej = E.datos.ejemplo;
  const filas = ej.contenedores_hueco.map(c =>
    `<tr><td>${c.nombre}</td><td>${c.modelo}</td><td>${c.color}</td><td>${c.tallas}</td><td class="num">${c.uds}</td></tr>`).join('');
  const total = ej.contenedores_hueco.reduce((s, c) => s + c.uds, 0);
  caja.innerHTML = `
    <h2>${p.l} P${pad(p.p)} C${E.hueco.nivel}</h2>
    <div class="caja-real">
      <b>Real</b> (por posición, no por nivel)<br>
      Zona hoy: <b>${NOM_ZONA[p.zona] || p.zona}</b><br>
      Plan Z5+01: <b>${NOM_PLAN[p.plan] || p.plan}</b>
    </div>
    <div class="caja-ejemplo">
      <span class="marca-ejemplo">DATOS DE EJEMPLO</span>
      <p style="margin:6px 0 0">No es el contenido de este hueco: el Excel no trae contenedores. Enseña cómo se vería.</p>
      <table>
        <thead><tr><th>Contenedor</th><th>Modelo</th><th>Color</th><th>Tallas</th><th class="num">Uds</th></tr></thead>
        <tbody>${filas}</tbody>
        <tfoot><tr><th colspan="4">Total</th><th class="num">${total}</th></tr></tfoot>
      </table>
    </div>
    <p class="suave" style="margin-top:12px">Para que esto sea real hace falta de Odoo: <code>stock.quant</code>
    (ubicación, producto, paquete, cantidad) de las ubicaciones del lineal, con <code>stock.quant.package</code>
    para el nombre del contenedor y <code>product.product</code> para modelo, color y talla.</p>`;
}

function resumenLineal(l) {
  const d = LIN[l];
  if (!d) return 'Sin fila en la hoja Por lineal.';
  return `Zona del lineal: <b>${d.zona || '—'}</b><br>
    ${ent(d.ocupadas)} de ${ent(d.posiciones)} posiciones ocupadas (${pct(d.pct_ocupacion)})<br>
    ${ent(d.ubicaciones)} ubicaciones en Odoo<br>
    ${ent(d.uds)} uds: ${ent(d.uds_0)} de zona 0, ${ent(d.uds_z)} de Z, ${ent(d.uds_otras)} otras<br>
    ${ent(d.sku)} SKU · ${ent(d.modelos_color)} modelos-color · ${ent(d.litros)} L estimados<br>
    Temporadas principales: ${d.temporadas || '—'}`;
}

// ------------------------------------------------------------------------------------------------ PNG
function guardarPNG() {
  const graf = E.vista === 'nave' ? nave : alzado;
  const url = graf.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' });
  const a = document.createElement('a');
  const hoy = new Date();
  const f = `${hoy.getFullYear()}${pad(hoy.getMonth() + 1)}${pad(hoy.getDate())}_${pad(hoy.getHours())}${pad(hoy.getMinutes())}`;
  a.href = url;
  a.download = `mapa-nau2_${E.vista === 'nave' ? (E.comparar ? 'antes-despues' : E.medida.id) : E.lineal}_${f}.png`;
  a.click();
}
