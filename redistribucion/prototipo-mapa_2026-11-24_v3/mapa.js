/* Mapa NAU-2 · prototipo v3 (24/11/2026). Mismo aspecto y uso que la v2; cambia de dónde salen los datos.
 *
 * Datos reales de Odoo (copia SQLite del programa de redistribución, generados con
 * «python programa.py generar-mapa»): datos.json (posiciones y niveles), huecos.json (qué hay en cada hueco,
 * se carga al abrir uno), modelos.json (dónde está cada modelo-color) y listas.json (listas 2 a 5).
 * El «Plan Z5+01» es la estimación del Excel del 06/11, sin probar; los movimientos siguen siendo de ejemplo.
 *
 * Canvas 2D + d3 (zoom, escalas, histograma). Niveles: nave → lineal en alzado → hueco.
 * Modos: Hoy (una medida), Plan Z5+01, Cortina (hoy | plan sobre un solo plano), Lado a lado (zoom
 * sincronizado) y Diferencia. Encima solo contornos, zona de oro y flechas (ejemplo).
 * El estado va en la dirección (#...): recargar o pasar el enlace enseña lo mismo.
 */
'use strict';

// =============================================================================================== utilidades
const $ = (s, r = document) => r.querySelector(s);
const pad = n => String(n).padStart(2, '0');
const esp = (v, d = 0) => (v == null || isNaN(v) ? '—' : v.toLocaleString('es-ES', { maximumFractionDigits: d, minimumFractionDigits: d }));
const fPct = v => (v == null ? '—' : esp(v * 100) + ' %');
const fEnt = v => esp(v);
const fDec = v => esp(v, 1);
const fM = v => (v == null ? '—' : esp(v) + ' m');
const nombreHueco = p => `${p.l} P${pad(p.p)}`;

// =============================================================================================== medidas
const CAT = {
  zona: { titulo: 'Zona hoy', detalle: 'por posición · Odoo', claves: ['0', 'Z', 'M', 'vacía'],
    var: { '0': '--z0', 'Z': '--zZ', 'M': '--zM', 'vacía': '--zV' },
    nombre: { '0': 'Zona 0 · I27 y V27', 'Z': 'Zona Z · el resto', 'M': 'Mezclada (≥ 10 % de la otra)', 'vacía': 'Vacía' },
    valor: p => p.zona },
  plan: { titulo: 'Plan Z5+01 · estimación del 06/11', detalle: 'sin probar', claves: ['0', '0 libre', 'Z', 'Z libre', 'libre', 'muelle', 'muelle vacío', 'sin dato'],
    var: { '0': '--z0', '0 libre': '--p0v', 'Z': '--zZ', 'Z libre': '--pZv', 'libre': '--libre', 'muelle': '--muelle', 'muelle vacío': '--muellev', 'sin dato': '--zV' },
    nombre: { '0': 'Zona 0', '0 libre': 'Zona 0 (vacía el 06/11)', 'Z': 'Zona Z', 'Z libre': 'Zona Z (vacía el 06/11)',
      'libre': 'Libre', 'muelle': 'Muelle', 'muelle vacío': 'Muelle vacío', 'sin dato': 'Sin dato' },
    valor: p => p.plan },
};
// Todas las medidas son por posición (suma de sus niveles). `lin`: el mismo dato por lineal, para la lista del panel.
const NUM = [
  { id: 'disp', titulo: 'Dispersión del modelo', detalle: 'lineales por modelo-color · media', fmt: fDec, valor: p => p.d, lin: 'dispersion',
    ayuda: 'En cuántos lineales está, de media, cada modelo-color de la posición (ponderado por unidades). 1 = junto.' },
  { id: 'visitas', titulo: 'Calor de picking', detalle: 'visitas en 4 semanas', fmt: fEnt, valor: p => p.v, lin: 'visitas',
    ayuda: 'Paradas de picking: pares distintos albarán–hueco de las salidas de las últimas 4 semanas. No son unidades.' },
  { id: 'metros', titulo: 'Metros a expedición', detalle: 'por posición · calculado', fmt: fM, valor: p => p.m },
  { id: 'uds', titulo: 'Unidades', detalle: 'por posición', fmt: fEnt, valor: p => p.u, lin: 'uds' },
  { id: 'oc', titulo: '% de niveles con stock', detalle: 'por posición', fmt: fPct, valor: p => p.oc, lin: 'pct_ocupacion' },
  { id: 'cont', titulo: 'Contenedores con stock', detalle: 'por posición', fmt: fEnt, valor: p => p.c, lin: 'contenedores' },
  { id: 'litros', titulo: 'Litros', detalle: 'por posición · parte estimada', fmt: fEnt, valor: p => p.lt, lin: 'litros' },
  { id: 'mc', titulo: 'Modelos-color distintos', detalle: 'por posición', fmt: fEnt, valor: p => p.mc, lin: 'modelos_color' },
  { id: 'pct_z', titulo: '% de unidades de zona Z', detalle: 'por posición', fmt: fPct, valor: p => (p.u ? p.uz / p.u : null), lin: 'pct_z' },
  { id: 'pct_0', titulo: '% de unidades de zona 0', detalle: 'por posición', fmt: fPct, valor: p => (p.u ? p.u0 / p.u : null), lin: 'pct_0' },
];
const NUM_POR_ID = Object.fromEntries(NUM.map(m => [m.id, m]));
const ORO_METROS = 40;
// Con la pestaña oculta el navegador para las animaciones: entonces todo se pinta sin transición.
const sinAnimar = () => document.hidden;

// =============================================================================================== estado
const E = {
  modo: 'hoy', medida: 'disp', contorno: false, oro: false, flechas: false, tema: 'claro', panel: true,
  nivel: 'nave', lineal: null, hueco: null,     // hueco: {p, n}
  fijadas: [],                                   // índices de posición (máx. 2)
  seleccion: null,                               // {x0,x1,y0,y1}
  apagadas: {},                                  // capa -> Set de claves apagadas
  rango: {},                                     // medida numérica -> [a, b]
  cortina: 0.5,
  flecha: null,
  busqueda: '',
};
let D = null, POS = [], LIN = {}, IDX = new Map(), CUBOS = new Map();
let MODELOS = {};             // modelo-color -> [nº lineales, nº huecos, uds, zona, [[clave hueco, uds], …]]
let HUECOS = null, LISTAS = null;   // se cargan cuando hacen falta
let modeloBuscado = null;     // modelo-color (o modelo) resaltado por el buscador
let MUNDO = null, NAVE = null;
let T = d3.zoomIdentity;
let VISTAS = [];
let COL = {};                 // colores del tema
let hover = null, hoverLineal = null, resaltar = null, resaltarEjemplo = false;
let animando = 0;

// =============================================================================================== carga
const leerJSON = f => fetch(f, { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(f + ': HTTP ' + r.status); return r.json(); });
Promise.all([leerJSON('datos.json'), leerJSON('modelos.json')])
  .then(([d, m]) => { MODELOS = m; iniciar(d); })
  .catch(e => {
    $('#carga').innerHTML = `<div style="max-width:420px;text-align:center"><b>No se han podido leer los datos</b><br>
      <span class="nota">${e.message}. Genera los datos con <code>python programa.py generar-mapa</code> y arranca el servidor (README.md).</span></div>`;
  });
const cargarHuecos = () => HUECOS ? Promise.resolve(HUECOS) : leerJSON('huecos.json').then(h => (HUECOS = h));
const cargarListas = () => LISTAS ? Promise.resolve(LISTAS) : leerJSON('listas.json').then(l => (LISTAS = l));

function iniciar(d) {
  D = d;
  POS = d.posiciones.map((p, i) => Object.assign({ i, cx: (p.x0 + p.x1) / 2, cy: (p.y0 + p.y1) / 2 }, p));
  LIN = d.lineales;
  POS.forEach(p => {
    IDX.set(p.l + '|' + p.p, p.i);
    for (let x = Math.floor(p.x0); x <= Math.floor(p.x1); x++) {
      if (!CUBOS.has(x)) CUBOS.set(x, []);
      CUBOS.get(x).push(p);
    }
  });
  const nave = POS.filter(p => !p.muelle);
  NAVE = { x0: d3.min(nave, p => p.x0) - 0.7, x1: d3.max(nave, p => p.x1) + 0.7,
    y0: d3.min(nave, p => p.y0) - 0.7, y1: d3.max(nave, p => p.y1) + 0.7 };
  MUNDO = { x0: d.geometria.base[0] - 4, x1: d3.max(POS, p => p.x1) + 1.5, y0: NAVE.y0 - 2.5, y1: NAVE.y1 + 2.5 };
  precalcular();

  // controles
  const sel = $('#medida');
  NUM.slice(0, 2).forEach(m => sel.add(new Option(`${m.titulo} · ${m.detalle}`, m.id)));
  sel.add(new Option('Zona hoy · por posición', 'zona'));
  NUM.slice(2).forEach(m => sel.add(new Option(`${m.titulo} · ${m.detalle}`, m.id)));
  sel.onchange = () => { E.medida = sel.value; cambiarColores(); refrescarTodo(); };
  document.querySelectorAll('#modos button').forEach(b => b.onclick = () => ponerModo(b.dataset.modo));
  conmutar('#b-contorno', 'contorno');
  conmutar('#b-oro', 'oro');
  conmutar('#b-flechas', 'flechas', () => { if (!E.flechas) E.flecha = null; arrancarAnimacion(); });
  $('#b-tema').onclick = () => { E.tema = E.tema === 'claro' ? 'oscuro' : 'claro'; aplicarTema(); };
  $('#b-panel').onclick = () => { E.panel = !E.panel; $('#cuerpo').classList.toggle('sin-panel', !E.panel); guardarURL(); };
  $('#cuerpo').addEventListener('transitionend', () => redimensionar());
  $('#b-png').onclick = guardarPNG;
  const dl = $('#sugerencias');
  Object.keys(LIN).forEach(l => dl.append(new Option(l)));
  ['I27', 'V27', 'PERMANENTE', 'I26', 'V26', 'I25', 'I16', 'I12'].forEach(t => dl.append(new Option(t, t)));
  // los 300 modelos-color más repartidos (en el buscador vale cualquiera, o el modelo sin color)
  Object.entries(MODELOS).sort((a, b) => b[1][0] - a[1][0] || b[1][2] - a[1][2]).slice(0, 300)
    .forEach(([mc, v]) => dl.append(new Option(mc, `${v[0]} lineales · ${fEnt(v[2])} uds`)));
  $('#b-listas').onclick = () => abrirListas();
  $('#buscar').addEventListener('input', () => buscar($('#buscar').value));
  document.addEventListener('keydown', teclas);
  new ResizeObserver(() => redimensionar()).observe($('#lienzo'));
  cortina();

  leerURL();
  aplicarTema(true);
  $('#medida').value = E.medida;
  $('#cuerpo').classList.toggle('sin-panel', !E.panel);
  ['contorno', 'oro', 'flechas'].forEach(k => $('#b-' + k).setAttribute('aria-pressed', String(E[k])));
  ponerModo(E.modo, true);
  if (E.busqueda) { $('#buscar').value = E.busqueda; buscar(E.busqueda, true); }
  if (E.nivel === 'lineal' && E.lineal) abrirAlzado(E.lineal, true);
  $('#carga').classList.add('oculto');
  arrancarAnimacion();
}

function conmutar(sel, clave, despues) {
  $(sel).onclick = () => {
    E[clave] = !E[clave];
    $(sel).setAttribute('aria-pressed', String(E[clave]));
    if (despues) despues();
    refrescarTodo();
  };
}

// =============================================================================================== tema y colores
function aplicarTema(primera) {
  document.documentElement.dataset.theme = E.tema;
  const cs = getComputedStyle(document.documentElement);
  const v = n => cs.getPropertyValue(n).trim();
  COL = new Proxy({}, { get: (o, k) => (k in o ? o[k] : (o[k] = v(k))) });
  COL.secuencial = E.tema === 'claro' ? (t => d3.interpolateYlGnBu(0.12 + 0.88 * t)) : (t => d3.interpolateViridis(0.08 + 0.92 * t));
  VISTAS.forEach(w => { w.cols = coloresObjetivo(w.capa); w.cols2 = w.capa2 ? coloresObjetivo(w.capa2) : null; });
  if (!primera) { refrescarTodo(); guardarURL(); }
}

function capaColor(capa, clave) { return COL[CAT[capa].var[clave]]; }

/** Color y si está encendida, para una posición en una capa ('zona' | 'plan' | 'dif' | id numérico). */
function colorDe(p, capa) {
  if (capa === 'zona' || capa === 'plan') {
    const k = CAT[capa].valor(p);
    return capaColor(capa, k) || COL['--zV'];
  }
  if (capa === 'dif') {
    const t = transicion(p);
    if (t.igual) return COL['--zV'];
    return destinoColor(t.b);
  }
  const m = NUM_POR_ID[capa];
  const v = valorNum(p, m);
  if (v == null) return COL['--superficie'];
  const [a, b] = DOMINIO[capa];
  return COL.secuencial(b > a ? Math.max(0, Math.min(1, (v - a) / (b - a))) : 0.5);
}

function encendida(p, capa) {
  if (capa === 'zona' || capa === 'plan') {
    const off = E.apagadas[capa];
    return !(off && off.has(CAT[capa].valor(p)));
  }
  if (capa === 'dif') {
    const off = E.apagadas.dif;
    return !(off && off.has(transicion(p).clave));
  }
  const r = E.rango[capa];
  if (!r) return true;
  const v = valorNum(p, NUM_POR_ID[capa]);
  return v != null && v >= r[0] && v <= r[1];
}

function valorNum(p, m) {
  if (m.valor) return m.valor(p) ?? null;
  const l = LIN[p.l];
  return l ? l[m.id] ?? null : null;
}

let DOMINIO = {};
function normPlan(c) {
  if (c === '0' || c === '0 libre') return '0';
  if (c === 'Z' || c === 'Z libre') return 'Z';
  if (c === 'muelle' || c === 'muelle vacío') return 'muelle';
  return c;
}
function transicion(p) {
  const a = p.zona, b = normPlan(p.plan);
  const igual = a === b || (a === 'vacía' && b === 'libre');
  return { a, b, igual, clave: igual ? 'igual' : a + '→' + b };
}
function destinoColor(b) {
  return { '0': COL['--z0'], 'Z': COL['--zZ'], 'libre': COL['--libre'], 'muelle': COL['--muelle'] }[b] || COL['--zV'];
}
let CATS_DIF = [];
let CONTORNOS = {}, FLECHAS = [], KPI = null;

