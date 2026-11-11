"""판재 가공 도면: 구멍표 PDF + 1:1 분할 인쇄 PDF + DXF

python cad/tools/drawings.py <cad.py> <출력폴더>
"""
import sys, math, json, importlib.util, os
import cadquery as cq
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager as fm
import ezdxf
# 한글 폰트: 환경변수 HERB_FONT → 알려진 경로 → 시스템 폰트 검색 → 없으면 기본 폰트(한글 깨짐 경고)
FONT_CANDIDATES=[
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",      # Debian/Ubuntu fonts-noto-cjk
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",           # Arch/Fedora
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",                  # macOS
    "C:/Windows/Fonts/malgun.ttf",                                 # Windows 맑은 고딕
]
FONT_NAME_HINTS=("NotoSansCJK","Noto Sans CJK","NotoSansKR","Noto Sans KR","NanumGothic","malgun","AppleSDGothic","AppleGothic")
def pick_font():
    env=os.environ.get("HERB_FONT")
    if env and os.path.exists(env): return env
    for fp in FONT_CANDIDATES:
        if os.path.exists(fp): return fp
    for fp in fm.findSystemFonts():
        if any(h.lower() in os.path.basename(fp).lower().replace(" ","") or h.lower() in fp.lower() for h in FONT_NAME_HINTS):
            return fp
    return None
fp=pick_font()
if fp:
    fm.fontManager.addfont(fp); plt.rcParams["font.family"]=fm.FontProperties(fname=fp).get_name()
else:
    print("경고: 한글 폰트를 못 찾음 → 기본 폰트 사용 (한글이 네모로 나올 수 있음). HERB_FONT=<폰트 경로>로 지정 가능", file=sys.stderr)
plt.rcParams["axes.unicode_minus"]=False
m=None; OUTDIR=None

FLAT_PREFIX=("P01","P02","P03","P06","P07","D01","D02","D03","F0","A0","A10","A11","A15","A16","T02","T04","I03","S05","I05","K01","K02","K03","K04","K05","K06")
TITLE={"P01_side_L":"옆판 왼쪽","P01_side_R":"옆판 오른쪽","P02_front":"앞판","P03_back":"뒷판","A15":"전장부 칸막이(알루미늄)","A16":"덕트 벽(알루미늄)","T04":"트레이 가운데 판","K01":"측면 박스 앞판","K02":"측면 박스 뒷판","K03":"측면 박스 바닥","K04":"측면 박스 천장","K05":"측면 박스 뚜껑","K06":"측면 박스 장착판",
 "P06_bottom":"바닥판","P07_top":"천장판","D01_door":"문 바깥판","D02_door_plug":"문 플러그(폼)","D03_door_plug_liner":"문 플러그 라이너",
 "F01":"바닥 단열 폼","F02":"천장 단열 폼","F03_foam_side_L":"왼쪽 단열 폼","F03_foam_side_R":"오른쪽 단열 폼","F04_foam_front":"앞 단열 폼",
 "F04_foam_back":"뒤 단열 폼","F05":"펠티어 구멍 막음 폼","A01":"전장부 바닥 라이너","A02_liner_bay_L":"전장부 왼쪽 라이너","A02_liner_bay_R":"전장부 오른쪽 라이너",
 "A03_liner_bay_front":"전장부 앞 라이너","A03_liner_bay_back":"전장부 뒤 라이너","A04_liner_ch_L":"챔버 왼쪽 라이너","A04_liner_ch_R":"챔버 오른쪽 라이너","A05":"챔버 뒤(덕트 벽 앞) 라이너",
 "A06":"덕트 뒤 라이너","A07":"천장 라이너","A10":"타공판","A11":"로드셀 차폐판","T02":"트레이 메시","I03":"활성탄 패드","S05":"배기 플랩(PET)","I05":"흡기 플랩(PET)"}
def title_of(n):
    for k,v in TITLE.items():
        if n.startswith(k): return v
    return n

def solid_of(p):
    vs=p["shape"].vals()
    return vs[0] if len(vs)==1 else cq.Compound.makeCompound(vs)

