"""STL sections -> editable Onshape feature, sketches and checked BREP solids.
Rounded/tilted surfaces are approximated with <=0.25 mm Z bands; not a CAD-history recovery.
"""
from pathlib import Path
import sys,json,hashlib,csv,math,zipfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'output'/'case-design'/'python-packages'))
import numpy as np,trimesh,ezdxf,cadquery as cq
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
ROOT=HERE.parents[1]
DEST=ROOT/'output'/'case-design'/'onshape'
DEST.mkdir(parents=True,exist_ok=True)
NAMES=['base_case_left','base_case_right','top_cover_left','top_cover_right','top_plate_choc_left','top_plate_choc_right','power_switch_knob']

def circle(points):
 p=np.asarray(points)[:-1]
 if len(p)<12:return None
 A=np.column_stack((2*p[:,0],2*p[:,1],np.ones(len(p))))
 x,y,k=np.linalg.lstsq(A,(p*p).sum(axis=1),rcond=None)[0]
 r=math.sqrt(max(0,k+x*x+y*y))
 if r<0.1 or r>20 or np.max(np.abs(np.linalg.norm(p-[x,y],axis=1)-r))>0.0002:return None
 angles=np.unwrap(np.arctan2(p[:,1]-y,p[:,0]-x))
 if abs(angles[-1]-angles[0])<5.5:return None
 return [round(x,6),round(y,6),round(r,6)]

def loop_data(coords):
 c=circle(coords)
 if c:return {'circle':c}
 return {'points':[[round(x,6),round(y,6)] for x,y in coords]}

def sections(mesh,z):
 s=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
 if s is None:return []
 rings=[Polygon(p[:,:2]).simplify(.0001,preserve_topology=True) for p in s.discrete]
 assert all(p.is_valid for p in rings),z
 region=rings[0]
 for p in rings[1:]:region=region.symmetric_difference(p)
 polys=[region] if region.geom_type=='Polygon' else list(region.geoms)
 return [{'outer':loop_data(orient(p,sign=1).exterior.coords),'holes':[loop_data(r.coords) for r in p.interiors]} for p in polys if p.area>1e-7]

def cuts(mesh,name):
 lo,hi=mesh.bounds[:,2]
 if name.startswith('top_plate'):return [lo,8.6,8.8,hi]
 # Preserve every horizontal-face datum and fill curved spans at most 0.25 mm.
 horizontal=np.abs(mesh.face_normals[:,2])>.999999
 important=np.unique(np.round(mesh.triangles[horizontal,:,2],6))
 levels=sorted(set([float(lo),float(hi)]+[float(v) for v in important]))
 result=[levels[0]]
 for a,b in zip(levels,levels[1:]):
  n=math.ceil((b-a)/.25)
  result.extend(np.linspace(a,b,n+1)[1:].tolist())
 return result

def wire(data,z):
 if 'circle' in data:
  x,y,r=data['circle'];return cq.Wire.makeCircle(r,cq.Vector(x,y,z),cq.Vector(0,0,1))
 return cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in data['points']],close=True)

def extrusions(layer):
 return [cq.Solid.extrudeLinear(wire(p['outer'],layer['z0']),[wire(h,layer['z0']) for h in p['holes']],cq.Vector(0,0,layer['z1']-layer['z0'])) for p in layer['profiles']]

def dxf(path,profiles):
 doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM
 for name in ['OUTLINE','CUTOUTS']:doc.layers.new(name)
 ms=doc.modelspace()
 for p in profiles:
  for name,data in [('OUTLINE',p['outer'])]+[('CUTOUTS',h) for h in p['holes']]:
   if 'circle' in data:
    x,y,r=data['circle'];ms.add_circle((x,y),r,dxfattribs={'layer':name})
   else:ms.add_lwpolyline(data['points'][:-1],close=True,dxfattribs={'layer':name})
 doc.saveas(path)
 assert not ezdxf.readfile(path).audit().errors