function precalcular() {
  // dominios de las medidas numéricas
  // Escala hasta el percentil 98: con datos reales hay posiciones muy por encima del resto (calor, unidades)
  // y con el máximo todo saldría del mismo color. Lo que pasa del tope se pinta con el color del tope.
  NUM.forEach(m => {
    const f = POS.filter(p => !p.muelle).map(m.valor).filter(v => v != null).sort(d3.ascending);
    const tope = m.id === 'metros' || m.fmt === fPct ? d3.max(f) : d3.quantileSorted(f, 0.98);
    DOMINIO[m.id] = [d3.min(f), Math.max(tope, d3.min(f) + 1e-9)];
  });
  // categorías de la diferencia
  const n = d3.rollup(POS, v => v.length, p => transicion(p).clave);
  CATS_DIF = [...n.entries()].sort((a, b) => (a[0] === 'igual') - (b[0] === 'igual') || b[1] - a[1])
    .map(([clave, cuantas]) => { const [a, b] = clave.split('→'); return { clave, cuantas, a, b }; });
  // contornos entre zona 0 y Z
  const zonaHoy = p => (p.zona === '0' || p.zona === 'Z' ? p.zona : null);
  const zonaPlan = p => { const z = normPlan(p.plan); return z === '0' || z === 'Z' ? z : null; };
  const porLineal = d3.group(POS.filter(p => !p.muelle), p => p.l);
  for (const [capa, f] of [['zona', zonaHoy], ['plan', zonaPlan]]) {
    const seg = [];
    for (const ps of porLineal.values()) {
      const o = ps.slice().sort((a, b) => a.y0 - b.y0);
      for (let k = 1; k < o.length; k++) {
        const a = o[k - 1], b = o[k];
        if (b.y0 - a.y1 > 0.5) continue;
        const za = f(a), zb = f(b);
        if (za && zb && za !== zb) { const y = (a.y1 + b.y0) / 2; seg.push([a.x0 - 0.05, y, a.x1 + 0.05, y]); }
      }
    }
    for (const [l, ps] of porLineal) {
      const vec = 'L' + pad(parseInt(l.slice(1), 10) + 1);
      ps.forEach(a => {
        const j = IDX.get(vec + '|' + a.p);
        if (j == null) return;
        const b = POS[j], za = f(a), zb = f(b);
        if (za && zb && za !== zb) { const x = (a.x1 + b.x0) / 2; seg.push([x, a.y0 - 0.05, x, a.y1 + 0.05]); }
      });
    }
    CONTORNOS[capa] = seg;
  }
  // flechas de ejemplo con metros ahorrados (la geometría es real; el movimiento, de ejemplo)
  FLECHAS = D.ejemplo.flechas.map((f, k) => {
    const a = POS[IDX.get(f.de[0] + '|' + f.de[1])], b = POS[IDX.get(f.a[0] + '|' + f.a[1])];
    return a && b ? { k, a, b, ahorro: (a.m ?? 0) - (b.m ?? 0) } : null;
  }).filter(Boolean).sort((x, y) => y.ahorro - x.ahorro);
  // cifras de hoy frente al plan (reales: cuentas del Excel y metros de la geometría)
  const media = arr => (arr.length ? d3.mean(arr, p => p.m) : null);
  const conM = POS.filter(p => p.m != null);
  const lineales = (f) => new Set(POS.filter(f).filter(p => !p.muelle).map(p => p.l)).size;
  KPI = {
    zHoy: POS.filter(p => p.zona === 'Z').length,
    zPlan: POS.filter(p => normPlan(p.plan) === 'Z').length,
    ceroHoy: POS.filter(p => p.zona === '0').length,
    ceroPlan: POS.filter(p => normPlan(p.plan) === '0').length,
    linZHoy: lineales(p => p.zona === 'Z'),
    linZPlan: lineales(p => normPlan(p.plan) === 'Z'),
    libres: POS.filter(p => p.plan === 'libre').length,
    linLibres: (() => { const g = d3.group(POS.filter(p => !p.muelle), p => p.l);
      return [...g.values()].filter(ps => ps.every(p => p.plan === 'libre')).length; })(),
    mZHoy: media(conM.filter(p => p.zona === 'Z')), mZPlan: media(conM.filter(p => normPlan(p.plan) === 'Z')),
    m0Hoy: media(conM.filter(p => p.zona === '0')), m0Plan: media(conM.filter(p => normPlan(p.plan) === '0')),
  };
}

// =============================================================================================== vistas
function capasDelModo() {
  switch (E.modo) {
    case 'plan': return [{ capa: 'plan' }];
    case 'cortina': return [{ capa: 'zona', capa2: 'plan' }];
    case 'lado': return [{ capa: 'zona', rotulo: `Hoy · Odoo ${D.fecha_datos}` }, { capa: 'plan', rotulo: 'Plan Z5+01 · estimación del 06/11, sin probar' }];
    case 'dif': return [{ capa: 'dif' }];
    default: return [{ capa: E.medida }];
  }
}

function ponerModo(modo, inicial) {
  const antes = VISTAS[0] ? encuadreActual(VISTAS[0]) : null;
  E.modo = modo;
  document.querySelectorAll('#modos button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.modo === modo)));
  $('#medida').disabled = modo !== 'hoy';
  $('#medida').title = modo === 'hoy' ? '' : 'La medida se elige en el modo Hoy; aquí se compara la zona';
  $('#cortina').classList.toggle('oculto', modo !== 'cortina');
  construirVistas();
  if (antes && !inicial) restaurarEncuadre(antes);
  if (inicial && E._zoomURL) { T = E._zoomURL; sincronizar(null); }
  refrescarTodo();
}

function construirVistas() {
  const cont = $('#vistas');
  cont.innerHTML = '';
  VISTAS = capasDelModo().map(c => {
    const el = document.createElement('div');
    el.className = 'vista';
    const canvas = document.createElement('canvas');
    el.append(canvas);
    if (c.rotulo) { const r = document.createElement('div'); r.className = 'rotulo-vista'; r.textContent = c.rotulo; el.append(r); }
    cont.append(el);
    const w = Object.assign({ el, canvas, ctx: canvas.getContext('2d') }, c);
    w.cols = coloresObjetivo(w.capa);
    w.cols2 = w.capa2 ? coloresObjetivo(w.capa2) : null;
    prepararZoom(w);
    prepararRaton(w);
    return w;
  });
  colocarVistas();
}

function colocarVistas() {
  const cont = $('#vistas');
  if (VISTAS.length === 2) {
    const r = $('#lienzo').getBoundingClientRect();
    const dx = MUNDO.x1 - MUNDO.x0, dy = MUNDO.y1 - MUNDO.y0;
    const esc = (w, h) => Math.min(w / dx, h / dy);
    cont.classList.toggle('vertical', esc(r.width, r.height / 2) > esc(r.width / 2, r.height));
  } else cont.classList.remove('vertical');
  VISTAS.forEach(medirVista);
}

function medirVista(w) {
  const r = w.el.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  w.w = r.width; w.h = r.height; w.dpr = dpr;
  w.canvas.width = Math.max(1, Math.round(r.width * dpr));
  w.canvas.height = Math.max(1, Math.round(r.height * dpr));
  const dos = VISTAS.length === 2;
  const pad = { t: dos ? 34 : 40, b: dos ? 48 : 100, l: 40, r: 24 };
  const dx = MUNDO.x1 - MUNDO.x0, dy = MUNDO.y1 - MUNDO.y0;
  const aw = Math.max(50, w.w - pad.l - pad.r), ah = Math.max(50, w.h - pad.t - pad.b);
  w.s0 = Math.min(aw / dx, ah / dy);
  w.ox = pad.l + (aw - dx * w.s0) / 2;
  w.oy = pad.t + (ah - dy * w.s0) / 2;
}

// Con dos vistas, las dos tienen que compartir la misma base para que el zoom sea el mismo.
function igualarBases() {
  if (VISTAS.length !== 2) return;
  const [a, b] = VISTAS;
  const s0 = Math.min(a.s0, b.s0);
  VISTAS.forEach(w => {
    const dx = MUNDO.x1 - MUNDO.x0, dy = MUNDO.y1 - MUNDO.y0;
    w.ox += (dx * (w.s0 - s0)) / 2; w.oy += (dy * (w.s0 - s0)) / 2; w.s0 = s0;
  });
  const ox = Math.min(a.ox, b.ox), oy = Math.min(a.oy, b.oy);
  VISTAS.forEach(w => { w.ox = ox; w.oy = oy; });
}

// Plano en blanco al abrir (v2): si la primera medida se hacía con el lienzo aún sin tamaño (0 px), el encuadre
// «de antes» salía de una escala absurda y al restaurarlo la cámara quedaba fuera de la nave. Ahora solo se
// restaura un encuadre medido con tamaño de verdad y con el centro dentro de la nave; si no, toda la nave.
const medidaValida = w => w && w.w >= 120 && w.h >= 120;
function redimensionar() {
  if (!D) return;
  const antes = medidaValida(VISTAS[0]) ? encuadreActual(VISTAS[0]) : null;
  colocarVistas();
  igualarBases();
  if (!medidaValida(VISTAS[0])) return;
  if (E._vista) { restaurarEncuadre(E._vista); E._vista = null; }      // encuadre de la dirección, ya con tamaño
  else if (antes &&antes.cx >= NAVE.x0 - 5 && antes.cx <= MUNDO.x1 + 5 && antes.cy >= MUNDO.y0 && antes.cy <= MUNDO.y1) restaurarEncuadre(antes);
  else { T = d3.zoomIdentity; sincronizar(null); }
  dibujarTodo();
  if (E.nivel === 'lineal') dibujarAlzado();
  colocarCortina();
}

// coordenadas: metros -> base -> pantalla
const bx = (w, x) => w.ox + (x - MUNDO.x0) * w.s0;
const by = (w, y) => w.oy + (MUNDO.y1 - y) * w.s0;
const sx = (w, x) => T.applyX(bx(w, x));
const sy = (w, y) => T.applyY(by(w, y));
const pxm = w => w.s0 * T.k;                    // píxeles por metro
const amundo = (w, px, py) => [MUNDO.x0 + (T.invertX(px) - w.ox) / w.s0, MUNDO.y1 - (T.invertY(py) - w.oy) / w.s0];

function encuadreActual(w) {
  const [cx, cy] = amundo(w, w.w / 2, w.h / 2);
  return { cx, cy, pxm: pxm(w) };
}
function restaurarEncuadre(e) {
  const w = VISTAS[0];
  const k = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, e.pxm / w.s0));
  T = d3.zoomIdentity.translate(w.w / 2 - k * bx(w, e.cx), w.h / 2 - k * by(w, e.cy)).scale(k);
  sincronizar(null);
}

// =============================================================================================== zoom
const ZOOM_MIN = 0.85, ZOOM_MAX = 60;
let zoomComp = null;

function prepararZoom(w) {
  w.zoom = d3.zoom().scaleExtent([ZOOM_MIN, ZOOM_MAX]).clickDistance(4)
    .filter(ev => !ev.shiftKey && !ev.button && ev.type !== 'dblclick')
    .on('start', () => w.canvas.classList.add('arrastrando'))
    .on('end', () => { w.canvas.classList.remove('arrastrando'); guardarURL(); })
    .on('zoom', ev => { T = ev.transform; sincronizar(w); dibujarTodo(); });
  w.sel = d3.select(w.canvas).call(w.zoom);
  w.canvas.addEventListener('dblclick', ev => {
    const [mx, my] = amundo(w, ev.offsetX, ev.offsetY);
    irA(mx, my, Math.min(ZOOM_MAX, T.k * 2.2), 520);
  });
}

function sincronizar(origen) {
  VISTAS.forEach(w => { if (w !== origen) w.canvas.__zoom = T; });
}

/** Lleva la cámara a (x, y) en metros con zoom k, animado. */
function irA(x, y, k, ms = 600) {
  const w = VISTAS[0];
  const fin = d3.zoomIdentity.translate(w.w / 2 - k * bx(w, x), w.h / 2 - k * by(w, y)).scale(k);
  if (sinAnimar()) { w.sel.call(w.zoom.transform, fin); return Promise.resolve(); }
  return w.sel.transition().duration(ms).ease(d3.easeCubicInOut).call(w.zoom.transform, fin).end().catch(() => {});
}
function encuadrar(caja, ms = 650) {
  const w = VISTAS[0];
  if (!caja && sinAnimar()) { w.sel.call(w.zoom.transform, d3.zoomIdentity); return Promise.resolve(); }
  if (!caja) return w.sel.transition().duration(ms).ease(d3.easeCubicInOut).call(w.zoom.transform, d3.zoomIdentity).end().catch(() => {});
  const cw = (caja.x1 - caja.x0 + 6) * w.s0, ch = (caja.y1 - caja.y0 + 6) * w.s0;
  const k = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.min(w.w / cw, (w.h - 90) / ch)));
  return irA((caja.x0 + caja.x1) / 2, (caja.y0 + caja.y1) / 2, k, ms);
}

// =============================================================================================== colores con transición
function coloresObjetivo(capa) { return POS.map(p => colorDe(p, capa)); }

function cambiarColores() {
  const nuevas = capasDelModo();
  VISTAS.forEach((w, k) => {
    const c = nuevas[k] || nuevas[0];
    const destino = coloresObjetivo(c.capa);
    const desde = w.cols.slice();
    w.capa = c.capa;
    if (sinAnimar()) { w.cols = destino; w.anim = null; return; }
    const interp = destino.map((d, i) => d3.interpolateRgb(desde[i], d));
    const t0 = performance.now();
    w.anim = t => { const u = Math.min(1, (t - t0) / 420); const e = d3.easeCubicOut(u);
      for (let i = 0; i < interp.length; i++) w.cols[i] = interp[i](e); return u < 1; };
  });
  arrancarAnimacion();
}