def view_map(bb):
    dims={"x":bb.xlen,"y":bb.ylen,"z":bb.zlen}
    ax=min(dims,key=dims.get)
    c=bb.center
    if ax=="x":
        out=-1 if c.x<150 else 1
        U=(lambda p:-p.y) if out<0 else (lambda p:p.y); V=lambda p:p.z
        face="바깥(왼쪽)에서 본 면" if out<0 else "바깥(오른쪽)에서 본 면"
    elif ax=="y":
        out=-1 if c.y<150 else 1
        U=(lambda p:p.x) if out<0 else (lambda p:-p.x); V=lambda p:p.z
        face="앞에서 본 면" if out<0 else "뒤(바깥)에서 본 면"
    else:
        U=lambda p:p.x; V=lambda p:p.y; face="위에서 본 면 (아래쪽=앞)"
    return ax,U,V,face,dims[ax]

def slice_faces(sol,ax,t):
    bb=sol.BoundingBox(); e=0.01; big=5
    if ax=="x": slab=cq.Solid.makeBox(e,bb.ylen+2*big,bb.zlen+2*big,cq.Vector(t-e/2,bb.ymin-big,bb.zmin-big))
    elif ax=="y": slab=cq.Solid.makeBox(bb.xlen+2*big,e,bb.zlen+2*big,cq.Vector(bb.xmin-big,t-e/2,bb.zmin-big))
    else: slab=cq.Solid.makeBox(bb.xlen+2*big,bb.ylen+2*big,e,cq.Vector(bb.xmin-big,bb.ymin-big,t-e/2))
    com=sol.intersect(slab)
    n={"x":cq.Vector(1,0,0),"y":cq.Vector(0,1,0),"z":cq.Vector(0,0,1)}[ax]
    fs=[f for f in com.Faces() if abs(abs(f.normalAt().dot(n))-1)<1e-6 and abs(getattr(f.Center(),ax)-(t+e/2))<1e-4]
    return fs

def wire_geom(w,U,V):
    es=w.Edges()
    if len(es)<=2 and all(ed.geomType()=="CIRCLE" for ed in es):
        c=es[0].arcCenter(); r=es[0].radius()
        return ("circle",(U(c),V(c)),r)
    from OCP.BRepTools import BRepTools_WireExplorer
    from OCP.BRep import BRep_Tool
    ex=BRepTools_WireExplorer(w.wrapped); es=[]
    while ex.More():
        pv=BRep_Tool.Pnt_s(ex.CurrentVertex())
        es.append((cq.Edge(ex.Current()),cq.Vector(pv.X(),pv.Y(),pv.Z()))); ex.Next()
    pts=[]
    for ed,v0 in es:
        if ed.geomType()=="LINE": ps=[ed.startPoint(),ed.endPoint()]
        else: ps=[ed.positionAt(i/16) for i in range(17)]
        if (ps[0]-v0).Length > (ps[-1]-v0).Length: ps=ps[::-1]
        for p in ps:
            q=(round(U(p),2),round(V(p),2))
            if not pts or (abs(pts[-1][0]-q[0])>1e-3 or abs(pts[-1][1]-q[1])>1e-3): pts.append(q)
    if len(pts)>1 and abs(pts[0][0]-pts[-1][0])<1e-3 and abs(pts[0][1]-pts[-1][1])<1e-3: pts=pts[:-1]
    # 일직선 위 중간점 제거
    out=[]
    n=len(pts)
    for i in range(n):
        a,b,c=pts[i-1],pts[i],pts[(i+1)%n]
        cr=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
        if abs(cr)>1e-6: out.append(b)
    return ("poly",out or pts,None)

def features(p):
    sol=solid_of(p); bb=sol.BoundingBox()
    ax,U,V,face,th=view_map(bb)
    lo=getattr(bb,ax+"min"); hi=getattr(bb,ax+"max")
    res={}
    for tag,f in (("a",0.04),("m1",0.36),("m",0.5),("m2",0.64),("b",0.96)):
        fs=slice_faces(sol,ax,lo+(hi-lo)*f)
        outer=[];inner=[]
        for F in fs:
            outer.append(wire_geom(F.outerWire(),U,V))
            inner+= [wire_geom(w,U,V) for w in F.innerWires()]
        res[tag]=(outer,inner)
    return ax,U,V,face,th,res

