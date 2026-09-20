import numpy as np, sys
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS=None
def candidates(stack, size=860, step=215, max_white=0.25):
    """사진처럼 보이는(흰 배경 적고 색 분포가 넓은) 정사각 후보 영역을 찾는다."""
    W,H=stack.size; out=[]
    g=np.asarray(stack.convert('L'),dtype=np.float32)
    a=np.asarray(stack.convert('RGB'),dtype=np.float32)
    for y in range(0,H-size,step):
        w=g[y:y+size]; c=a[y:y+size]
        white=(w>235).mean()
        if white>max_white: continue
        # 텍스트 많은 영역은 가로줄 밝기 변화가 큼 → 행별 표준편차가 큰 행 비율로 근사
        rowstd=w.std(axis=1); txt=((rowstd>60)).mean()
        sat=(c.max(axis=2)-c.min(axis=2)).mean()
        out.append((y,white,txt,sat))
    # 겹침 제거: txt 낮은 순으로
    out.sort(key=lambda t:t[2]); sel=[]
    for y,w,t,s in out:
        if all(abs(y-q)>=size*0.8 for q,_,_,_ in sel): sel.append((y,w,t,s))
    return sorted(sel)
def sheet(stack, cands, out, size=860, tile=220):
    cols=6; rows=(len(cands)+cols-1)//cols
    sh=Image.new('RGB',(cols*tile,rows*(tile+12)),'white'); d=ImageDraw.Draw(sh)
    for i,(y,w,t,s) in enumerate(cands):
        im=stack.crop((0,y,stack.width,y+size)).resize((tile,tile)); x=(i%cols)*tile; yy=(i//cols)*(tile+12)
        sh.paste(im,(x,yy+12)); d.text((x+2,yy),f"{i}:{y}",fill='red')
    sh.save(out)