function arrancarAnimacion() {
  if (animando) return;
  const paso = t => {
    let seguir = E.flechas || (resaltar && resaltar.size > 0 && resaltar.size <= 60);
    VISTAS.forEach(w => { if (w.anim) { if (!w.anim(t)) w.anim = null; else seguir = true; } });
    dibujarTodo(t);
    animando = seguir ? requestAnimationFrame(paso) : 0;
  };
  animando = requestAnimationFrame(paso);
}

// =============================================================================================== dibujo
function dibujarTodo(t) {
  if (!D) return;
  VISTAS.forEach(w => dibujar(w, t || performance.now()));
  pintarEstado();
}

function dibujar(w, t) {
  const c = w.ctx, k = pxm(w);
  c.setTransform(w.dpr, 0, 0, w.dpr, 0, 0);
  c.fillStyle = COL['--plano'];
  c.fillRect(0, 0, w.w, w.h);
  // suelo de la nave
  const n0x = sx(w, NAVE.x0), n0y = sy(w, NAVE.y1), n1x = sx(w, NAVE.x1), n1y = sy(w, NAVE.y0);
  c.fillStyle = COL['--suelo'];
  redondeado(c, n0x, n0y, n1x - n0x, n1y - n0y, Math.min(8, k * 0.8));
  c.fill();
  c.strokeStyle = COL['--borde-nave']; c.lineWidth = 1; c.stroke();
  // pasillos transversales
  const bandas = [[6.5, 9.0, 'Transversal'], [29.0, 31.0, 'Pasillo central'], [43.0, 45.5, 'Transversal']];
  bandas.forEach(([y0, y1]) => { c.fillStyle = COL['--pasillo']; c.fillRect(n0x, sy(w, y1), n1x - n0x, sy(w, y0) - sy(w, y1)); });
  // zona de oro (rombo: |x-26| + |y-30| < 40 m, el camino a pie más corto)
  if (E.oro) dibujarOro(w);
  // celdas
  const cortinaX = w.capa2 ? E.cortina * w.w : null;
  const hayFiltroBusqueda = !!resaltar;
  const vx0 = -2, vx1 = w.w + 2, vy0 = -2, vy1 = w.h + 2;
  const minW = 1.0;
  for (let i = 0; i < POS.length; i++) {
    const p = POS[i];
    let x0 = sx(w, p.x0), x1 = sx(w, p.x1), y0 = sy(w, p.y1), y1 = sy(w, p.y0);
    if (x1 < vx0 || x0 > vx1 || y1 < vy0 || y0 > vy1) continue;
    if (x1 - x0 < minW) { const m = (x0 + x1) / 2; x0 = m - minW / 2; x1 = m + minW / 2; }
    const gap = k > 18 ? 1 : 0.5;
    y0 += gap / 2; y1 -= gap / 2;
    let alfa = hayFiltroBusqueda && !resaltar.has(i) ? 0.13 : 1;
    if (cortinaX != null) {
      if (x0 < cortinaX) pintarCelda(c, p, w.capa, w.cols[i], x0, Math.min(x1, cortinaX), y0, y1, alfa);
      if (x1 > cortinaX) pintarCelda(c, p, w.capa2, w.cols2[i], Math.max(x0, cortinaX), x1, y0, y1, alfa);
    } else pintarCelda(c, p, w.capa, w.cols[i], x0, x1, y0, y1, alfa);
  }
  // muelle
  const mu = POS.filter(p => p.muelle);
  if (mu.length) {
    const a = sx(w, d3.min(mu, p => p.x0) - 0.7), b = sy(w, d3.max(mu, p => p.y1) + 0.7);
    const cc = sx(w, d3.max(mu, p => p.x1) + 0.7), dd = sy(w, d3.min(mu, p => p.y0) - 0.7);
    c.save(); c.setLineDash([4, 4]); c.strokeStyle = COL['--borde-nave']; c.lineWidth = 1;
    redondeado(c, a, b, cc - a, dd - b, 6); c.stroke(); c.restore();
    texto(c, 'Muelle', a, b - 6, { color: COL['--texto-2'], peso: 600, base: 'bottom' });
    texto(c, 'sitio aproximado', a, b - 6 - 13, { color: COL['--texto-3'], tam: 10, base: 'bottom' });
  }
  // rótulos de pasillos (centrados en la parte visible)
  bandas.forEach(([y0, y1, t]) => {
    const yy = (sy(w, y0) + sy(w, y1)) / 2;
    if (sy(w, y0) - sy(w, y1) < 9) return;
    const xa = Math.max(n0x, 0), xb = Math.min(n1x, w.w);
    if (xb - xa < 120) return;
    texto(c, t, (xa + xb) / 2, yy, { color: COL['--pasillo-texto'], tam: Math.min(12, Math.max(9.5, (sy(w, y0) - sy(w, y1)) * 0.6)), al: 'center', base: 'middle', espaciado: true });
  });
  // contornos
  if (E.contorno) {
    c.save();
    if (cortinaX != null) { trazarContornos(w, 'zona', 0, cortinaX); trazarContornos(w, 'plan', cortinaX, w.w); }
    else if (w.capa === 'zona' || w.capa === 'plan') trazarContornos(w, w.capa, 0, w.w);
    else if (w.capa === 'dif') trazarContornos(w, 'plan', 0, w.w);
    else trazarContornos(w, 'zona', 0, w.w);
    c.restore();
  }
  // lineal bajo el ratón, selección, fijadas
  if (hoverLineal) contornoLineal(w, hoverLineal, COL['--acento'], 1.5);
  if (E.seleccion) {
    const s = E.seleccion;
    const a = sx(w, s.x0), b = sy(w, s.y1), cc = sx(w, s.x1), dd = sy(w, s.y0);
    c.fillStyle = COL['--acento'] + '18'; c.strokeStyle = COL['--acento']; c.lineWidth = 1.5; c.setLineDash([5, 3]);
    c.fillRect(a, b, cc - a, dd - b); c.strokeRect(a, b, cc - a, dd - b); c.setLineDash([]);
  }
  if (resaltar && resaltar.size && resaltar.size <= 60) {
    const fase = (performance.now() % 1600) / 1600;
    resaltar.forEach(i => {
      const p = POS[i], x = sx(w, p.cx), y = sy(w, p.cy);
      c.beginPath(); c.arc(x, y, 7 + 8 * fase, 0, Math.PI * 2);
      c.strokeStyle = resaltarEjemplo ? COL['--ejemplo'] : COL['--acento']; c.globalAlpha = 1 - fase; c.lineWidth = 2; c.stroke();
      c.globalAlpha = 1;
      marcoCelda(w, p, resaltarEjemplo ? COL['--ejemplo'] : COL['--acento'], 2);
    });
  }
  if (hover != null) marcoCelda(w, POS[hover], COL['--texto'], 2);
  E.fijadas.forEach((i, n) => { marcoCelda(w, POS[i], COL['--texto'], 2.5); insignia(w, POS[i], n ? 'B' : 'A'); });
  if (E.flechas) dibujarFlechas(w, t);
  // expedición
  const ex = sx(w, D.geometria.base[0]), ey = sy(w, D.geometria.base[1]);
  c.beginPath(); c.arc(ex, ey, 6, 0, Math.PI * 2); c.fillStyle = COL['--texto']; c.fill();
  c.beginPath(); c.arc(ex, ey, 10, 0, Math.PI * 2); c.strokeStyle = COL['--texto']; c.globalAlpha = 0.25; c.lineWidth = 2; c.stroke(); c.globalAlpha = 1;
  texto(c, 'Expedición', ex, ey + 15, { color: COL['--texto'], peso: 600, al: 'center', base: 'top', fondo: true });
  // números de lineal y posiciones (se pegan al borde si la nave se sale de la pantalla)
  rotulos(w);
}

function pintarCelda(c, p, capa, color, x0, x1, y0, y1, alfa) {
  const on = encendida(p, capa);
  c.globalAlpha = on ? alfa : alfa * 0.55;
  c.fillStyle = on ? color : COL['--apagado'];
  c.fillRect(x0, y0, x1 - x0, y1 - y0);
  c.globalAlpha = 1;
}

function trazarContornos(w, capa, xa, xb) {
  const c = w.ctx;
  c.save();
  c.beginPath(); c.rect(xa, 0, xb - xa, w.h); c.clip();
  c.strokeStyle = COL['--texto']; c.lineWidth = Math.max(1.6, Math.min(3, pxm(w) * 0.25)); c.lineCap = 'round';
  c.beginPath();
  CONTORNOS[capa].forEach(([x0, y0, x1, y1]) => { c.moveTo(sx(w, x0), sy(w, y0)); c.lineTo(sx(w, x1), sy(w, y1)); });
  c.stroke();
  c.restore();
}

function dibujarOro(w) {
  const c = w.ctx, [bxm, bym] = D.geometria.base, r = ORO_METROS;
  c.save();
  c.beginPath(); c.rect(sx(w, NAVE.x0), sy(w, NAVE.y1), sx(w, NAVE.x1) - sx(w, NAVE.x0), sy(w, NAVE.y0) - sy(w, NAVE.y1)); c.clip();
  c.beginPath();
  c.moveTo(sx(w, bxm + r), sy(w, bym)); c.lineTo(sx(w, bxm), sy(w, bym + r));
  c.lineTo(sx(w, bxm - r), sy(w, bym)); c.lineTo(sx(w, bxm), sy(w, bym - r)); c.closePath();
  c.fillStyle = COL['--oro']; c.globalAlpha = 0.16; c.fill(); c.globalAlpha = 1;
  c.restore();
  w.oroPendiente = true;   // el borde se dibuja encima de las celdas
}

function contornoLineal(w, l, color, ancho) {
  const ps = POS.filter(p => p.l === l);
  if (!ps.length) return;
  const c = w.ctx;
  const a = sx(w, d3.min(ps, p => p.x0)) - 2, b = sy(w, d3.max(ps, p => p.y1)) - 2;
  const cc = sx(w, d3.max(ps, p => p.x1)) + 2, dd = sy(w, d3.min(ps, p => p.y0)) + 2;
  c.strokeStyle = color; c.lineWidth = ancho; redondeado(c, a, b, cc - a, dd - b, 3); c.stroke();
}
function marcoCelda(w, p, color, ancho) {
  const c = w.ctx;
  const a = sx(w, p.x0), b = sy(w, p.y1), cc = sx(w, p.x1), dd = sy(w, p.y0);
  const ex = Math.max(0, (4 - (cc - a)) / 2);
  c.strokeStyle = COL['--superficie']; c.lineWidth = ancho + 2.5; c.strokeRect(a - ex - 1, b - 1, cc - a + 2 * ex + 2, dd - b + 2);
  c.strokeStyle = color; c.lineWidth = ancho; c.strokeRect(a - ex - 1, b - 1, cc - a + 2 * ex + 2, dd - b + 2);
}
function insignia(w, p, letra) {
  const c = w.ctx, x = sx(w, p.x1) + 6, y = sy(w, p.y1) - 6;
  c.fillStyle = COL['--texto']; redondeado(c, x - 1, y - 9, 15, 15, 4); c.fill();
  texto(c, letra, x + 6.5, y - 1.5, { color: COL['--superficie'], peso: 700, tam: 10, al: 'center', base: 'middle' });
}

function rotulos(w) {
  const c = w.ctx, k = pxm(w);
  if (w.oroPendiente) {
    const [bxm, bym] = D.geometria.base, r = ORO_METROS;
    c.save();
    c.beginPath(); c.rect(sx(w, NAVE.x0), sy(w, NAVE.y1), sx(w, NAVE.x1) - sx(w, NAVE.x0), sy(w, NAVE.y0) - sy(w, NAVE.y1)); c.clip();
    c.beginPath();
    c.moveTo(sx(w, bxm + r), sy(w, bym)); c.lineTo(sx(w, bxm), sy(w, bym + r));
    c.lineTo(sx(w, bxm - r), sy(w, bym)); c.lineTo(sx(w, bxm), sy(w, bym - r)); c.closePath();
    c.strokeStyle = COL['--oro']; c.lineWidth = 2; c.setLineDash([7, 5]); c.stroke();
    c.restore();
    const lx = sx(w, bxm + r * 0.55), ly = sy(w, bym + r * 0.45);
    texto(c, `Zona de oro · < ${ORO_METROS} m a pie`, lx, ly, { color: COL['--texto'], peso: 600, tam: 11, fondo: true });
    w.oroPendiente = false;
  }
  // números de lineal
  // L13 y L14 están espalda con espalda (0,4 m): cada lineal solo si caben; si no, uno de cada 2, 4, 10 o 20.
  const cada = k * 0.4 >= 26 ? 1 : [2, 4, 10, 20].find(s => s * k >= 30) || 20;
  const yArriba = Math.max(14, sy(w, NAVE.y1) - 8), yAbajo = Math.min(w.h - (VISTAS.length === 1 ? 92 : 50), sy(w, NAVE.y0) + 14);
  const vistos = new Set();
  POS.forEach(p => {
    if (p.muelle || vistos.has(p.l)) return;
    vistos.add(p.l);
    const n = parseInt(p.l.slice(1), 10);
    if (n !== 1 && n % cada) return;
    const x = sx(w, p.cx);
    if (x < 30 || x > w.w - 10) return;
    const fuerte = hoverLineal === p.l;
    const opt = { color: fuerte ? COL['--acento'] : COL['--texto-2'], tam: 10.5, peso: fuerte ? 700 : 500, al: 'center' };
    texto(c, p.l, x, yArriba, Object.assign({ base: 'bottom' }, opt));
    if (yAbajo > yArriba + 40) texto(c, p.l, x, yAbajo, Object.assign({ base: 'top' }, opt));
  });
  if (hoverLineal && !vistos.has('__')) {
    const ps = POS.filter(p => p.l === hoverLineal);
    if (ps.length && !ps[0].muelle) {
      const x = sx(w, ps[0].cx);
      texto(c, hoverLineal, x, yArriba, { color: COL['--superficie'], tam: 10.5, peso: 700, al: 'center', base: 'bottom', fondo: COL['--acento'] });
    }
  }
  // posiciones a la izquierda
  const xIzq = Math.max(sx(w, NAVE.x0) - 6, 34);
  const marcas = [1, 4, 10, 17, 18, 24, 25, 30, 36, 42];
  const L = POS.find(p => p.l === 'L01');
  let ultima = -99;
  marcas.forEach(n => {
    const p = POS.find(q => q.p === n && !q.muelle);
    if (!p) return;
    const y = sy(w, p.cy);
    if (y < 10 || y > w.h - 10 || Math.abs(y - ultima) < 14) return;
    if (Math.abs(y - sy(w, D.geometria.base[1])) < 16 && Math.abs(xIzq - sx(w, D.geometria.base[0])) < 40) return;
    ultima = y;
    texto(c, 'P' + pad(n), xIzq, y, { color: COL['--texto-3'], tam: 10, al: 'right', base: 'middle' });
  });
}

