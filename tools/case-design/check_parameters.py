"""Local geometric check of the FeatureScript parameter construction (not FS execution)."""
from build import *

data=json.loads((DEST/'profiles.json').read_text())
checks={}
for side in ['left','right']:
 name=f'base_case_{side}';model=data[name]
 shape=cq.importers.importStep(str(DEST/f'{name}_reference.step')).val()
 old=model['layers'][0];outline=old['profiles'][0]['outer']
 floor=extrusions(old)[0]
 parameters={'bottomThickness':1.2,'extraDepth':4,'wallExtra':1.2,'widthExtra':2,'lengthExtra':3,'insertDiameter':2.9}
 bottom=2-parameters['extraDepth']-parameters['bottomThickness']
 lowerfloor=extrusions({'z0':bottom,'z1':2-parameters['extraDepth'],'profiles':old['profiles']})[0]
 rim=next(l['profiles'] for l in model['layers'] if l['z0']<=5.5<=l['z1'])
 lowerwalls=extrusions({'z0':2-parameters['extraDepth'],'z1':2,'profiles':rim})
 bounds=np.asarray(model['bounds']);cx,cy=(bounds[0,:2]+bounds[1,:2])/2
 dx=parameters['wallExtra']+parameters['widthExtra'];dy=parameters['wallExtra']+parameters['lengthExtra']
 expanded={'points':[[x+(-dx if x<cx else dx),y+(-dy if y<cy else dy)] for x,y in outline['points']]}
 outer=extrusions({'z0':bottom,'z1':6.5,'profiles':[{'outer':expanded,'holes':[outline]}]})
 result=shape.cut(floor).fuse(lowerfloor,*lowerwalls,*outer).clean()
 assert result.isValid() and len(result.Solids())==1
 box=result.BoundingBox()
 assert abs(box.zmin-bottom)<.00001 and abs(box.zmax-13.5)<.00001
 checks[name]={'parameters_mm':parameters,'valid_single_solid':True,'bottom_z_mm':box.zmin,'top_z_mm':box.zmax,'total_height_mm':box.zlen,'width_mm':box.xlen,'length_mm':box.ylen,'scope':'Local OCC geometry, not Onshape FeatureScript runtime'}
 cq.exporters.export(result,str(DEST/f'{name}_parameter_example.step'))
 print(name,checks[name],flush=True)
(DEST/'parameter_validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