def main():
 data={};stats={};holes=[];assembly=cq.Assembly(name='CLEAVE_HHJP_design_reference')
 for name in NAMES:
  src=ROOT/'models'/f'{name}.stl';m=trimesh.load_mesh(src)
  translation=[0,250,0] if name.startswith('top_plate') else [0,0,0]
  m.apply_translation(translation)
  levels=cuts(m,name);layers=[]
  for a,b in zip(levels,levels[1:]):
   profiles=sections(m,(a+b)/2)
   if not profiles:continue
   if layers and layers[-1]['profiles']==profiles:layers[-1]['z1']=round(b,6)
   else:layers.append({'z0':round(a,6),'z1':round(b,6),'profiles':profiles})
  data[name]={'layers':layers,'translation':translation,'bounds':m.bounds.tolist()}
  print(name,'layers',len(layers),flush=True)
  for tag,z in ([('outline',1),('supports',4.5),('rim',5.5),('cover_mounts',12)] if name.startswith('base') else [('profile',9.5 if name.startswith('top_plate') else 14 if name.startswith('top_cover') else 1)]):
   profiles=sections(m,z);dxf(DEST/f'{name}_{tag}.dxf',profiles)
   for p in profiles:
    for h in p['holes']:
     if 'circle' in h:
      x,y,r=h['circle'];holes.append([name,tag,z,x,y,round(r*2,6)])
  solids=[s for l in layers for s in extrusions(l)]
  shape=solids[0].fuse(*solids[1:]).clean() if len(solids)>1 else solids[0]
  assert shape.isValid(),name
  assert len(shape.Solids())==1,(name,len(shape.Solids()))
  path=DEST/f'{name}_reference.step';cq.exporters.export(shape,str(path))
  reopened=cq.importers.importStep(str(path)).val()
  assert reopened.isValid() and len(reopened.Solids())==1
  stats[name]={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_volume_mm3':float(m.volume),'rebuilt_volume_mm3':shape.Volume(),'volume_difference_percent':100*(shape.Volume()/m.volume-1),'valid_single_solid':True,'layers':len(layers),'bounds_mm':m.bounds.tolist(),'translation_mm':translation}
  assembly.add(shape,name=name)
  print(' checked',name,'volume difference %',round(stats[name]['volume_difference_percent'],4),flush=True)
 (DEST/'profiles.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
 (DEST/'validation.json').write_text(json.dumps(stats,indent=2),encoding='utf8')
 with (DEST/'hole_centers_mm.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['part','profile','z_mm','x_mm','y_mm','diameter_mm']);w.writerows(holes)
 cq.exporters.export(assembly.toCompound(),str(DEST/'all_parts_reference.step'))
 emit_featurescript(data)
 preview(data)

def emit_featurescript(data):
 template=(HERE/'feature-template.fs').read_text(encoding='utf8')
 fs=template.replace('/*PROFILE_DATA*/',json.dumps(data,separators=(',',':')))
 (DEST/'CLEAVE_HHJP.fs').write_text(fs,encoding='utf8')

def preview(data):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Polygon as Patch,Circle
 fig,axs=plt.subplots(2,2,figsize=(14,8))
 for ax,(side,z) in zip(axs.flat,[('left',4.5),('right',4.5),('left',9.5),('right',9.5)]):
  name=('base_case_' if z<5 else 'top_plate_choc_')+side
  m=trimesh.load_mesh(ROOT/'models'/f'{name}.stl')
  if z>5:m.apply_translation([0,250,0])
  for p in sections(m,z):
   for loop,color in [(p['outer'],'#90bdd2')]+[(h,'white') for h in p['holes']]:
    if 'circle' in loop:
     x,y,r=loop['circle'];ax.add_patch(Circle((x,y),r,facecolor=color,edgecolor='#234'))
    else:ax.add_patch(Patch(loop['points'],facecolor=color,edgecolor='#234',linewidth=.5))
  ax.set_xlim(m.bounds[0,0]-5,m.bounds[1,0]+5);ax.set_ylim(-5,110);ax.set_aspect('equal');ax.set_title(f'{name} / Z={z} mm');ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(DEST/'profiles_preview.png',dpi=150);plt.close(fig)

if __name__=='__main__':main()