def key(g):
    if g[0]=="circle": return ("c",round(g[1][0],1),round(g[1][1],1),round(g[2]*2,1))
    us=[p[0] for p in g[1]]; vs=[p[1] for p in g[1]]
    return ("r",round(min(us),1),round(min(vs),1),round(max(us),1),round(max(vs),1))

def analyze(p):
    ax,U,V,face,th,res=features(p)
    outer=res["m"][0]
    # origin = lower-left of outline
    allpts=[q for o in outer for q in (o[1] if o[0]=="poly" else [o[1]])]
    u0=min(q[0] for q in allpts); v0=min(q[1] for q in allpts)
    W=max(q[0] for q in allpts)-u0; H=max(q[1] for q in allpts)-v0
    def sh(g):
        if g[0]=="circle": return ("circle",(g[1][0]-u0,g[1][1]-v0),g[2])
        return ("poly",[(a-u0,b-v0) for a,b in g[1]],None)
    K={t:{key(g):g for g in res[t][1]} for t in res}
    km=K["m"]; ka=K["a"]; kb=K["b"]
    thr=[k for k in km if k in K["m1"] and k in K["m2"] and (k in ka or k in kb)]
    through=[sh(km[k]) for k in thr]
    pockets=[]
    seen=set()
    allk={}
    for t in ("a","m1","m","m2","b"): allk.update(K[t])
    for k,g in allk.items():
        if k in thr or k in seen: continue
        seen.add(k)
        if k[0]=="c" and any(t[0]=="c" and abs(t[1]-k[1])<0.2 and abs(t[2]-k[2])<0.2 and t[3]<k[3] for t in thr):
            if k not in ka and k not in kb: continue
            pockets.append((sh(g),"접시머리 자리")); continue
        side=("보는 면 쪽" if k in ka and k not in kb else "반대 면 쪽" if k in kb and k not in ka else "가운데")
        if k in ka and k in kb: continue
        pockets.append((sh(g),side))
    outl=[sh(o) for o in outer]
    return dict(name=p["name"],title=title_of(p["name"]),mat=p["mat"],face=face,th=round(th,2),W=round(W,1),H=round(H,1),
                outline=outl,through=through,pockets=pockets,note=p.get("note",""))

def label_hole(g):
    if g[0]=="circle":
        (u,v),r=g[1],g[2]; return ("원",f"Ø{2*r:.1f}",u,v,None)
    us=[q[0] for q in g[1]]; vs=[q[1] for q in g[1]]
    return ("사각",f"{max(us)-min(us):.1f}×{max(vs)-min(vs):.1f}",min(us),min(vs),(max(us),max(vs)))

def draw_geom(axp,d,lw=0.8):
    for o in d["outline"]:
        if o[0]=="poly":
            xs=[q[0] for q in o[1]]+[o[1][0][0]]; ys=[q[1] for q in o[1]]+[o[1][0][1]]
            axp.plot(xs,ys,"k-",lw=lw)
    for g in d["through"]:
        if g[0]=="circle":
            axp.add_patch(plt.Circle(g[1],g[2],fill=False,lw=lw,color="k"))
            axp.plot([g[1][0]-g[2]-1.5,g[1][0]+g[2]+1.5],[g[1][1]]*2,"r-",lw=0.3)
            axp.plot([g[1][0]]*2,[g[1][1]-g[2]-1.5,g[1][1]+g[2]+1.5],"r-",lw=0.3)
        else:
            xs=[q[0] for q in g[1]]+[g[1][0][0]]; ys=[q[1] for q in g[1]]+[g[1][0][1]]
            axp.plot(xs,ys,"k-",lw=lw)
    for g,side in d["pockets"]:
        if g[0]=="circle": axp.add_patch(plt.Circle(g[1],g[2],fill=False,lw=lw,ls="--",color="b"))
        else:
            xs=[q[0] for q in g[1]]+[g[1][0][0]]; ys=[q[1] for q in g[1]]+[g[1][0][1]]
            axp.plot(xs,ys,"b--",lw=lw)

def is_rect(d):
    o=d["outline"]
    return len(o)==1 and o[0][0]=="poly" and len(o[0][1])<=5

