from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'output'/'case-design'/'python-packages'))
import numpy as np,trimesh,cadquery as cq
from shapely.geometry import Polygon,Point
from build import sections,DEST,ROOT,NAMES

def ring(data):
 if 'circle' in data:
  x,y,r=data['circle'];return Point(x,y).buffer(r,quad_segs=90)
 return Polygon(data['points'])
def material(profiles):
 from shapely.ops import unary_union
 return unary_union([ring(p['outer']).difference(unary_union([ring(h) for h in p['holes']])) for p in profiles])

data=json.loads((DEST/'profiles.json').read_text())
report=json.loads((DEST/'validation.json').read_text())
for name in NAMES:
 m=trimesh.load_mesh(ROOT/'models'/f'{name}.stl');m.apply_translation(data[name]['translation'])
 error=0;worst=0
 for l in data[name]['layers']:
  target=material(l['profiles']);height=l['z1']-l['z0']
  diffs=[]
  for f in [.1,.3,.5,.7,.9]:
   z=l['z0']+f*height;original=material(sections(m,z))
   diff=original.symmetric_difference(target).area
   diffs.append(diff);worst=max(worst,diff)
  error+=sum(diffs)/len(diffs)*height
 report[name]['sampled_symmetric_difference_mm3']=error
 report[name]['sampled_symmetric_difference_percent']=100*error/m.volume
 report[name]['worst_sample_section_difference_mm2']=worst
 assert 100*error/m.volume<2,(name,100*error/m.volume)
 print(name,'symmetric difference %',round(100*error/m.volume,4),flush=True)

# Confirm the four Choc mounting bores coincide with the four base insert bores.
alignment={}
for side in ['left','right']:
 base=material(sections(trimesh.load_mesh(ROOT/'models'/f'base_case_{side}.stl'),4.5))
 plate=trimesh.load_mesh(ROOT/'models'/f'top_plate_choc_{side}.stl');plate.apply_translation([0,250,0])
 def holes(profiles,radius):
  return [h['circle'][:2] for p in profiles for h in p['holes'] if 'circle' in h and abs(h['circle'][2]-radius)<.001]
 a=holes(sections(trimesh.load_mesh(ROOT/'models'/f'base_case_{side}.stl'),4.5),1.45)
 b=holes(sections(plate,9.5),1.1)
 errors=[min(math.dist(p,q) for q in a) for p in b]
 assert len(a)==len(b)==4
 assert max(errors)<.001,(side,errors)
 alignment[side]={'base_mounts':a,'plate_mounts':b,'max_center_error_mm':max(errors),'plate_y_translation_mm':250}
report['mounting_alignment']=alignment
(DEST/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Four plate mounts per side align with base inserts.',flush=True)
