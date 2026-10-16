from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'output'/'case-design'
OUTPUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(OUTPUT/'python-packages'))
import trimesh,numpy as np
names=['base_case_left','base_case_right','top_cover_left','top_cover_right','top_plate_choc_left','top_plate_choc_right','power_switch_knob']
report={}
for name in names:
 m=trimesh.load_mesh(ROOT/'models'/f'{name}.stl')
 levels,count=np.unique(np.round(m.vertices[:,2],5),return_counts=True)
 info={'bounds':m.bounds.tolist(),'watertight':bool(m.is_watertight),'volume':float(m.volume),'faces':len(m.faces),'z_levels':dict(zip(map(str,levels),map(int,count)))}
 print(name,json.dumps(info))
 report[name]=info
 for z in ([0.5,1.5,2.5,4,5.5,7,9,11] if name.startswith('base') else [(m.bounds[0,2]+m.bounds[1,2])/2]):
  s=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
  if s is None:continue
  loops=[]
  for pts in s.discrete:
   from shapely.geometry import Polygon
   p=Polygon(pts[:,:2]).simplify(.005,preserve_topology=True)
   loops.append({'area':round(p.area,5),'bounds':list(p.bounds),'points':len(p.exterior.coords)-1,'coords':list(p.exterior.coords)})
  info.setdefault('sections',{})[str(z)]=loops
  print(' section',z,[(x['area'],x['points'],[round(v,3) for v in x['bounds']]) for x in loops])
(OUTPUT/'analysis.json').write_text(json.dumps(report,indent=2))