function dibujarFlechas(w, t) {
  const c = w.ctx;
  FLECHAS.forEach(f => {
    const a = [sx(w, f.a.cx), sy(w, f.a.cy)], b = [sx(w, f.b.cx), sy(w, f.b.cy)];
    const sel = E.flecha === f.k;
    const atenuada = E.flecha != null && !sel;
    const [qx, qy] = control(a, b);
    c.save();
    c.globalAlpha = atenuada ? 0.25 : 1;
    c.strokeStyle = COL['--superficie']; c.lineWidth = sel ? 6 : 4.5;
    c.beginPath(); c.moveTo(a[0], a[1]); c.quadraticCurveTo(qx, qy, b[0], b[1]); c.stroke();
    c.strokeStyle = COL['--ejemplo']; c.lineWidth = sel ? 3 : 2;
    c.setLineDash([7, 6]); c.lineDashOffset = -(t / 40) % 13;
    c.beginPath(); c.moveTo(a[0], a[1]); c.quadraticCurveTo(qx, qy, b[0], b[1]); c.stroke();
    c.setLineDash([]);
    // punta
    const ang = Math.atan2(b[1] - qy, b[0] - qx), L = sel ? 13 : 10;
    c.fillStyle = COL['--ejemplo'];
    c.beginPath(); c.moveTo(b[0], b[1]);
    c.lineTo(b[0] - L * Math.cos(ang - 0.42), b[1] - L * Math.sin(ang - 0.42));
    c.lineTo(b[0] - L * Math.cos(ang + 0.42), b[1] - L * Math.sin(ang + 0.42)); c.closePath(); c.fill();
    c.beginPath(); c.arc(a[0], a[1], sel ? 5 : 3.5, 0, Math.PI * 2); c.fill();
    if (sel) {
      [a, b].forEach((q, j) => {
        const r = 12 + 4 * Math.sin(t / 220);
        c.beginPath(); c.arc(q[0], q[1], r, 0, Math.PI * 2); c.strokeStyle = COL['--ejemplo']; c.lineWidth = 2; c.stroke();
        texto(c, j ? 'Destino' : 'Origen', q[0], q[1] - r - 4, { color: COL['--texto'], peso: 600, tam: 10.5, al: 'center', base: 'bottom', fondo: true });
      });
    }
    c.restore();
  });
}
function control(a, b) {
  const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1];
  return [mx - dy * 0.18, my + dx * 0.18];
}

function redondeado(c, x, y, w, h, r) {
  r = Math.max(0, Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2));
  c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
}
function texto(c, t, x, y, o = {}) {
  c.font = `${o.peso || 500} ${o.tam || 11}px Inter, system-ui, sans-serif`;
  c.textAlign = o.al || 'left'; c.textBaseline = o.base || 'alphabetic';
  if (o.espaciado && 'letterSpacing' in c) c.letterSpacing = '0.06em';
  if (o.fondo) {
    const m = c.measureText(t), wt = m.width + 10, ht = (o.tam || 11) + 6;
    let x0 = c.textAlign === 'center' ? x - wt / 2 : c.textAlign === 'right' ? x - wt + 5 : x - 5;
    let y0 = c.textBaseline === 'top' ? y - 3 : c.textBaseline === 'bottom' ? y - ht + 3 : c.textBaseline === 'middle' ? y - ht / 2 : y - ht + 4;
    c.fillStyle = typeof o.fondo === 'string' ? o.fondo : COL['--superficie'];
    c.globalAlpha = typeof o.fondo === 'string' ? 1 : 0.92; redondeado(c, x0, y0, wt, ht, 4); c.fill(); c.globalAlpha = 1;
  }
  c.fillStyle = o.color || COL['--texto'];
  c.fillText(t, x, y);
  if ('letterSpacing' in c) c.letterSpacing = '0px';
}

// =============================================================================================== ratón
function celdaEn(w, px, py) {
  const [mx, my] = amundo(w, px, py);
  const tol = Math.max(0, 3 / pxm(w));
  let mejor = null, dist = 1e9;
  for (let x = Math.floor(mx - tol); x <= Math.floor(mx + tol); x++) {
    (CUBOS.get(x) || []).forEach(p => {
      if (mx >= p.x0 - tol && mx <= p.x1 + tol && my >= p.y0 && my <= p.y1) {
        const d = Math.abs(mx - p.cx);
        if (d < dist) { dist = d; mejor = p; }
      }
    });
  }
  return mejor;
}
function flechaEn(w, px, py) {
  if (!E.flechas) return null;
  for (const f of FLECHAS) {
    const a = [sx(w, f.a.cx), sy(w, f.a.cy)], b = [sx(w, f.b.cx), sy(w, f.b.cy)], q = control(a, b);
    for (let s = 0; s <= 1; s += 0.025) {
      const x = (1 - s) ** 2 * a[0] + 2 * (1 - s) * s * q[0] + s * s * b[0];
      const y = (1 - s) ** 2 * a[1] + 2 * (1 - s) * s * q[1] + s * s * b[1];
      if (Math.hypot(x - px, y - py) < 7) return f;
    }
  }
  return null;
}

function prepararRaton(w) {
  const cv = w.canvas;
  let inicioSel = null;
  cv.addEventListener('pointermove', ev => {
    if (inicioSel) {
      const [x, y] = amundo(w, ev.offsetX, ev.offsetY);
      E.seleccion = { x0: Math.min(inicioSel[0], x), x1: Math.max(inicioSel[0], x), y0: Math.min(inicioSel[1], y), y1: Math.max(inicioSel[1], y) };
      dibujarTodo();
      return;
    }
    const f = flechaEn(w, ev.offsetX, ev.offsetY);
    const p = f ? null : celdaEn(w, ev.offsetX, ev.offsetY);
    const nuevo = p ? p.i : null;
    cv.classList.toggle('sobre-celda', !!(p || f));
    cv.classList.toggle('seleccionando', ev.shiftKey);
    if (nuevo !== hover || (p ? p.l : null) !== hoverLineal) {
      hover = nuevo; hoverLineal = p ? p.l : null;
      dibujarTodo(); marcarListaLineal();
    }
    if (f) mostrarTip(ev, tipFlecha(f));
    else if (p) mostrarTip(ev, tipCelda(p, w));
    else ocultarTip();
  });
  cv.addEventListener('pointerleave', () => { hover = null; hoverLineal = null; ocultarTip(); dibujarTodo(); marcarListaLineal(); });
  cv.addEventListener('pointerdown', ev => {
    if (!ev.shiftKey || ev.button) return;
    cv.setPointerCapture(ev.pointerId);
    inicioSel = amundo(w, ev.offsetX, ev.offsetY);
    E.seleccion = null;
  });
  cv.addEventListener('pointerup', ev => {
    if (!inicioSel) return;
    inicioSel = null;
    if (E.seleccion && (E.seleccion.x1 - E.seleccion.x0) * (E.seleccion.y1 - E.seleccion.y0) < 0.2) E.seleccion = null;
    pintarPanel(); dibujarTodo();
  });
  cv.addEventListener('click', ev => {
    if (ev.shiftKey) return;
    const f = flechaEn(w, ev.offsetX, ev.offsetY);
    if (f) { E.flecha = E.flecha === f.k ? null : f.k; pintarPanel(); return; }
    const p = celdaEn(w, ev.offsetX, ev.offsetY);
    if (!p) { if (E.flecha != null) { E.flecha = null; pintarPanel(); } return; }
    fijar(p.i);
  });
}

function fijar(i) {
  const k = E.fijadas.indexOf(i);
  if (k >= 0) E.fijadas.splice(k, 1);
  else { E.fijadas.push(i); if (E.fijadas.length > 2) E.fijadas.shift(); }
  if (!E.panel) { E.panel = true; $('#cuerpo').classList.remove('sin-panel'); }
  pintarPanel(); dibujarTodo(); guardarURL();
}

// =============================================================================================== tooltip
function mostrarTip(ev, html) {
  const tip = $('#tip');
  tip.innerHTML = html;
  tip.classList.add('visible');
  const r = tip.getBoundingClientRect();
  let x = ev.clientX + 16, y = ev.clientY + 16;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 16;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 16;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}
function ocultarTip() { $('#tip').classList.remove('visible'); }

function tipCelda(p, w) {
  const capa = w ? (w.capa2 && w.canvas && false ? w.capa2 : w.capa) : 'zona';
  const filas = [
    ['Zona hoy', CAT.zona.nombre[p.zona]],
    ['Unidades', `${fEnt(p.u)}${p.u ? ` · 0: ${fEnt(p.u0)} · Z: ${fEnt(p.uz)}` : ''}`],
    ['Niveles con stock', `${p.niv.filter(n => n[2] > 0).length} de ${p.niv.length}`],
    ['Contenedores', fEnt(p.c)],
    ['Modelos-color', fEnt(p.mc)],
    ['Dispersión', p.d != null ? fDec(p.d) + ' lineales' : '—'],
    ['Visitas (4 sem.)', fEnt(p.v)],
    ['A expedición', p.m != null ? fM(p.m) : '— (muelle)'],
    ['Plan (est. 06/11)', CAT.plan.nombre[p.plan]],
  ];
  const m = NUM_POR_ID[capa];
  if (m && !['metros', 'disp', 'visitas', 'uds', 'cont', 'mc'].includes(m.id)) filas.splice(1, 0, [m.titulo, m.fmt(valorNum(p, m))]);
  if (capa === 'dif') { const t = transicion(p); filas.push(['Cambio', t.igual ? 'Igual' : `${t.a} → ${t.b}`]); }
  return `<div class="t"><i style="background:${colorDe(p, capa)}"></i>${nombreHueco(p)}${p.muelle ? ' · muelle' : ''}</div>
    <dl>${filas.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join('')}</dl>`;
}
function tipFlecha(f) {
  return `<div class="t"><span class="ej">DATOS DE EJEMPLO</span></div>
    <dl><dt>De</dt><dd>${nombreHueco(f.a)}</dd><dt>A</dt><dd>${nombreHueco(f.b)}</dd>
    <dt>Metros ahorrados</dt><dd>${fM(f.ahorro)}</dd></dl>`;
}

// =============================================================================================== cortina
function cortina() {
  const asa = $('#cortina .asa');
  let arrastre = false;
  asa.addEventListener('pointerdown', ev => { arrastre = true; asa.setPointerCapture(ev.pointerId); ev.stopPropagation(); });
  asa.addEventListener('pointermove', ev => {
    if (!arrastre) return;
    const r = $('#lienzo').getBoundingClientRect();
    E.cortina = Math.max(0.02, Math.min(0.98, (ev.clientX - r.left) / r.width));
    colocarCortina(); dibujarTodo();
  });
  asa.addEventListener('pointerup', () => { arrastre = false; guardarURL(); });
}
function colocarCortina() { $('#cortina').style.left = (E.cortina * 100) + '%'; }

// =============================================================================================== leyenda
let leyendaPlegada = false;
function pintarLeyenda() {
  const ley = $('#leyenda');
  ley.innerHTML = '';
  ley.classList.toggle('oculto', E.nivel !== 'nave');
  const plegar = document.createElement('button');
  plegar.className = 'cerrar'; plegar.style.cssText = 'position:absolute;right:6px;top:6px;font-size:13px';
  plegar.textContent = leyendaPlegada ? '▴' : '▾';
  plegar.title = leyendaPlegada ? 'Desplegar la leyenda' : 'Plegar la leyenda';
  plegar.onclick = () => { leyendaPlegada = !leyendaPlegada; pintarLeyenda(); };
  ley.append(plegar);
  ley.style.paddingRight = '30px';
  document.querySelectorAll('.leyenda-vista').forEach(n => n.remove());
  const porVista = VISTAS.length === 2;
  ley.classList.toggle('oculto', E.nivel !== 'nave' || porVista);
  const capas = [...new Set(VISTAS.flatMap(w => [w.capa, w.capa2]).filter(Boolean))];
  capas.forEach((capa, nCapa) => {
    const bloque = document.createElement('div');
    if (capas.length > 1) bloque.style.marginBottom = '8px';
    if (capa === 'zona' || capa === 'plan') {
      const def = CAT[capa];
      const n = d3.rollup(POS, v => v.length, def.valor);
      bloque.innerHTML = `<h3>${def.titulo}<span class="chip-detalle">${def.detalle}</span></h3>`;
      const chips = document.createElement('div'); chips.className = 'chips';
      def.claves.forEach(k => chips.append(chip(capa, k, def.nombre[k], capaColor(capa, k), n.get(k) || 0)));
      bloque.append(chips);
    } else if (capa === 'dif') {
      bloque.innerHTML = `<h3>Qué cambia de hoy al plan Z5+01<span class="chip-detalle">por posición</span></h3>`;
      const chips = document.createElement('div'); chips.className = 'chips';
      CATS_DIF.forEach(cd => {
        const nom = cd.clave === 'igual' ? 'Sin cambio' : `${cd.a} → ${cd.b}`;
        const ch = chip('dif', cd.clave, nom, cd.clave === 'igual' ? COL['--zV'] : destinoColor(cd.b), cd.cuantas);
        if (cd.clave !== 'igual') {
          const o = document.createElement('i'); o.style.background = capaColor('zona', cd.a) || COL['--zV'];
          ch.prepend(o);
        }
        chips.append(ch);
      });
      bloque.append(chips);
    } else bloque.append(histograma(capa));
    if (porVista) {
      // Lado a lado: cada plano lleva su leyenda en una sola línea, debajo, sin tapar el plano.
      bloque.querySelector('h3').remove();
      bloque.className = 'leyenda-vista';
      VISTAS[nCapa].el.append(bloque);
      return;
    }
    if (leyendaPlegada) { const h = bloque.querySelector('h3'); bloque.innerHTML = ''; bloque.append(h); h.style.margin = '0'; }
    ley.append(bloque);
  });
}

