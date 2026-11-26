# -*- coding: utf-8 -*-
# KOROSHI - Página HTML del % de faltante (faltante ÷ recibido) por SKU, modelo-color y modelo (v1.0, 26/11/2026).
# Solo lee el fichero de datos de KOROSHI_faltante_relativo_listado_2026-11-26.py (leído de Odoo el 26/11, solo
# lectura) y escribe una página autónoma (sin internet): resumen, explicación, pestañas por nivel, buscador,
# filtro por alerta y por recibido, y columnas ordenables.
# Uso: python -I -X utf8 KOROSHI_faltante_relativo_html_2026-11-26.py <datos.txt> <salida.html>
import json
import sys

ENT, OUT = sys.argv[1:3]
datos = {'sku': [], 'color': [], 'modelo': []}
for lin in open(ENT, encoding='utf-8'):
    p = lin.rstrip('\n').split('|')
    if len(p) < 3:
        continue
    clave = p[1].replace('~', '-0000')
    if p[0] == 's':
        rec, sal, dev, baj, alt, enf, st, f7 = (float(x) for x in p[2:10])
        ult = ('%s/%s' % (p[10][2:], p[10][:2])) if len(p) > 10 and p[10] else ''
        falt = max(baj - alt + enf, 0)
        datos['sku'].append({'k': clave, 'pct': round(falt * 100 / rec, 2), 'falt': falt, 'rec': rec, 'sal': sal,
                             'baj': baj, 'alt': alt, 'enf': enf, 'st': st, 'f7': f7, 'ult': ult})
    else:
        rec, falt, sob, enf, f7, n, nf = (float(x) for x in p[2:9])
        datos['color' if p[0] == 'c' else 'modelo'].append(
            {'k': clave, 'pct': round(falt * 100 / rec, 2), 'falt': falt, 'rec': rec, 'sob': sob, 'enf': enf,
             'f7': f7, 'n': int(n), 'nf': int(nf)})

