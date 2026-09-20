import numpy as np, os, glob
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
W=860
def load_stack(files):
    ims=[]
    for f in files:
        im=Image.open(f).convert('RGB')
        if im.width!=W: im=im.resize((W,int(im.height*W/im.width)),Image.LANCZOS)
        ims.append(im)
    H=sum(i.height for i in ims); st=Image.new('RGB',(W,H),'white'); y=0; bounds=[]
    for i in ims: st.paste(i,(0,y)); y+=i.height; bounds.append(y)
    return st,bounds
def snap(a,y,r=420):
    H=a.shape[0]; lo=max(1,y-r); hi=min(H-1,y+r)
    rows=a[lo:hi,:,:].reshape(hi-lo,-1).astype(np.float32).std(axis=1)
    return lo+int(np.argmin(rows))
def auto_cuts(st,bounds,target=1800):
    a=np.asarray(st); H=a.shape[0]; cuts=[0]
    b=set(bounds[:-1])
    y=0
    while H-y>target*1.35:
        y_next=y+target
        # 원본 파일 경계가 가까우면 경계를 우선
        near=[x for x in b if y+target*0.6<x<y+target*1.4]
        y=min(near,key=lambda x:abs(x-y_next)) if near else snap(a,y_next)
        cuts.append(y)
    cuts.append(H); return cuts