function chip(capa, clave, nombre, color, cuantas) {
  const b = document.createElement('button');
  b.className = 'chip';
  const off = E.apagadas[capa] && E.apagadas[capa].has(clave);
  b.setAttribute('aria-pressed', String(!off));
  b.innerHTML = `<i style="background:${color}"></i>${nombre}<b>${fEnt(cuantas)}</b>`;
  b.title = 'Clic: apagar o encender. Doble clic: dejar solo esta.';
  let espera = null;
  b.onclick = () => {
    clearTimeout(espera);
    espera = setTimeout(() => {
      const s = E.apagadas[capa] || (E.apagadas[capa] = new Set());
      s.has(clave) ? s.delete(clave) : s.add(clave);
      refrescarTodo(); guardarURL();
    }, 200);
  };
  b.ondblclick = () => {
    clearTimeout(espera);
    const todas = capa === 'dif' ? CATS_DIF.map(c => c.clave) : CAT[capa].claves;
    const s = new Set(todas.filter(k => k !== clave));
    const yaSolo = E.apagadas[capa] && E.apagadas[capa].size === s.size && !E.apagadas[capa].has(clave);
    E.apagadas[capa] = yaSolo ? new Set() : s;
    refrescarTodo(); guardarURL();
  };
  return b;
}

/** Histograma de la medida con un rango que se arrastra: lo que queda fuera se apaga en el plano. */
function histograma(capa) {
  const m = NUM_POR_ID[capa];
  const cont = document.createElement('div');
  const porLineal = false;
  const [a, b] = DOMINIO[capa];
  const vals = POS.filter(p => !p.muelle).map(m.valor).filter(v => v != null).map(v => Math.min(v, b));
  const r = E.rango[capa];
  const enRango = r ? vals.filter(v => v >= r[0] && v <= r[1]).length : vals.length;
  cont.innerHTML = `<h3>${m.titulo}<span class="chip-detalle">${m.detalle}</span>
    <span class="chip-detalle">${fEnt(enRango)} de ${fEnt(vals.length)} ${porLineal ? 'lineales' : 'posiciones'}</span></h3>`;
  const W = 380, H = 74, ml = 6, mr = 6, mt = 4, mb = 18;
  const x = d3.scaleLinear().domain([a, b]).range([ml, W - mr]);
  const bins = d3.bin().domain([a, b]).thresholds(28)(vals);
  const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length)]).range([H - mb, mt]);
  const svg = d3.create('svg').attr('id', 'histo').attr('width', W).attr('height', H);
  svg.append('g').selectAll('rect').data(bins).join('rect')
    .attr('x', d => x(d.x0) + 0.5).attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 1))
    .attr('y', d => y(d.length)).attr('height', d => H - mb - y(d.length)).attr('rx', 1.5)
    .attr('fill', d => COL.secuencial(b > a ? ((d.x0 + d.x1) / 2 - a) / (b - a) : 0.5))
    .attr('opacity', d => (!r || (d.x1 > r[0] && d.x0 < r[1]) ? 1 : 0.25));
  svg.append('text').attr('x', ml).attr('y', H - 4).text(m.fmt(a));
  svg.append('text').attr('x', W - mr).attr('y', H - 4).attr('text-anchor', 'end').text((b < d3.max(POS, m.valor) ? '≥ ' : '') + m.fmt(b));
  if (r) svg.append('text').attr('x', W / 2).attr('y', H - 4).attr('text-anchor', 'middle').attr('font-weight', 600)
    .text(`${m.fmt(r[0])} – ${m.fmt(r[1])}`);
  const brush = d3.brushX().extent([[ml, mt], [W - mr, H - mb]])
    .on('end', ev => {
      if (!ev.sourceEvent) return;
      E.rango[capa] = ev.selection ? ev.selection.map(x.invert) : undefined;
      if (!ev.selection) delete E.rango[capa];
      refrescarTodo(); guardarURL();
    });
  const g = svg.append('g').call(brush);
  if (r) g.call(brush.move, r.map(x));
  cont.append(svg.node());
  const ayuda = document.createElement('div'); ayuda.className = 'ayuda-leyenda';
  ayuda.textContent = (m.ayuda ? m.ayuda + ' ' : '') + 'Arrastra sobre las barras para quedarte con un tramo; clic fuera del tramo para quitarlo.';
  cont.append(ayuda);
  return cont;
}

// =============================================================================================== panel
function pintarPanel() {
  const p = $('#panel-dentro');
  p.innerHTML = '';
  if (E.nivel === 'lineal') { p.append(...panelLineal()); return; }
  if (E.fijadas.length) p.append(tarjetaFijadas());
  if (E.seleccion) p.append(tarjetaSeleccion());
  if (modeloBuscado) p.append(tarjetaModelo());
  if (E.flechas) p.append(tarjetaMovimientos());
  p.append(tarjetaHoy());
  p.append(tarjetaLineales());
  p.append(tarjetaKPI());
}

function el(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; }

function tarjetaFijadas() {
  const t = el(`<div class="tarjeta"><h4>Fijadas<span class="der nota" style="text-transform:none;letter-spacing:0">clic en otra para comparar</span></h4></div>`);
  E.fijadas.forEach((i, n) => {
    const p = POS[i], l = LIN[p.l] || {};
    const f = el(`<div class="fijada" style="${n ? 'margin-top:12px;padding-top:12px;border-top:1px solid var(--linea)' : ''}">
      <h5><span class="letra">${n ? 'B' : 'A'}</span><i style="background:${capaColor('zona', p.zona)}"></i>${nombreHueco(p)}
        <button class="cerrar" title="Soltar" aria-label="Soltar">×</button></h5>
      <div class="datos">
        <span>Zona hoy</span><span>${CAT.zona.nombre[p.zona]}</span>
        <span>Unidades</span><span>${fEnt(p.u)}</span>
        <span>Niveles con stock</span><span>${p.niv.filter(n => n[2] > 0).length} de ${p.niv.length}</span>
        <span>Contenedores · modelos-color</span><span>${fEnt(p.c)} · ${fEnt(p.mc)}</span>
        <span>Dispersión · visitas 4 sem.</span><span>${p.d != null ? fDec(p.d) : '—'} · ${fEnt(p.v)}</span>
        <span>A expedición</span><span>${p.m != null ? fM(p.m) : '—'}</span>
        <span>Plan (est. 06/11)</span><span>${CAT.plan.nombre[p.plan]}</span>
        <span class="sub">Su lineal entero</span><span hidden></span>
        <span>Posiciones con stock</span><span>${fPct(l.pct_ocupacion)}</span>
        <span>Unidades</span><span>${fEnt(l.uds)}</span>
        <span>Zona Z</span><span>${fPct(l.pct_z)}</span>
        <span>Modelos-color</span><span>${fEnt(l.modelos_color)}</span>
      </div>
      <div class="acciones"><button class="boton alz">Ver alzado de ${p.l}</button><button class="boton cen">Centrar</button></div>
    </div>`);
    f.querySelector('.cerrar').onclick = () => fijar(i);
    f.querySelector('.alz').onclick = () => abrirAlzado(p.l);
    f.querySelector('.cen').onclick = () => irA(p.cx, p.cy, Math.max(T.k, 6));
    t.append(f);
  });
  if (E.fijadas.length === 2) {
    const [a, b] = E.fijadas.map(i => POS[i]);
    const dm = a.m != null && b.m != null ? b.m - a.m : null;
    t.append(el(`<div class="nota" style="margin-top:10px">B está a <b>${dm == null ? '—' : fM(Math.abs(dm))}</b> ${dm == null ? '' : dm > 0 ? 'más lejos' : 'más cerca'} de expedición que A
      ${a.l === b.l ? '· mismo lineal' : `· ${Math.abs(parseInt(a.l.slice(1), 10) - parseInt(b.l.slice(1), 10))} lineales de distancia`}.</div>`));
  }
  return t;
}

function tarjetaSeleccion() {
  const s = E.seleccion;
  const ps = POS.filter(p => p.cx >= s.x0 && p.cx <= s.x1 && p.cy >= s.y0 && p.cy <= s.y1);
  const n = d3.rollup(ps, v => v.length, p => p.zona);
  const np = d3.rollup(ps, v => v.length, p => normPlan(p.plan));
  const lins = [...new Set(ps.map(p => p.l))];
  const uds = d3.sum(ps, p => p.u);
  const t = el(`<div class="tarjeta"><h4>Selección<button class="cerrar der" aria-label="Quitar selección">×</button></h4>
    <div class="kpis">
      <div class="kpi"><div class="v">${fEnt(ps.length)}</div><div class="e">posiciones</div></div>
      <div class="kpi"><div class="v">${fEnt(lins.length)}</div><div class="e">lineales tocados</div></div>
    </div>
    <div class="datos">
      <span>Zona 0 hoy</span><span>${fEnt(n.get('0') || 0)}</span>
      <span>Zona Z hoy</span><span>${fEnt(n.get('Z') || 0)}</span>
      <span>Vacías hoy</span><span>${fEnt(n.get('vacía') || 0)}</span>
      <span>Ocupadas hoy</span><span>${fPct(ps.length ? ((n.get('0') || 0) + (n.get('Z') || 0) + (n.get('M') || 0)) / ps.length : null)}</span>
      <span>A expedición (media)</span><span>${fM(d3.mean(ps.filter(p => p.m != null), p => p.m))}</span>
      <span>Unidades</span><span>${fEnt(uds)}</span>
      <span>Contenedores con stock</span><span>${fEnt(d3.sum(ps, p => p.c))}</span>
      <span>Visitas de picking (4 sem.)</span><span>${fEnt(d3.sum(ps, p => p.v))}</span>
      <span>Libres con el plan (est. 06/11)</span><span>${fEnt(np.get('libre') || 0)}</span>
    </div></div>`);
  t.querySelector('.cerrar').onclick = () => { E.seleccion = null; pintarPanel(); dibujarTodo(); };
  return t;
}

function tarjetaMovimientos() {
  const total = d3.sum(FLECHAS, f => f.ahorro);
  const t = el(`<div class="tarjeta ejemplo"><h4><span class="ej">DATOS DE EJEMPLO</span> Movimientos</h4>
    <div class="kpis" style="margin-bottom:8px"><div class="kpi"><div class="v">${FLECHAS.length}</div><div class="e">movimientos</div></div>
    <div class="kpi"><div class="v">${fM(total)}</div><div class="e">ahorrados (ida)</div></div></div>
    <p class="nota" style="margin:0 0 6px">Ordenados por metros ahorrados hasta expedición (los metros salen de la geometría; los movimientos son inventados).</p>
    <ul class="lista mov"></ul></div>`);
  const ul = t.querySelector('ul');
  FLECHAS.forEach((f, n) => {
    const li = el(`<li class="${E.flecha === f.k ? 'activo' : ''}"><span class="num">${n + 1}</span><span>${nombreHueco(f.a)} → ${nombreHueco(f.b)}</span><span class="num">${fM(f.ahorro)}</span></li>`);
    li.onclick = () => { E.flecha = E.flecha === f.k ? null : f.k; pintarPanel(); if (E.flecha != null) encuadrar(cajaDe([f.a, f.b]), 600); };
    ul.append(li);
  });
  return t;
}

/** Huecos de un modelo-color, o de todos los colores de un modelo: [[clave, uds, modelo-color], …]. */
function huecosDeModelo(txt) {
  if (MODELOS[txt]) return { mcs: [txt], huecos: MODELOS[txt][4].map(([k, u]) => [k, u, txt]) };
  const mcs = Object.keys(MODELOS).filter(mc => mc.startsWith(txt + '-'));
  return { mcs, huecos: mcs.flatMap(mc => MODELOS[mc][4].map(([k, u]) => [k, u, mc])) };
}
const textoClave = k => { const [l, p, n] = k.split('|'); return `${l} P${pad(+p)} C${n}`; };

function tarjetaModelo() {
  const { mcs, huecos } = huecosDeModelo(modeloBuscado);
  const lins = new Set(huecos.map(h => h[0].split('|')[0]).filter(l => l.startsWith('L')));
  const uds = d3.sum(huecos, h => h[1]);
  const porHueco = d3.rollups(huecos, v => d3.sum(v, h => h[1]), h => h[0]).sort((a, b) => b[1] - a[1]);
  const t = el(`<div class="tarjeta"><h4>Dónde está ${modeloBuscado}<button class="cerrar der" aria-label="Quitar">×</button></h4>
    <div class="kpis">
      <div class="kpi"><div class="v">${lins.size}</div><div class="e">lineales</div></div>
      <div class="kpi"><div class="v">${porHueco.length}</div><div class="e">huecos</div></div>
      <div class="kpi"><div class="v">${fEnt(uds)}</div><div class="e">unidades</div></div>
      <div class="kpi"><div class="v">${mcs.length}</div><div class="e">${mcs.length === 1 ? 'modelo-color' : 'colores'}</div></div>
    </div>
    <p class="nota" style="margin:8px 0 6px">${lins.size > 1 ? 'Repartido: cuantos más lineales, más riesgo de faltante y más metros por pedido.' : 'Junto en un solo lineal.'}</p>
    <ul class="lista mod"></ul></div>`);
  t.querySelector('.cerrar').onclick = () => { $('#buscar').value = ''; buscar(''); };
  const ul = t.querySelector('ul');
  porHueco.slice(0, 80).forEach(([k, u]) => {
    const [l, p, n] = k.split('|');
    const li = el(`<li><span><b>${l}</b></span><span>P${pad(+p)} C${n}</span><span class="num">${fEnt(u)}</span></li>`);
    li.onclick = () => { const i = IDX.get(l + '|' + p); if (i != null) abrirAlzado(l, false, { p: +p, n: +n, i }); };
    ul.append(li);
  });
  if (porHueco.length > 80) t.append(el(`<p class="nota" style="margin:6px 0 0">… y ${porHueco.length - 80} huecos más (lista 1).</p>`));
  return t;
}