PAGINA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>% de faltante KOROSHI</title>
<style>
:root{--fondo:#f6f7f9;--papel:#fff;--texto:#1d2433;--suave:#5b6475;--linea:#e3e6eb;--azul:#2f5c9e;
 --crit:#b3261e;--crit-f:#fbe3e1;--alar:#c2570c;--alar-f:#fdebdc;--vig:#8a6d00;--vig-f:#fff4cc}
@media (prefers-color-scheme:dark){:root{--fondo:#14171c;--papel:#1d2128;--texto:#e7e9ee;--suave:#a0a7b4;
 --linea:#2e333c;--azul:#8db4f0;--crit:#ff8a80;--crit-f:#3d1f1d;--alar:#ffb174;--alar-f:#3b2a1c;--vig:#f0d264;--vig-f:#353016}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--texto);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.envoltura{max-width:1180px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:24px;margin:0 0 4px}
.sub{color:var(--suave);margin:0 0 18px}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:18px}
.tarjeta{background:var(--papel);border:1px solid var(--linea);border-radius:10px;padding:14px}
.tarjeta .n{font-size:28px;font-weight:700;line-height:1.1}
.tarjeta .t{color:var(--suave);font-size:13px;margin-top:4px}
.tarjeta.crit .n{color:var(--crit)} .tarjeta.alar .n{color:var(--alar)} .tarjeta.vig .n{color:var(--vig)}
details{background:var(--papel);border:1px solid var(--linea);border-radius:10px;padding:10px 14px;margin-bottom:18px}
summary{cursor:pointer;font-weight:600}
details p,details li{color:var(--suave)}
.barra{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.pestanas{display:flex;gap:4px;background:var(--papel);border:1px solid var(--linea);border-radius:10px;padding:4px}
.pestanas button,.chip{border:0;background:transparent;color:var(--texto);padding:7px 12px;border-radius:7px;font:inherit;cursor:pointer}
.pestanas button.activa{background:var(--azul);color:#fff}
.chip{border:1px solid var(--linea);background:var(--papel)}
.chip.activa{border-color:var(--azul);color:var(--azul);font-weight:600}
input[type=search]{flex:1;min-width:180px;padding:8px 10px;border:1px solid var(--linea);border-radius:8px;background:var(--papel);color:var(--texto);font:inherit}
.cuenta{color:var(--suave);font-size:13px;margin:4px 0 8px}
.tabla{overflow-x:auto;background:var(--papel);border:1px solid var(--linea);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--linea);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{position:sticky;top:0;background:var(--papel);cursor:pointer;user-select:none;font-size:13px;color:var(--suave)}
th.orden{color:var(--azul)}
tr:hover td{background:color-mix(in srgb,var(--azul) 6%,transparent)}
.cod{font-family:ui-monospace,Consolas,monospace;font-size:13px}
.pct{font-weight:700}
.et{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}
.et.crit{background:var(--crit-f);color:var(--crit)} .et.alar{background:var(--alar-f);color:var(--alar)} .et.vig{background:var(--vig-f);color:var(--vig)}
.barrita{display:inline-block;height:6px;border-radius:3px;background:var(--crit);vertical-align:middle;margin-left:6px;opacity:.7}
.nota{background:var(--papel);border:1px solid var(--linea);border-left:4px solid var(--alar);border-radius:10px;padding:10px 14px;margin-top:18px;color:var(--suave)}
.pie{color:var(--suave);font-size:12px;margin-top:18px}
</style>
</head>
<body>
<div class="envoltura">
<h1>% de faltante · KOROSHI</h1>
<p class="sub">Foto del 26/11/2026 · almacén NAU-2 · faltante ÷ recibido, por SKU, modelo-color y modelo</p>

<div class="tarjetas">
 <div class="tarjeta"><div class="n">0,28 %</div><div class="t">Faltante global<br>1.728 uds de 622.909 recibidas</div></div>
 <div class="tarjeta crit"><div class="n" id="t-crit"></div><div class="t">SKU en crítico (≥ 10 %)<br>con 50 uds recibidas o más</div></div>
 <div class="tarjeta alar"><div class="n" id="t-alar"></div><div class="t">SKU en alarma (7–10 %)<br>con 50 uds recibidas o más</div></div>
 <div class="tarjeta"><div class="n" id="t-mod"></div><div class="t">Modelos en alarma o crítico (≥ 7 %)</div></div>
</div>

<details>
 <summary>Cómo se calcula y cómo leerlo</summary>
 <ul>
  <li><b>Faltante</b> de un SKU = lo dado de baja por ajuste − lo dado de alta + lo que está en FALTANTE (no encontrado y sin revisar).</li>
  <li><b>% faltante</b> = faltante ÷ recibido de proveedor. Un SKU al 10 % ha perdido 1 de cada 10 uds recibidas.</li>
  <li>En <b>modelo-color</b> y <b>modelo</b> no se compensan tallas ni colores: lo que sobra en una talla no tapa lo que falta en otra.</li>
  <li><b>Alerta:</b> vigilar desde el 2 %, alarma desde el 7 % (lo revisa el jefe de almacén) y crítico desde el 10 % (lo revisa Isaac).</li>
  <li>Un SKU con muy poco recibido sale muy alto con 1 sola ud (1 de 5 = 20 %). Por eso, de entrada se ven solo los que tienen <b>50 uds recibidas o más</b>; al desmarcar «≥ 50 recibidas» se ven todos.</li>
  <li><b>Faltas 7 días</b> = líneas de pedido de tienda no servidas por falta desde el 19/11.</li>
 </ul>
</details>

<div class="barra">
 <div class="pestanas" id="pestanas">
  <button data-n="sku" class="activa">SKU</button><button data-n="color">Modelo-color</button><button data-n="modelo">Modelo</button>
 </div>
 <button class="chip" data-a="crit">Crítico</button>
 <button class="chip" data-a="alar">Alarma</button>
 <button class="chip" data-a="vig">Vigilar</button>
 <button class="chip activa" id="minimo">≥ 50 recibidas</button>
 <input type="search" id="buscar" placeholder="Buscar SKU o modelo…">
</div>
<div class="cuenta" id="cuenta"></div>
<div class="tabla"><table><thead id="cab"></thead><tbody id="cuerpo"></tbody></table></div>

<div class="nota"><b>Fuera del listado: pack de calcetines 2611UN10-000323.</b> El 29/09 un ajuste quitó exactamente la mitad de lo recibido en todas las tallas (por ejemplo, 581 de 1.162 en la L). Parece un tema de unidades (packs frente a unidades), no un faltante real; se está revisando.</div>
<p class="pie">Fuente: Odoo nath.tuctuc.com (compañía 8), leído el 26/11/2026 por la tarde, solo lectura. Solo SKU, modelo-color y modelos con un 2 % o más. Prendas (códigos NNNNLLNN-…), sin consumibles.</p>
</div>

<script>
const D = __DATOS__;
const n0 = x => Math.round(x).toLocaleString('es-ES');
const n2 = x => x.toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:2});
const al = p => p>=10?'crit':p>=7?'alar':p>=2?'vig':'';
const ET = {crit:'Crítico',alar:'Alarma',vig:'Vigilar'};
const COLS = {
 sku:[['k','SKU'],['pct','% faltante'],['falt','Faltante'],['rec','Recibido'],['sal','Salido'],['baj','Bajas'],['alt','Altas'],['enf','En FALTANTE'],['st','Stock'],['f7','Faltas 7 días'],['ult','Última baja']],
 color:[['k','Modelo-color'],['pct','% faltante'],['falt','Faltante'],['rec','Recibido'],['sob','Sobra en otras tallas'],['enf','En FALTANTE'],['f7','Faltas 7 días'],['nf','SKU con falta'],['n','SKU']],
 modelo:[['k','Modelo'],['pct','% faltante'],['falt','Faltante'],['rec','Recibido'],['sob','Sobra en otras tallas/colores'],['enf','En FALTANTE'],['f7','Faltas 7 días'],['nf','SKU con falta'],['n','SKU']]
};
let nivel='sku', alertas=new Set(), minimo=true, orden=['pct',-1], texto='';
document.getElementById('t-crit').textContent = D.sku.filter(r=>r.rec>=50&&r.pct>=10).length;
document.getElementById('t-alar').textContent = D.sku.filter(r=>r.rec>=50&&r.pct>=7&&r.pct<10).length;
document.getElementById('t-mod').textContent = D.modelo.filter(r=>r.pct>=7).length;
function pintar(){
 const cols=COLS[nivel];
 document.getElementById('cab').innerHTML='<tr>'+cols.map(([c,t])=>`<th data-c="${c}" class="${orden[0]==c?'orden':''}">${t}${orden[0]==c?(orden[1]<0?' ▾':' ▴'):''}</th>`).join('')+'<th>Alerta</th></tr>';
 let filas=D[nivel].filter(r=>(!minimo||r.rec>=50)&&(!alertas.size||alertas.has(al(r.pct)))&&(!texto||r.k.toLowerCase().includes(texto)));
 const [c,s]=orden; filas.sort((a,b)=>(typeof a[c]=='string'?a[c].localeCompare(b[c]):(a[c]-b[c]))*s || b.falt-a.falt);
 document.getElementById('cuenta').textContent=`${filas.length} ${nivel=='sku'?'SKU':nivel=='color'?'modelo-color':'modelos'}`+(minimo?' con 50 uds recibidas o más':'');
 document.getElementById('cuerpo').innerHTML=filas.map(r=>{const a=al(r.pct);return '<tr>'+cols.map(([c])=>{
   if(c=='k') return `<td class="cod">${r.k}</td>`;
   if(c=='pct') return `<td class="pct" style="color:var(--${a=='crit'?'crit':a=='alar'?'alar':'vig'})">${n2(r.pct)} %<span class="barrita" style="width:${Math.min(r.pct,30)*2}px"></span></td>`;
   if(c=='ult') return `<td>${r.ult||''}</td>`;
   return `<td>${n0(r[c])}</td>`;}).join('')+`<td><span class="et ${a}">${ET[a]||''}</span></td></tr>`;}).join('') || `<tr><td colspan="${cols.length+1}" style="text-align:center;color:var(--suave)">Nada con estos filtros.</td></tr>`;
 document.querySelectorAll('#cab th[data-c]').forEach(th=>th.onclick=()=>{const c=th.dataset.c; orden=[c, orden[0]==c?-orden[1]:(c=='k'?1:-1)]; pintar();});
}
document.querySelectorAll('#pestanas button').forEach(b=>b.onclick=()=>{nivel=b.dataset.n; document.querySelectorAll('#pestanas button').forEach(x=>x.classList.toggle('activa',x==b)); minimo=nivel=='sku'; document.getElementById('minimo').classList.toggle('activa',minimo); pintar();});
document.querySelectorAll('.chip[data-a]').forEach(b=>b.onclick=()=>{const a=b.dataset.a; alertas.has(a)?alertas.delete(a):alertas.add(a); b.classList.toggle('activa'); pintar();});
document.getElementById('minimo').onclick=e=>{minimo=!minimo; e.target.classList.toggle('activa',minimo); pintar();};
document.getElementById('buscar').oninput=e=>{texto=e.target.value.trim().toLowerCase(); pintar();};
pintar();
</script>
</body>
</html>
"""
open(OUT, 'w', encoding='utf-8').write(PAGINA.replace('__DATOS__', json.dumps(datos, ensure_ascii=False)))
print('Escrito', OUT, {k: len(v) for k, v in datos.items()})
