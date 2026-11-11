import sys, os, io, csv, urllib.request, concurrent.futures as cf
from PIL import Image
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
S, DST, MODELO = sys.argv[1], sys.argv[2], sys.argv[3]
ORI=os.path.join(S,'ori_antiguas'); os.makedirs(ORI,exist_ok=True); os.makedirs(DST,exist_ok=True)
B='https://cdn.shopify.com/s/files/1/0922/7858/7767/files/'
rows=[l.rstrip('\n').split('\t') for l in open(os.path.join(S,'antiguas.tsv'),encoding='utf-8') if l.strip()]
def bajar(r):
    p=os.path.join(ORI,r[0]+'.jpg')
    if os.path.exists(p): return r[0],None
    try:
        b=urllib.request.urlopen(urllib.request.Request(B+r[1]+'?width=1600',headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read()
        open(p,'wb').write(b); return r[0],None
    except Exception as e: return r[0],str(e)
with cf.ThreadPoolExecutor(6) as ex: errs={k:e for k,e in ex.map(bajar,rows) if e}
print('bajadas', len(rows)-len(errs), 'errores', len(errs), flush=True)
det=vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODELO)))
ARRIBA={'TR','MC','ML','SU','CL','BL','TP','CC','PC','MS','PL','SM','TS','CZ'}
codes=[]; out=[]
for r in rows:
    k=r[0]; t=k[4:6]; p=os.path.join(ORI,k+'.jpg'); res='--------'; modo=''
    if k in errs: modo='error_descarga'
    else:
        im=Image.open(p).convert('RGB'); W,H=im.size; box=None
        if t not in ARRIBA|{'JA','PT','PS','FA','VS','VE'}: modo='complemento_sin_recorte'
        else:
            try: rr=det.detect(mp.Image.create_from_file(p))
            except Exception: rr=None
            if not rr or not rr.pose_landmarks: modo='sin_persona_detectada'
            else:
                L=rr.pose_landmarks[0]; y=lambda i:L[i].y; x=lambda i:L[i].x
                yS=(y(11)+y(12))/2; yH=(y(23)+y(24))/2; yK=(y(25)+y(26))/2; yA=(y(27)+y(28))/2; tor=yH-yS; pie=yK-yH
                if t in ARRIBA: a,b=yS-0.30*tor, yH+0.30*tor; xs=[11,12,13,14,23,24]
                elif t=='JA': a,b=yS-0.30*tor, yH+0.55*tor; xs=[11,12,13,14,23,24]
                elif t=='PT': a,b=yH-0.25*pie, yA+0.12*pie; xs=[23,24,25,26,27,28]
                elif t in ('PS','FA'): a,b=yH-0.30*pie, yK+0.45*(yA-yK); xs=[23,24,25,26]
                else: a,b=yS-0.20*tor, yK+0.55*(yA-yK); xs=[11,12,23,24,25,26]
                a=max(0,a); b=min(1,b)
                need=[11,12,23,24] if t in ARRIBA|{'JA','VS','VE'} else [23,24,25,26]
                vis=all(L[i].visibility>0.6 and 0<=L[i].x<=1 and 0<=L[i].y<=1 for i in need)
                # sentado / pose rara: rodillas casi a la altura de caderas
                if not vis: modo='partes_no_visibles_sin_recorte'
                elif tor<=0 or (t in ('PT','PS','FA','VS','VE') and pie<0.6*tor): modo='pose_rara_sin_recorte'
                elif b-a<0.25 or b-a>0.97: modo='encuadre_ya_cercano'
                else:
                    xv=[x(i) for i in xs]; cx=(min(xv)+max(xv))/2
                    wf=max((max(xv)-min(xv))*1.6,(b-a)*H*0.75/W)
                    l=max(0,cx-wf/2); rgt=min(1,cx+wf/2)
                    box=(l,a,rgt,b); modo='recortada'
        if box:
            q=[min(99,max(0,int(round(v*100)))) for v in box]; res=''.join(f'{v:02d}' for v in q)
            l,a,rgt,b=[v/100 for v in q]; c=im.crop((int(l*W),int(a*H),int(rgt*W),int(b*H)))
        else: c=im
        c.thumbnail((1024,1024)); c.save(os.path.join(DST,k+'.jpg'),quality=85)
    codes.append(res); out.append([k,r[3],B+r[1],(k+'.jpg') if modo!='error_descarga' else '',modo,'https://koroshishop.com/products/'+r[4],r[2],r[5]])
open(os.path.join(S,'boxes_antiguas.txt'),'w').write(''.join(codes))
with open(os.path.join(DST,'20261111_imagenes_koroshi_antiguas.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';'); w.writerow(['referencia','color','url_origen','archivo','recorte','pagina_web','metodo_eleccion','ids_product_template']); w.writerows(out)
from collections import Counter; print(Counter(o[4] for o in out))