function tarjetaHoy() {
  const c = D.cifras, pz = c.posiciones_por_zona;
  const t = el(`<div class="tarjeta"><h4>Cómo está hoy<span class="der" style="text-transform:none;letter-spacing:0">Odoo ${D.fecha_datos}</span></h4>
    <div class="kpis">
      <div class="kpi"><div class="v">${fPct(c.mc_mas_de_1_lineal / c.modelos_color)}</div><div class="e">modelos-color en más de un lineal (${fEnt(c.mc_mas_de_1_lineal)} de ${fEnt(c.modelos_color)})</div></div>
      <div class="kpi"><div class="v">${fEnt(c.mc_3_o_mas_lineales)}</div><div class="e">modelos-color en 3 lineales o más</div></div>
      <div class="kpi"><div class="v">${fEnt(c.uds_mapa)}</div><div class="e">uds en huecos y muelle</div></div>
      <div class="kpi"><div class="v">${fEnt(c.uds_pendiente)}</div><div class="e">uds pendientes de ubicar (lista 5)</div></div>
      <div class="kpi"><div class="v">${fEnt(c.contenedores_a_cero)}</div><div class="e">contenedores a cero sin archivar</div></div>
      <div class="kpi"><div class="v">${fEnt(c.huecos_mezclados)}</div><div class="e">huecos con zona 0 y Z (lista 3)</div></div>
    </div>
    <div class="datos">
      <span>Posiciones de zona 0 · Z · mezcladas · vacías</span><span>${fEnt(pz['0'] || 0)} · ${fEnt(pz.Z || 0)} · ${fEnt(pz.M || 0)} · ${fEnt(pz['vacía'] || 0)}</span>
      <span>Huecos (niveles) con stock</span><span>${fEnt(c.huecos_con_stock)} de ${fEnt(c.huecos)}</span>
      <span>Visitas de picking (${c.dias_calor} días)</span><span>${fEnt(c.visitas)}</span>
      <span>Litros estimados por familia</span><span>${fPct(c.litros_estimados_pct)}</span>
      <span>Uds sin litros (sin volumen ni familia)</span><span>${fEnt(c.uds_sin_litros)}</span>
    </div>
    <div class="acciones"><button class="boton">Abrir las listas</button></div></div>`);
  t.querySelector('.acciones button').onclick = () => abrirListas();
  return t;
}

function tarjetaKPI() {
  const k = KPI;
  const fila = (titulo, hoy, plan, fmt, menosEsMejor = true, unidad = '') => {
    const d = plan - hoy, rel = hoy ? d / hoy : 0;
    const mejor = menosEsMejor ? d < 0 : d > 0;
    return `<div class="kpi"><div class="e">${titulo}</div><div class="v">${fmt(plan)}${unidad}</div>
      <div class="d ${d === 0 ? '' : mejor ? 'mejor' : 'peor'}">${d > 0 ? '+' : ''}${esp(rel * 100)} % · hoy ${fmt(hoy)}</div></div>`;
  };
  return el(`<div class="tarjeta ejemplo"><h4><span class="ej">ESTIMACIÓN DEL 06/11, SIN PROBAR</span> Plan Z5+01</h4>
    <div class="kpis">
      ${fila('Posiciones de zona Z', k.zHoy, k.zPlan, fEnt)}
      ${fila('Lineales con zona Z', k.linZHoy, k.linZPlan, fEnt)}
      ${fila('Z: metros medios a expedición', k.mZHoy, k.mZPlan, v => esp(v), true, ' m')}
      ${fila('0: metros medios a expedición', k.m0Hoy, k.m0Plan, v => esp(v), true, ' m')}
      <div class="kpi"><div class="e">Posiciones libres</div><div class="v">${fEnt(k.libres)}</div><div class="d">${k.linLibres} lineales enteros</div></div>
      ${fila('Posiciones de zona 0', k.ceroHoy, k.ceroPlan, fEnt)}
    </div>
    <p class="nota" style="margin:8px 0 0">El plan es la hoja «Layout compactado Z5+01» del Excel del 06/11: no se ha probado ni recalculado.
    «Hoy» es Odoo del ${D.fecha_datos}. Metros calculados con la geometría de kpi.py. El plan nuevo es la fase 2.</p></div>`);
}

let ORDEN_LISTA = null;
function tarjetaLineales() {
  const capa = VISTAS[0] ? VISTAS[0].capa : 'zona';
  const m = NUM_POR_ID[capa] && NUM_POR_ID[capa].lin ? NUM_POR_ID[capa] : NUM_POR_ID.disp;
  const filas = Object.entries(LIN).filter(([l]) => !l.startsWith('MU')).map(([l, d]) => ({ l, v: d[m.lin] }))
    .filter(f => f.v != null).sort((a, b) => b.v - a.v);
  const max = d3.max(filas, f => f.v) || 1;
  const [a, b] = d3.extent(filas, f => f.v);
  const t = el(`<div class="tarjeta"><h4>Lineales<span class="der" style="text-transform:none;letter-spacing:0">${m.titulo}</span></h4><ul class="lista" id="lista-lineales"></ul></div>`);
  const ul = t.querySelector('ul');
  filas.forEach(f => {
    const li = el(`<li data-l="${f.l}"><span><b>${f.l}</b></span><span class="barra"><i style="width:${(f.v / max) * 100}%;background:${COL.secuencial(b > a ? (f.v - a) / (b - a) : 0.5)}"></i></span><span class="num">${m.fmt(f.v)}</span></li>`);
    li.onmouseenter = () => { hoverLineal = f.l; dibujarTodo(); };
    li.onmouseleave = () => { hoverLineal = null; dibujarTodo(); };
    li.onclick = () => abrirAlzado(f.l);
    ul.append(li);
  });
  return t;
}
function marcarListaLineal() {
  const ul = $('#lista-lineales');
  if (!ul) return;
  ul.querySelectorAll('li.activo').forEach(li => li.classList.remove('activo'));
  if (!hoverLineal) return;
  const li = ul.querySelector(`li[data-l="${hoverLineal}"]`);
  if (li) {
    li.classList.add('activo');
    // Solo se desplaza la lista (scrollIntoView movía también la página y el plano).
    const arriba = li.offsetTop - ul.offsetTop, abajo = arriba + li.offsetHeight;
    if (arriba < ul.scrollTop) ul.scrollTop = arriba;
    else if (abajo > ul.scrollTop + ul.clientHeight) ul.scrollTop = abajo - ul.clientHeight;
  }
}

// =============================================================================================== alzado y hueco

async function abrirAlzado(l, sinAnimar_, hueco) {
  const ps = POS.filter(p => p.l === l);
  if (!ps.length) return;
  const huecoURL = hueco || (sinAnimar_ && E.lineal === l ? E.hueco : null);   // al recargar se conserva el hueco
  E.nivel = 'lineal'; E.lineal = l; E.hueco = huecoURL;
  ocultarTip();
  if (!sinAnimar_ && VISTAS[0]) await encuadrar(cajaDe(ps), 520);
  pintarMigas(); pintarPanel(); pintarLeyenda();
  $('#alzado').style.transition = sinAnimar() || sinAnimar_ ? 'none' : '';
  dibujarAlzado(!sinAnimar_);
  $('#alzado').classList.add('visible');
  guardarURL();
}
function cerrarAlzado() {
  E.nivel = 'nave'; const l = E.lineal; E.lineal = null; E.hueco = null;
  $('#alzado').style.transition = sinAnimar() ? 'none' : '';
  $('#alzado').classList.remove('visible');
  pintarMigas(); pintarPanel(); pintarLeyenda(); guardarURL();
  if (l) { hoverLineal = null; dibujarTodo(); }
}
function cajaDe(ps) {
  return { x0: d3.min(ps, p => p.x0), x1: d3.max(ps, p => p.x1), y0: d3.min(ps, p => p.y0), y1: d3.max(ps, p => p.y1) };
}

function dibujarAlzado(fundido) {
  const caja = $('#alzado');
  const W = caja.clientWidth, H = caja.clientHeight;
  if (!W || !E.lineal) return;
  const ps = POS.filter(p => p.l === E.lineal).sort((a, b) => a.p - b.p);
  const capa = E.modo === 'plan' ? 'plan' : 'zona';
  const tramos = [
    { t: 'Al otro lado del pasillo central · P18 en adelante', ps: ps.filter(p => p.p >= 18) },
    { t: 'Lado de expedición · P00–P17', ps: ps.filter(p => p.p <= 17) },
  ].filter(tr => tr.ps.length);
  const l = LIN[E.lineal] || {};
  // Niveles tal como existen en Odoo (de arriba abajo); una casilla rayada es un nivel que esa posición no tiene.
  const NIVELES = [...new Set(ps.flatMap(p => p.niv.map(n => n[0])))].sort((a, b) => b - a);
  const nNiv = NIVELES.length || 1;
  const ml = 56, mr = 24, top = 122, entre = 48, abajo = 30;
  const maxCols = d3.max(tramos, tr => tr.ps.length);
  const cw = Math.min(86, (W - ml - mr - 20) / maxCols);
  const desplaza = Math.max(0, (W - ml - mr - cw * maxCols) / 2);
  const altoTramo = Math.min(nNiv * 52 + 40, (H - top - abajo - entre * (tramos.length - 1)) / tramos.length);
  const ch = (altoTramo - 40) / nNiv;

  const svg = d3.select(caja).selectAll('svg').data([0]).join('svg');
  svg.selectAll('*').remove();
  // cabecera
  const cab = svg.append('g').attr('transform', `translate(${ml + desplaza},34)`);
  miniNave(svg, W - mr - 190, 14, 190, 70);
  cab.append('text').text(E.lineal).attr('font-size', 26).attr('font-weight', 700).attr('fill', COL['--texto']);
  cab.append('text').attr('x', 80).attr('y', -6).attr('font-size', 12).attr('fill', COL['--texto-2'])
    .text(`Lineal en alzado · color: ${capa === 'plan' ? 'zona en el plan Z5+01 (estimación 06/11, por posición)' : 'zona de hoy de cada hueco (Odoo)'}`);
  cab.append('text').attr('x', 80).attr('y', 11).attr('font-size', 12).attr('fill', COL['--texto-2'])
    .text(`${fEnt(l.ocupadas)} de ${fEnt(l.posiciones)} posiciones con stock · ${fEnt(l.uds)} uds · ${fEnt(l.contenedores)} contenedores · ${fEnt(l.modelos_color)} modelos-color · ${fEnt(l.ubicaciones)} huecos en Odoo`);
  cab.append('text').attr('x', 0).attr('y', 40).attr('font-size', 11.5).attr('fill', COL['--texto-3'])
    .text(`Niveles tal como existen en Odoo (${NIVELES.map(n => 'C' + n).join(', ')}). En cada hueco: unidades y contenedores. Rayado: el nivel no existe en esa posición.`);
  cab.append('text').attr('x', 0).attr('y', 55).attr('font-size', 11.5).attr('fill', COL['--texto-3'])
    .text('Banda dorada: C2–C3, altura cómoda (supuesto: C1 abajo).');

  tramos.forEach((tr, g) => {
    const y0 = top + g * (altoTramo + entre);
    const gt = svg.append('g').attr('transform', `translate(${ml + desplaza},${y0})`);
    gt.append('text').text(tr.t).attr('font-size', 12).attr('font-weight', 600).attr('fill', COL['--texto-2']).attr('y', -10);
    // banda de altura cómoda
    gt.append('rect').attr('x', -6).attr('y', ch * 1 - 3).attr('width', tr.ps.length * cw + 12).attr('height', ch * 2 + 6)
      .attr('rx', 8).attr('fill', COL['--oro']).attr('opacity', 0.14);
    NIVELES.forEach((n, j) => gt.append('text').text('C' + n).attr('x', -14).attr('y', j * ch + ch / 2 + 4)
      .attr('text-anchor', 'end').attr('font-size', 11).attr('fill', COL['--texto-3']));
    tr.ps.forEach((p, k) => {
      gt.append('text').text('P' + pad(p.p)).attr('x', k * cw + cw / 2).attr('y', 4 * ch + 15).attr('text-anchor', 'middle')
        .attr('font-size', 11).attr('font-weight', 600).attr('fill', COL['--texto-2']);
      if (p.m != null && cw > 40) gt.append('text').text(fM(p.m)).attr('x', k * cw + cw / 2).attr('y', 4 * ch + 28)
        .attr('text-anchor', 'middle').attr('font-size', 9.5).attr('fill', COL['--texto-3']);
      NIVELES.forEach((n, j) => {
        const sel = E.hueco && E.hueco.p === p.p && E.hueco.n === n;
        const h = p.niv.find(x => x[0] === n);    // [nivel, zona, uds, cont. con stock, cont. activos, modelos-color, visitas, litros]
        const c = gt.append('g').attr('class', 'celda').attr('transform', `translate(${k * cw + 2},${j * ch + 2})`)
          .style('opacity', 0);
        if (!h) {
          c.append('rect').attr('width', cw - 4).attr('height', ch - 4).attr('rx', 5).attr('fill', 'none')
            .attr('stroke', COL['--linea-fuerte']).attr('stroke-dasharray', '3 3');
          if (sinAnimar() || !fundido) c.style('opacity', 1); else c.transition().delay(k * 9 + j * 14).duration(260).style('opacity', 1);
          return;
        }
        const zonaH = h[1];
        const color = capa === 'plan' ? colorDe(p, 'plan') : capaColor('zona', zonaH);
        const busc = resaltar && !resaltar.has(p.i);
        c.append('rect').attr('class', 'fondo').attr('width', cw - 4).attr('height', ch - 4).attr('rx', 5)
          .attr('fill', color).attr('opacity', busc ? 0.2 : 1)
          .attr('stroke', sel ? COL['--texto'] : 'none').attr('stroke-width', sel ? 3 : 0);
        if (cw > 40 && ch > 22) {
          const oscuro = ['0', 'Z', 'M', 'muelle'].includes(capa === 'plan' ? p.plan : zonaH);
          const col = oscuro ? '#fff' : COL['--texto-2'];
          c.append('text').text(h[2] ? fEnt(h[2]) : `C${n}`).attr('x', (cw - 4) / 2).attr('y', (ch - 4) / 2 + (ch > 38 ? -1 : 4))
            .attr('text-anchor', 'middle').attr('font-size', 11.5).attr('font-weight', 700).attr('fill', col).attr('pointer-events', 'none');
          if (ch > 38 && h[2]) c.append('text').text(`${h[3]} cont.`).attr('x', (cw - 4) / 2).attr('y', (ch - 4) / 2 + 12)
            .attr('text-anchor', 'middle').attr('font-size', 9.5).attr('fill', col).attr('opacity', 0.85).attr('pointer-events', 'none');
        }
        c.on('mouseenter', ev => mostrarTip(ev, `<div class="t"><i style="background:${color}"></i>${nombreHueco(p)} C${n}</div>
            <dl><dt>Zona hoy</dt><dd>${CAT.zona.nombre[zonaH]}</dd><dt>Unidades</dt><dd>${fEnt(h[2])}</dd>
            <dt>Contenedores</dt><dd>${fEnt(h[3])} con stock${h[4] > h[3] ? ` · ${h[4] - h[3]} a cero` : ''}</dd>
            <dt>Modelos-color</dt><dd>${fEnt(h[5])}</dd><dt>Visitas (4 sem.)</dt><dd>${fEnt(h[6])}</dd>
            <dt>Litros</dt><dd>${fEnt(h[7])}</dd>
            <dt>Plan (est. 06/11)</dt><dd>${CAT.plan.nombre[p.plan]}</dd><dt>A expedición</dt><dd>${p.m != null ? fM(p.m) : '—'}</dd></dl>`))
          .on('mousemove', ev => mostrarTip(ev, $('#tip').innerHTML))
          .on('mouseleave', ocultarTip)
          .on('click', () => { E.hueco = { p: p.p, n, i: p.i }; pintarMigas(); pintarPanel(); dibujarAlzado(); guardarURL(); });
        if (sinAnimar() || !fundido) c.style('opacity', 1);
        else c.transition().delay(k * 9 + j * 14).duration(260).style('opacity', 1);
      });
    });
  });
}

