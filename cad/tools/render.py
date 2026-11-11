"""렌더 이미지 (pyvista 오프스크린)

python cad/tools/render.py <cad.py> [출력폴더=.] [all|ext|sec|dbg]
  ext: 외관·내부(r1~r4), sec: 단면(r5, r6), all: 둘 다
리눅스 서버에서는 xvfb-run 으로 실행한다 (CI 참고).
"""
import os, sys, importlib.util, numpy as np, pyvista as pv
pv.OFF_SCREEN=True
m=None; meshes={}; OUT="."

def load_meshes(cad_module):
    global m, meshes
    m=cad_module; meshes={}
    for p in m.PARTS:
        sh=p["shape"].val() if hasattr(p["shape"],"val") else p["shape"]
        if hasattr(p["shape"],"vals") and len(p["shape"].vals())>1:
            sh=m.cq.Compound.makeCompound(p["shape"].vals())
        vs,fs=sh.tessellate(0.3,0.5)
        if not fs: continue
        v=np.array([(a.x,a.y,a.z) for a in vs]); f=np.hstack([[3,*t] for t in fs])
        meshes[p["name"]]=(pv.PolyData(v,f),p)

def shot(fn, keep, cam, title, size=(1400,1100), parallel=False, zoom=1.0, alpha_override=None):
    fn=os.path.join(OUT,fn)
    pl=pv.Plotter(off_screen=True, window_size=size); pl.set_background("white"); pl.enable_depth_peeling(8)
    for n,(mesh,p) in meshes.items():
        if not keep(n,p): continue
        c=p["color"]; op=c[3] if len(c)==4 else 1.0
        if n.startswith(("H02",)): op=1.0
        if alpha_override: op=alpha_override(n,p,op)
        pl.add_mesh(mesh,color=c[:3],opacity=op,smooth_shading=False,show_edges=False,
                    specular=0.2)
        try: pl.add_mesh(mesh.extract_feature_edges(40),color=(0.25,0.25,0.25),line_width=0.6,opacity=min(1,op+0.2))
        except: pass
    pl.camera_position=cam
    if parallel: pl.enable_parallel_projection()
    pl.camera.zoom(zoom)
    pl.add_text(title,font_size=11,color="black")
    pl.screenshot(fn); pl.close(); print(fn)
P1=lambda n,p: p["phase"]==1
iso=[(-420,-520,430),(150,150,120),(0,0,1)]
cut=lambda n,p: P1(n,p) and not n.startswith(("D0","P02_","F04_foam_front","P07_","S04","S05","A03_liner_bay_front","E10","E11","F02","A07","P01_side_L","F03_foam_side_L","A04_liner_ch_L","A02_liner_bay_L","C01","C02","C_"))
bay=lambda n,p: P1(n,p) and (p["shape"].val().BoundingBox().zmax<=81.5 if hasattr(p["shape"],"val") else True) and not n.startswith(("A10","P05","P02","F04","A03_liner_bay_front","E10","E11","I0","D0","P01","F03","A02","A04","F02","A07","P07","F01_","P06","A01"))
sec=lambda n,p: P1(n,p) and not n.startswith(("P01_side_L","F03_foam_side_L","A04_liner_ch_L","A02_liner_bay_L","C01","C02","C_"))
def section(fn, x0, title):
    fn=os.path.join(OUT,fn)
    pl=pv.Plotter(off_screen=True, window_size=(1500,1100)); pl.set_background("white")
    for n,(mesh,p) in meshes.items():
        if p["phase"]!=1 and not n.startswith("X_P2"): continue
        if n.startswith(("D_","E10_bolt","I_bolt")): pass
        try: cm=mesh.clip(normal=(-1,0,0),origin=(x0,0,0))
        except: continue
        if cm.n_points==0: continue
        c=p["color"]; op=c[3] if len(c)==4 else 1.0
        if n.startswith(("H02",)): op=1.0
        pl.add_mesh(cm,color=c[:3],opacity=max(op,0.35))
        try: pl.add_mesh(cm.extract_feature_edges(40),color=(0.2,0.2,0.2),line_width=0.6)
        except: pass
    pl.camera_position=[(x0-900,150,135),(x0,150,135),(0,0,1)]
    pl.enable_parallel_projection(); pl.camera.zoom(1.25)
    pl.add_text(title,font_size=11,color="black"); pl.screenshot(fn); pl.close(); print(fn)
def run(cad_module, outdir=".", which="all", version=""):
    global OUT
    OUT=str(outdir); os.makedirs(OUT,exist_ok=True)
    load_meshes(cad_module)
    tag=f"{version} " if version else ""
    if which in ("all","ext"):
        shot("r1_exterior.png", lambda n,p: True, iso, f"{tag}exterior (front door closed)")
        shot("r2_cutaway.png", cut, [(-380,-420,330),(150,150,110),(0,0,1)], f"{tag}cutaway: front/left/top removed")
        shot("r3_bay_top.png", bay, [(150,150,700),(150,150,0),(0,1,0)], f"{tag}bay plan view (z<81, liners/foam hidden)", parallel=True, zoom=1.3)
        shot("r4_bay_iso.png", bay, [(-200,-250,320),(150,140,40),(0,0,1)], f"{tag}bay iso")
    if which in ("all","sec"):
        section("r5_section_x65.png", 65, f"{tag}section x=65 (fan/PTC axis), seen from left; front=left")
        section("r6_section_x150.png", 150, f"{tag}section x=150 (loadcell/sensor), seen from left")
        section("r7_section_x220.png", 220, f"{tag}section x=220 (intake axis), seen from left")
    if which=="dbg":
        shot("dbg.png", lambda n,p: n.startswith(("H0","A12","A13")), [(-200,-250,320),(70,170,40),(0,0,1)], "heater debug")

if __name__=="__main__":
    spec=importlib.util.spec_from_file_location("herb_cad",sys.argv[1]); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    run(mod, sys.argv[2] if len(sys.argv)>2 else ".", sys.argv[3] if len(sys.argv)>3 else "all", os.environ.get("HERB_VERSION",""))
