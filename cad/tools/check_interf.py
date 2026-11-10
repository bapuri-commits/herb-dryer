import sys, importlib.util
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
spec=importlib.util.spec_from_file_location("m",sys.argv[1]); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
P=[]
for p in m.PARTS:
    s=p["shape"].val().wrapped if hasattr(p["shape"],"val") else p["shape"]
    b=Bnd_Box(); BRepBndLib.Add_s(s,b); b.SetGap(0.0)
    P.append((p["name"],p["kind"],p["phase"],s,b))
res=[]
for i in range(len(P)):
  for j in range(i+1,len(P)):
    a,b=P[i],P[j]
    if a[4].IsOut(b[4]): continue
    if a[2]!=b[2]: continue   # 1차-2차 대체 관계
    c=BRepAlgoAPI_Common(a[3],b[3]).Shape(); g=GProp_GProps(); BRepGProp.VolumeProperties_s(c,g); v=g.Mass()
    if v>0.05: res.append((v,a[0],b[0],a[1],b[1]))
res.sort(reverse=True)
for v,a,b,ka,kb in res: print(f"{v:9.2f}  {a}  <->  {b}   [{ka}/{kb}]")
print("TOTAL",len(res))