def overview_page(pdf,d):
    fig=plt.figure(figsize=(11.69,8.27))
    axp=fig.add_axes([0.04,0.08,0.55,0.82]); axp.set_aspect("equal")
    draw_geom(axp,d)
    rows=[]
    for i,g in enumerate(sorted(d["through"],key=lambda g:(label_hole(g)[3],label_hole(g)[2]))):
        t,sz,u,v,_=label_hole(g); hid=f"H{i+1}"
        rows.append((hid,t,sz,u,v))
        axp.annotate(hid,(u,v),fontsize=6,color="r",xytext=(3,3),textcoords="offset points")
    for j,(g,side) in enumerate(d["pockets"]):
        t,sz,u,v,_=label_hole(g); rows.append((f"P{j+1}",f"{t} 포켓({side})",sz,u,v))
        axp.annotate(f"P{j+1}",(u,v),fontsize=6,color="b",xytext=(3,-8),textcoords="offset points")
    axp.set_xlim(-15,d["W"]+15); axp.set_ylim(-15,d["H"]+15)
    axp.set_xlabel("u (mm, 왼쪽 모서리부터)"); axp.set_ylabel("v (mm, 아래 모서리부터)")
    axp.grid(True,lw=0.2)
    axp.annotate("",(0,-8),(d["W"],-8),arrowprops=dict(arrowstyle="<->",lw=0.6)); axp.text(d["W"]/2,-13,f"{d['W']:.1f}",ha="center",fontsize=8)
    axp.annotate("",(-8,0),(-8,d["H"]),arrowprops=dict(arrowstyle="<->",lw=0.6)); axp.text(-13,d["H"]/2,f"{d['H']:.1f}",va="center",rotation=90,fontsize=8)
    fig.text(0.04,0.95,f"{d['title']}  —  {d['name']}",fontsize=14,weight="bold")
    fig.text(0.04,0.92,f"재료: {d['mat']}   두께 {d['th']}   외곽 {d['W']:.1f} × {d['H']:.1f} mm   기준: {d['face']}, 왼쪽 아래 모서리 = (0,0)",fontsize=9)
    if d["note"]: fig.text(0.04,0.03,"비고: "+d["note"],fontsize=8)
    # table
    axt=fig.add_axes([0.62,0.08,0.36,0.82]); axt.axis("off")
    lines=["ID   종류        크기          u(가로)   v(세로)","-"*52]
    for hid,t,sz,u,v in rows:
        lines.append(f"{hid:<5}{t:<10}{sz:<14}{u:>8.1f}{v:>9.1f}")
    if not is_rect(d):
        lines+=["","외곽 꼭짓점 (u, v):"]
        for o in d["outline"]:
            if o[0]=="poly":
                pts=o[1]; lines+=[f"  ({a:.1f}, {b:.1f})" for a,b in pts[:40]]
    lines+=["","원 = 중심 좌표 / 사각 = 왼쪽 아래 꼭짓점 좌표","파란 점선 = 관통 아님(포켓)"]
    axt.text(0,1,"\n".join(lines[:70]),va="top",family=plt.rcParams["font.family"],fontsize=7.2)
    pdf.savefig(fig); plt.close(fig)
    return rows

