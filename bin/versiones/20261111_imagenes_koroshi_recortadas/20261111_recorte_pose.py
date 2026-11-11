import sys, os, glob
from PIL import Image
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
src, dst, modelo = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(dst, exist_ok=True)
det=vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=modelo)))
ARRIBA={'TR','MC','ML','SU','CL','BL','TP','CC','PC','MS','PL','SM','TS','CZ'}
res=[]; BOX={}
for f in sorted(glob.glob(os.path.join(src,'*.jpg'))):
    ref=os.path.basename(f)[:-4]; t=ref[4:6]
    im=Image.open(f).convert('RGB'); W,H=im.size
    def keep(m):
        im.save(os.path.join(dst,ref+'.jpg'),quality=90); res.append((ref,m))
    if t not in ARRIBA|{'JA','PT','PS','FA','VS','VE'}: keep('complemento_sin_recorte'); continue
    r=det.detect(mp.Image.create_from_file(f))
    if not r.pose_landmarks: keep('sin_persona_detectada'); continue
    L=r.pose_landmarks[0]; y=lambda i:L[i].y; x=lambda i:L[i].x
    yS=(y(11)+y(12))/2; yH=(y(23)+y(24))/2; yK=(y(25)+y(26))/2; yA=(y(27)+y(28))/2
    tor=yH-yS; pie=yK-yH
    if t in ARRIBA: a,b=yS-0.30*tor, yH+0.30*tor; xs=[11,12,13,14,23,24]
    elif t=='JA': a,b=yS-0.30*tor, yH+0.55*tor; xs=[11,12,13,14,23,24]
    elif t=='PT': a,b=yH-0.25*pie, yA+0.12*pie; xs=[23,24,25,26,27,28]
    elif t in ('PS','FA'): a,b=yH-0.30*pie, yK+0.45*(yA-yK); xs=[23,24,25,26]
    else: a,b=yS-0.20*tor, yK+0.55*(yA-yK); xs=[11,12,23,24,25,26]
    a=max(0,a); b=min(1,b)
    if b-a<0.25 or b-a>0.97: keep('encuadre_ya_cercano'); continue
    xv=[x(i) for i in xs]; cx=(min(xv)+max(xv))/2
    hpx=(b-a)*H; wpx=max((max(xv)-min(xv))*W*1.6, hpx*0.75)
    l=max(0,int(cx*W-wpx/2)); rr=min(W,int(cx*W+wpx/2))
    BOX[ref]=[round(l/W,4),round(a,4),round(rr/W,4),round(b,4)]
    im.crop((l,int(a*H),rr,int(b*H))).save(os.path.join(dst,ref+'.jpg'),quality=90); res.append((ref,'recortada'))
from collections import Counter
print(Counter(m for _,m in res))
open(os.path.join(dst,'resultado.txt'),'w',encoding='utf-8').write('\n'.join(';'.join(x) for x in res))
import json; json.dump(BOX,open(os.path.join(dst,'boxes.json'),'w'))