/** Plano en miniatura con el lineal abierto marcado: para no perder dónde se está. */
function miniNave(svg, x, y, w, h) {
  const g = svg.append('g').attr('transform', `translate(${x},${y})`);
  const sxm = d3.scaleLinear().domain([NAVE.x0, NAVE.x1]).range([0, w]);
  const sym = d3.scaleLinear().domain([NAVE.y0, NAVE.y1]).range([h, 0]);
  g.append('rect').attr('width', w).attr('height', h).attr('rx', 6).attr('fill', COL['--suelo']).attr('stroke', COL['--linea-fuerte']);
  const porLineal = d3.group(POS.filter(p => !p.muelle), p => p.l);
  for (const [l, ps] of porLineal) {
    const actual = l === E.lineal;
    g.append('rect').attr('x', sxm(d3.min(ps, p => p.x0)) - (actual ? 1 : 0)).attr('width', actual ? 3 : 0.9)
      .attr('y', sym(d3.max(ps, p => p.y1))).attr('height', sym(d3.min(ps, p => p.y0)) - sym(d3.max(ps, p => p.y1)))
      .attr('fill', actual ? COL['--acento'] : COL['--linea-fuerte']);
  }
  const [bx0, by0] = D.geometria.base;
  g.append('circle').attr('cx', sxm(bx0) + 3).attr('cy', sym(by0)).attr('r', 3).attr('fill', COL['--texto']);
  g.append('text').text('dónde está').attr('x', w).attr('y', h + 13).attr('text-anchor', 'end').attr('font-size', 10).attr('fill', COL['--texto-3']);
}

function panelLineal() {
  const l = LIN[E.lineal] || {};
  const out = [];
  if (E.hueco) {
    const p = POS[E.hueco.i] || POS[IDX.get(E.lineal + '|' + E.hueco.p)];
    const h = p.niv.find(x => x[0] === E.hueco.n) || [E.hueco.n, 'vacía', 0, 0, 0, 0, 0, 0];
    out.push(el(`<div class="tarjeta"><h4>Hueco</h4>
      <div class="fijada"><h5><i style="background:${capaColor('zona', h[1])}"></i>${nombreHueco(p)} C${E.hueco.n}</h5>
      <div class="datos"><span>Zona hoy</span><span>${CAT.zona.nombre[h[1]]}</span>
      <span>Unidades · litros</span><span>${fEnt(h[2])} · ${fEnt(h[7])}</span>
      <span>Contenedores con stock · a cero</span><span>${fEnt(h[3])} · ${fEnt(h[4] - h[3])}</span>
      <span>Modelos-color</span><span>${fEnt(h[5])}</span>
      <span>Visitas de picking (4 sem.)</span><span>${fEnt(h[6])}</span>
      <span>A expedición</span><span>${p.m != null ? fM(p.m) : '—'}</span>
      <span>Plan (est. 06/11, posición)</span><span>${CAT.plan.nombre[p.plan]}</span></div></div></div>`));
    const t = el(`<div class="tarjeta"><h4>Qué hay dentro<span class="der" style="text-transform:none;letter-spacing:0">Odoo ${D.fecha_datos}</span></h4>
      <p class="nota" style="margin:0">Cargando…</p></div>`);
    out.push(t);
    const clave = `${p.l}|${p.p}|${E.hueco.n}`;
    cargarHuecos().then(H => pintarContenido(t, H[clave], clave)).catch(e => { t.querySelector('.nota').textContent = 'No se ha podido leer huecos.json: ' + e.message; });
  } else out.push(el(`<div class="tarjeta"><p class="nota" style="margin:0">Toca un hueco del alzado para ver qué hay dentro. <kbd>Esc</kbd> vuelve a la nave.</p></div>`));
  out.push(el(`<div class="tarjeta"><h4>${E.lineal} entero <span class="der" style="text-transform:none;letter-spacing:0">Odoo ${D.fecha_datos}</span></h4>
    <div class="kpis">
      <div class="kpi"><div class="v">${fPct(l.pct_ocupacion)}</div><div class="e">posiciones con stock</div></div>
      <div class="kpi"><div class="v">${fEnt(l.uds)}</div><div class="e">unidades</div></div>
      <div class="kpi"><div class="v">${l.dispersion != null ? fDec(l.dispersion) : '—'}</div><div class="e">lineales por modelo-color (media)</div></div>
      <div class="kpi"><div class="v">${fEnt(l.visitas)}</div><div class="e">visitas de picking (4 sem.)</div></div>
    </div>
    <div class="datos">
      <span>Zona del lineal</span><span>${CAT.zona.nombre[l.zona] || '—'}</span>
      <span>Uds zona 0 / Z</span><span>${fEnt(l.uds_0)} / ${fEnt(l.uds_z)}</span>
      <span>SKU · modelos-color</span><span>${fEnt(l.sku)} · ${fEnt(l.modelos_color)}</span>
      <span>Contenedores con stock</span><span>${fEnt(l.contenedores)}</span>
      <span>Litros (parte estimada)</span><span>${fEnt(l.litros)}</span>
      <span>Huecos en Odoo</span><span>${fEnt(l.ubicaciones)}</span>
      <span class="sub">Temporadas principales (uds)</span><span hidden></span>
      <span style="grid-column:1/-1;text-align:left;font-weight:400">${(l.temporadas || '—').replace(/ /g, ' · ')}</span>
    </div></div>`));
  return out;
}

/** Contenedores del hueco con sus modelos-color, tallas y unidades (huecos.json). */
function pintarContenido(t, h, clave) {
  const nota = t.querySelector('.nota');
  if (!h || (!h.c.length && !h.s.length && !h.v0.length)) { nota.textContent = 'Vacío: no hay stock ni contenedores.'; return; }
  nota.remove();
  const filas = [];
  h.c.forEach(([nombre, uds, mcs]) => mcs.forEach(([mc, tallas, u], k) => filas.push(
    `<tr><td>${k ? '' : `<b>${nombre}</b>`}</td><td><a href="#" data-mc="${mc}">${mc}</a></td><td>${tallas}</td><td class="n">${fEnt(u)}</td></tr>`)));
  h.s.forEach(([mc, tallas, u]) => filas.push(`<tr><td class="nota">suelto</td><td><a href="#" data-mc="${mc}">${mc}</a></td><td>${tallas}</td><td class="n">${fEnt(u)}</td></tr>`));
  const total = d3.sum(h.c, c => c[1]) + d3.sum(h.s, s => s[2]);
  t.append(el(`<div><table class="cont"><thead><tr><th>Contenedor</th><th>Modelo-color</th><th>Tallas (uds)</th><th class="n">Uds</th></tr></thead>
    <tbody>${filas.join('')}</tbody><tfoot><tr><th colspan="3">Total · ${h.c.length} contenedores</th><th class="n">${fEnt(total)}</th></tr></tfoot></table>
    ${h.v0.length ? `<p class="nota" style="margin:8px 0 0"><b>${h.v0.length} contenedores a cero sin archivar:</b> ${h.v0.slice(0, 12).join(', ')}${h.v0.length > 12 ? '…' : ''}</p>` : ''}
    <p class="nota" style="margin:6px 0 0">Clic en un modelo-color: dónde más está.</p></div>`));
  t.querySelectorAll('a[data-mc]').forEach(a => a.onclick = ev => { ev.preventDefault(); $('#buscar').value = a.dataset.mc; cerrarAlzado(); buscar(a.dataset.mc); });
}

// =============================================================================================== migas, buscador, teclas
function pintarMigas() {
  const n = $('#migas');
  n.innerHTML = '';
  const boton = (t, f, actual) => { const b = document.createElement('button'); b.textContent = t; if (actual) b.setAttribute('aria-current', 'page'); else b.onclick = f; return b; };
  const sep = () => { const s = document.createElement('span'); s.className = 'sep'; s.textContent = '›'; return s; };
  n.append(boton('Nave', cerrarAlzado, E.nivel === 'nave'));
  if (E.nivel === 'lineal') {
    n.append(sep(), boton(E.lineal, () => { E.hueco = null; pintarMigas(); pintarPanel(); dibujarAlzado(); guardarURL(); }, !E.hueco));
    if (E.hueco) n.append(sep(), boton(`P${pad(E.hueco.p)} C${E.hueco.n}`, null, true));
  }
}

function buscar(txt, sinMover) {
  E.busqueda = txt;
  const t = txt.trim().toUpperCase();
  resaltar = null; resaltarEjemplo = false; modeloBuscado = null;
  let m, set = new Set();
  if (!t) { /* nada */ }
  else if (MODELOS[t] || Object.keys(MODELOS).some(mc => mc.startsWith(t + '-'))) {
    // modelo-color exacto, o un modelo con todos sus colores
    modeloBuscado = t;
    huecosDeModelo(t).huecos.forEach(([k]) => { const [l, p] = k.split('|'); const j = IDX.get(l + '|' + p); if (j != null) set.add(j); });
  }
  else if ((m = t.match(/^L?\s*(\d{1,3})(?:\s*[- ]\s*P?\s*(\d{1,2}))?$/))) {
    const l = 'L' + pad(parseInt(m[1], 10));
    POS.forEach(p => { if (p.l === l && (m[2] == null || p.p === parseInt(m[2], 10))) set.add(p.i); });
  } else if ((m = t.match(/^MU-?(\d{1,2})$/))) {
    POS.forEach(p => { if (p.l === 'MU-' + pad(+m[1])) set.add(p.i); });
  } else if (/^([IV]\d{2}|PERMANENTE)$/.test(t)) {
    // lineales donde la temporada está entre las 4 primeras (por unidades)
    const ls = new Set(Object.keys(LIN).filter(l => (LIN[l].temporadas || '').split(' ').some(s => s.startsWith(t + ':'))));
    POS.forEach(p => { if (ls.has(p.l)) set.add(p.i); });
  } else if (t.length >= 4) {
    // trozo de modelo: el primer modelo-color que lo contiene
    const k = Object.keys(MODELOS).find(x => x.includes(t));
    if (k) return buscar(k, sinMover);
  }
  if (t) resaltar = set;
  refrescarTodo(); guardarURL(); arrancarAnimacion();
  if (!sinMover && set.size && E.nivel === 'nave') encuadrar(cajaDe([...set].map(i => POS[i])), 600);
}

function teclas(ev) {
  if (ev.target.matches('input, select')) { if (ev.key === 'Escape') ev.target.blur(); return; }
  if (ev.key === 'Escape' && !$('#listas').classList.contains('oculto')) { cerrarListas(); return; }
  if (ev.key === 'Escape') {
    if (E.nivel === 'lineal' && E.hueco) { E.hueco = null; pintarMigas(); pintarPanel(); dibujarAlzado(); guardarURL(); }
    else if (E.nivel === 'lineal') cerrarAlzado();
    else if (E.seleccion || E.fijadas.length || E.flecha != null) { E.seleccion = null; E.fijadas = []; E.flecha = null; pintarPanel(); dibujarTodo(); guardarURL(); }
  } else if (ev.key === 'Enter' && E.nivel === 'nave' && E.fijadas.length) abrirAlzado(POS[E.fijadas[E.fijadas.length - 1]].l);
  else if (ev.key === '0' && E.nivel === 'nave') encuadrar(null);
}

// =============================================================================================== estado, URL y refresco
function refrescarTodo() {
  VISTAS.forEach(w => { if (!w.anim) { w.cols = coloresObjetivo(w.capa); w.cols2 = w.capa2 ? coloresObjetivo(w.capa2) : null; } });
  redimensionar();
  pintarLeyenda(); pintarPanel(); pintarMigas();
  if (E.nivel === 'lineal') dibujarAlzado();
  guardarURL();
}