def tiled_pages(pdf,d):
    PW,PH=210,297; M=10; TW,TH=PW-2*M,PH-2*M-12
    nu=max(1,math.ceil((d["W"]+10)/TW)); nv=max(1,math.ceil((d["H"]+10)/TH))
    for j in range(nv):
        for i in range(nu):
            fig=plt.figure(figsize=(PW/25.4,PH/25.4))
            axp=fig.add_axes([M/PW,M/PH,TW/PW,TH/PH]); axp.set_aspect("equal"); axp.axis("off")
            x0=-5+i*TW; y0=-5+j*TH
            axp.set_xlim(x0,x0+TW); axp.set_ylim(y0,y0+TH)
            draw_geom(axp,d,lw=0.5)
            for gx in range(int(math.floor(x0/50))*50,int(x0+TW)+1,50):
                axp.plot([gx,gx],[y0,y0+TH],color="0.75",lw=0.25)
                axp.text(gx+1,y0+2,str(gx),fontsize=5,color="0.4")
            for gy in range(int(math.floor(y0/50))*50,int(y0+TH)+1,50):
                axp.plot([x0,x0+TW],[gy,gy],color="0.75",lw=0.25)
                axp.text(x0+1,gy+1,str(gy),fontsize=5,color="0.4")
            axp.plot([x0,x0+TW,x0+TW,x0,x0],[y0,y0,y0+TH,y0+TH,y0],"k:",lw=0.3)
            fig.text(M/PW,1-8/PH,f"1:1  {d['title']} ({d['face']})  쪽 {j*nu+i+1}/{nu*nv}  [열 {i+1}, 행 {j+1}]  회색 격자 50mm",fontsize=7)
            bx=fig.add_axes([(PW-M-100)/PW,(PH-11)/PH,100/PW,2/PH]); bx.axis("off"); bx.set_xlim(0,100); bx.set_ylim(0,1)
            bx.plot([0,100],[0.5,0.5],"k-",lw=1); bx.text(50,1.2,"100mm — 자로 재서 확인 (인쇄: 실제 크기 100%)",fontsize=5,ha="center")
            pdf.savefig(fig); plt.close(fig)
    return nu*nv

def write_dxf(d,fn):
    doc=ezdxf.new(); ms=doc.modelspace()
    for ln,col in (("OUTLINE",7),("HOLES",1),("POCKETS",5)): doc.layers.add(ln,color=col)
    def poly(pts,layer): ms.add_lwpolyline(pts,close=True,dxfattribs={"layer":layer})
    for o in d["outline"]:
        if o[0]=="poly": poly(o[1],"OUTLINE")
    for g in d["through"]:
        if g[0]=="circle": ms.add_circle(g[1],g[2],dxfattribs={"layer":"HOLES"})
        else: poly(g[1],"HOLES")
    for g,_ in d["pockets"]:
        if g[0]=="circle": ms.add_circle(g[1],g[2],dxfattribs={"layer":"POCKETS"})
        else: poly(g[1],"POCKETS")
    doc.saveas(fn)

HOLES_PDF="herb_dryer_holes.pdf"          # 구멍표 (판마다 1쪽)
PRINT_PDF="herb_dryer_print_1to1.pdf"     # 1:1 분할 인쇄 (포맥스판)
TILE=("P01","P02","P03","P06","P07","D01","K01","K02","K03","K04","K05","K06")

def run(cad_module, outdir, version=""):
    """cad_module: 실행된 CAD 모듈 (PARTS 보유). 실패한 판 이름 목록을 돌려준다."""
    global m, OUTDIR
    m=cad_module; OUTDIR=str(outdir); os.makedirs(OUTDIR+"/dxf",exist_ok=True)
    flats=[p for p in m.PARTS if p["phase"]==1 and p["name"].startswith(FLAT_PREFIX)]
    order=sorted(flats,key=lambda p:p["name"])
    data=[]; failed=[]
    for p in order:
        try: data.append(analyze(p))
        except Exception as e: print("FAIL",p["name"],e); failed.append(p["name"])
    if version:
        for d in data: d["title"]=f"{d['title']} [{version}]"
    summary=[]
    with PdfPages(f"{OUTDIR}/{HOLES_PDF}") as pdf:
        for d in data:
            rows=overview_page(pdf,d); write_dxf(d,f"{OUTDIR}/dxf/{d['name']}.dxf")
            summary.append(dict(name=d["name"],title=d["title"],mat=d["mat"],th=d["th"],W=d["W"],H=d["H"],n_holes=len(d["through"]),n_pockets=len(d["pockets"]),face=d["face"],rect=is_rect(d)))
    with PdfPages(f"{OUTDIR}/{PRINT_PDF}") as pdf:
        tot=0
        for d in data:
            if d["name"].startswith(TILE): tot+=tiled_pages(pdf,d)
    print("pages 1:1:",tot)
    json.dump(summary,open(f"{OUTDIR}/cut_summary.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    for s in summary: print(s["name"],s["W"],s["H"],s["th"],s["n_holes"],s["n_pockets"],s["rect"])
    return failed

if __name__=="__main__":
    spec=importlib.util.spec_from_file_location("herb_cad",sys.argv[1]); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    sys.exit(1 if run(mod,sys.argv[2]) else 0)