function pintarEstado() {
  const w = VISTAS[0];
  if (!w) return;
  const visibles = POS.filter(p => (!resaltar || resaltar.has(p.i)) && encendida(p, w.capa)).length;
  $('#estado').innerHTML = `<span><b>Datos reales</b> · Odoo ${D.fecha_datos} · copia ${D.fuente}</span>
    <span>${fEnt(visibles)} de ${fEnt(POS.length)} posiciones encendidas</span>
    <span>zoom ×${esp(T.k, 1)} · ${esp(pxm(w), 1)} px/m</span>
    ${E.flechas || resaltarEjemplo ? '<span class="ej">HAY DATOS DE EJEMPLO EN PANTALLA</span>' : ''}
    <span style="margin-left:auto"><kbd>clic</kbd> fijar · <kbd>doble clic</kbd> acercar · <kbd>Mayús</kbd>+arrastrar seleccionar · <kbd>Esc</kbd> subir · <kbd>0</kbd> toda la nave</span>`;
}

let temporizadorURL = null;
function guardarURL() {
  clearTimeout(temporizadorURL);
  temporizadorURL = setTimeout(() => {
    const q = new URLSearchParams();
    q.set('modo', E.modo); q.set('medida', E.medida);
    if (E.contorno) q.set('limite', '1');
    if (E.oro) q.set('oro', '1');
    if (E.flechas) q.set('mov', '1');
    if (E.tema !== 'claro') q.set('tema', E.tema);
    if (!E.panel) q.set('panel', '0');
    if (E.nivel === 'lineal') q.set('lineal', E.lineal);
    if (E.hueco) q.set('hueco', E.hueco.p + '-' + E.hueco.n);
    if (E.fijadas.length) q.set('fijadas', E.fijadas.map(i => POS[i].l + '-' + POS[i].p).join(','));
    if (E.modo === 'cortina') q.set('cortina', E.cortina.toFixed(3));
    if (E.busqueda) q.set('buscar', E.busqueda);
    Object.entries(E.apagadas).forEach(([k, s]) => { if (s.size) q.set('apagadas_' + k, [...s].join('|')); });
    Object.entries(E.rango).forEach(([k, r]) => q.set('rango_' + k, r.map(v => +v.toFixed(4)).join('_')));
    if (medidaValida(VISTAS[0])) { const e = encuadreActual(VISTAS[0]); q.set('vista', [e.cx, e.cy, e.pxm].map(v => v.toFixed(2)).join('_')); }
    history.replaceState(null, '', '#' + q.toString());
  }, 250);
}

function leerURL() {
  const q = new URLSearchParams(location.hash.slice(1));
  if (!q.toString()) return;
  const modos = ['hoy', 'plan', 'cortina', 'lado', 'dif'];
  if (modos.includes(q.get('modo'))) E.modo = q.get('modo');
  if (q.get('medida') && (q.get('medida') === 'zona' || NUM_POR_ID[q.get('medida')])) E.medida = q.get('medida');
  E.contorno = q.get('limite') === '1'; E.oro = q.get('oro') === '1'; E.flechas = q.get('mov') === '1';
  if (q.get('tema') === 'oscuro') E.tema = 'oscuro';
  if (q.get('panel') === '0') E.panel = false;
  if (q.get('lineal') && LIN[q.get('lineal')]) { E.nivel = 'lineal'; E.lineal = q.get('lineal'); }
  if (q.get('hueco') && E.lineal) {
    const [p, n] = q.get('hueco').split('-').map(Number);
    const i = IDX.get(E.lineal + '|' + p);
    if (i != null) E.hueco = { p, n, i };
  }
  if (q.get('fijadas')) E.fijadas = q.get('fijadas').split(',').map(s => { const [l, p] = s.split('-'); return IDX.get(l + '|' + p); }).filter(i => i != null).slice(0, 2);
  if (q.get('cortina')) E.cortina = Math.max(0.02, Math.min(0.98, +q.get('cortina')));
  if (q.get('buscar')) E.busqueda = q.get('buscar');
  for (const [k, v] of q.entries()) {
    if (k.startsWith('apagadas_')) E.apagadas[k.slice(9)] = new Set(v.split('|'));
    if (k.startsWith('rango_') && NUM_POR_ID[k.slice(6)]) E.rango[k.slice(6)] = v.split('_').map(Number);
  }
  if (q.get('vista')) {
    const [cx, cy, p] = q.get('vista').split('_').map(Number);
    // El centro guardado nunca puede quedar fuera de la nave (si no, se abre en blanco).
    if ([cx, cy, p].every(Number.isFinite)) E._vista = { cx: Math.max(NAVE.x0, Math.min(NAVE.x1, cx)),
      cy: Math.max(NAVE.y0, Math.min(NAVE.y1, cy)), pxm: p };
  }
}

// Se aplica el encuadre de la URL cuando ya hay vistas medidas.
const _ponerModo = ponerModo;
ponerModo = function (modo, inicial) {
  _ponerModo(modo, inicial);
  if (inicial && E._vista) { redimensionar(); dibujarTodo(); }
};

// =============================================================================================== PNG
async function guardarPNG() {
  const fecha = new Date();
  const sello = `${fecha.getFullYear()}${pad(fecha.getMonth() + 1)}${pad(fecha.getDate())}_${pad(fecha.getHours())}${pad(fecha.getMinutes())}`;
  let lienzo;
  if (E.nivel === 'lineal') {
    const svg = $('#alzado svg');
    const xml = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    await new Promise(r => { img.onload = r; img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml); });
    const dpr = 2;
    lienzo = document.createElement('canvas'); lienzo.width = svg.clientWidth * dpr; lienzo.height = svg.clientHeight * dpr;
    const c = lienzo.getContext('2d'); c.fillStyle = COL['--plano']; c.fillRect(0, 0, lienzo.width, lienzo.height);
    c.drawImage(img, 0, 0, lienzo.width, lienzo.height);
  } else {
    const r = $('#vistas').getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    lienzo = document.createElement('canvas'); lienzo.width = r.width * dpr; lienzo.height = r.height * dpr;
    const c = lienzo.getContext('2d');
    VISTAS.forEach(w => { const q = w.el.getBoundingClientRect(); c.drawImage(w.canvas, (q.left - r.left) * dpr, (q.top - r.top) * dpr); });
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    const titulo = { hoy: (NUM_POR_ID[E.medida] || { titulo: 'Zona hoy' }).titulo, plan: 'Plan Z5+01', cortina: 'Hoy | plan Z5+01',
      lado: 'Hoy y plan Z5+01', dif: 'Diferencia hoy → plan Z5+01' }[E.modo];
    const plan = ['plan', 'cortina', 'lado', 'dif'].includes(E.modo) ? ' · plan = estimación del 06/11' : '';
    texto(c, `NAU-2 · ${titulo} · Odoo ${D.fecha_datos}${plan}${E.flechas ? ' · con DATOS DE EJEMPLO' : ''}`, 14, r.height - 12,
      { color: COL['--texto-2'], tam: 12, peso: 600, fondo: true });
  }
  const a = document.createElement('a');
  a.href = lienzo.toDataURL('image/png');
  a.download = `mapa-nau2_${E.nivel === 'lineal' ? E.lineal : E.modo}_${sello}.png`;
  a.click();
}

// =============================================================================================== listas
const LISTAS_DEF = [
  { id: 1, titulo: '1 · Modelos repartidos', ayuda: 'Cada modelo-color, de más a menos lineales, con sus huecos y unidades. Clic: verlo en el plano.' },
  { id: 2, titulo: '2 · Contenedores a cero', ayuda: 'Contenedores activos sin stock (sin archivar), por hueco. Clic: abrir el hueco.' },
  { id: 3, titulo: '3 · Huecos con 0 y Z', ayuda: 'Huecos con unidades de las dos zonas (cualquier cantidad), de más a menos mezclados. Clic: abrir el hueco.' },
  { id: 4, titulo: '4 · Sin salidas en N días', ayuda: 'Stock por referencia cuya última orden de entrega es más antigua que N días (o no tiene ninguna en el histórico). Clic: dónde está su modelo-color.' },
  { id: 5, titulo: '5 · Pendiente de ubicar', ayuda: 'Stock de NAVE2 que no está en un hueco: contenedores colgados de la nave, muelle sin hueco, N1-, perchas…' },
];
const LI = { n: 1, filtro: '', dias: 90, minLin: 2 };

function filasLista(n) {
  const f = LI.filtro.trim().toUpperCase();
  const pasa = r => !f || r.some(c => String(c).toUpperCase().includes(f));
  if (n === 1) {
    const cols = ['Modelo-color', 'Lineales', 'Huecos', 'Uds', 'Zona', 'Huecos (uds)'];
    const filas = Object.entries(MODELOS).filter(([, v]) => v[0] >= LI.minLin)
      .sort((a, b) => b[1][0] - a[1][0] || b[1][2] - a[1][2])
      .map(([mc, v]) => [mc, v[0], v[1], v[2], v[3], v[4].map(([k, u]) => `${textoClave(k)}: ${u}`).join(' · ')]).filter(pasa);
    return { cols, filas };
  }
  const L = LISTAS['l' + n];
  let filas = L.filas;
  if (n === 4) {
    const corte = new Date(D.fecha_datos.split(' ')[0].split('/').reverse().join('-'));
    corte.setDate(corte.getDate() - LI.dias);
    const c = corte.toISOString().slice(0, 10);
    filas = filas.filter(r => !r[8] || r[8] < c);
  }
  return { cols: L.cols, filas: filas.filter(pasa) };
}

async function abrirListas(n) {
  if (n) LI.n = n;
  const caja = $('#listas');
  caja.classList.remove('oculto');
  caja.querySelector('.cuerpo-lista').innerHTML = '<p class="nota">Cargando listas…</p>';
  await cargarListas();
  pintarListas();
}
function cerrarListas() { $('#listas').classList.add('oculto'); }

function pintarListas() {
  const caja = $('#listas');
  const pest = caja.querySelector('.pestanas');
  pest.innerHTML = '';
  LISTAS_DEF.forEach(d => {
    const b = document.createElement('button');
    b.textContent = d.titulo; b.setAttribute('aria-pressed', String(d.id === LI.n));
    b.onclick = () => { LI.n = d.id; pintarListas(); };
    pest.append(b);
  });
  const def = LISTAS_DEF.find(d => d.id === LI.n);
  const { cols, filas } = filasLista(LI.n);
  const MAX = 400;
  const cuerpo = caja.querySelector('.cuerpo-lista');
  const numerica = cols.map((_, j) => filas.slice(0, 50).every(r => typeof r[j] === 'number'));
  cuerpo.innerHTML = `<div class="filtros">
      <input type="search" class="control" id="l-filtro" placeholder="Filtrar (texto en cualquier columna)" value="${LI.filtro.replace(/"/g, '&quot;')}">
      ${LI.n === 4 ? `<label class="nota">N = <input type="number" class="control" id="l-dias" min="1" max="400" value="${LI.dias}" style="width:76px"> días</label>` : ''}
      ${LI.n === 1 ? `<label class="nota">mín. <input type="number" class="control" id="l-min" min="1" max="50" value="${LI.minLin}" style="width:64px"> lineales</label>` : ''}
      <span class="nota"><b>${fEnt(filas.length)}</b> filas${filas.length > MAX ? ` · se ven ${MAX}; Excel lleva todas` : ''}</span>
      <span class="hueco-flex"></span>
      <button class="boton" id="l-excel">Exportar a Excel</button>
    </div>
    <p class="nota" style="margin:4px 0 8px">${def.ayuda}${LI.n === 4 ? ` Histórico de salidas desde ${LISTAS.dias_historico}.` : ''}</p>
    <div class="tabla-lista"><table class="cont"><thead><tr>${cols.map((c, j) => `<th class="${numerica[j] ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.slice(0, MAX).map((r, i) => `<tr data-i="${i}">${r.map((c, j) => `<td class="${numerica[j] ? 'n' : ''}">${typeof c === 'number' ? (cols[j].startsWith('%') ? fPct(c) : fEnt(c)) : c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const fi = $('#l-filtro');
  fi.oninput = () => { LI.filtro = fi.value; clearTimeout(fi._t); fi._t = setTimeout(() => { pintarListas(); const g = $('#l-filtro'); g.focus(); g.setSelectionRange(g.value.length, g.value.length); }, 250); };
  if ($('#l-dias')) $('#l-dias').onchange = ev => { LI.dias = Math.max(1, +ev.target.value || 90); pintarListas(); };
  if ($('#l-min')) $('#l-min').onchange = ev => { LI.minLin = Math.max(1, +ev.target.value || 2); pintarListas(); };
  $('#l-excel').onclick = () => exportarExcel(def, cols, filas);
  cuerpo.querySelectorAll('tbody tr').forEach(tr => tr.onclick = () => irDesdeLista(LI.n, filas[+tr.dataset.i]));
}

function irDesdeLista(n, r) {
  const abrirHueco = txt => {
    const m = /^(L\d+|MU-\d+) P(\d+) C(\d+)$/.exec(txt || '');
    if (!m) return;
    const i = IDX.get(m[1] + '|' + +m[2]);
    if (i == null) return;
    cerrarListas(); abrirAlzado(m[1], false, { p: +m[2], n: +m[3], i });
  };
  if (n === 1 || n === 4) { cerrarListas(); if (E.nivel === 'lineal') cerrarAlzado(); $('#buscar').value = r[n === 1 ? 0 : 1]; buscar(r[n === 1 ? 0 : 1]); }
  else if (n === 2 || n === 3) abrirHueco(r[n === 2 ? 1 : 0]);
}

function exportarExcel(def, cols, filas) {
  if (typeof XLSX === 'undefined') { alert('No se ha podido cargar la librería de Excel (sin internet).'); return; }
  const hoja = XLSX.utils.aoa_to_sheet([cols, ...filas]);
  hoja['!cols'] = cols.map((c, j) => ({ wch: Math.min(60, Math.max(c.length, ...filas.slice(0, 200).map(r => String(r[j]).length)) + 2) }));
  const libro = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(libro, hoja, def.titulo.replace(/[^\wáéíóúñÁÉÍÓÚÑ ]/g, '').trim().slice(0, 31));
  const f = new Date(), sello = `${f.getFullYear()}${pad(f.getMonth() + 1)}${pad(f.getDate())}_${pad(f.getHours())}${pad(f.getMinutes())}`;
  XLSX.writeFile(libro, `lista${def.id}_${def.titulo.split('·')[1].trim().replace(/\s+/g, '-').toLowerCase()}_${sello}.xlsx`);
}
