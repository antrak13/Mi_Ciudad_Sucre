"""Revisión visual antes de exportar o animar. No sustituye los activos públicos."""
import sys
import json
from pathlib import Path
import bpy
from mathutils import Vector

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
import construir as c
from esqueleto import crear as crear_rig
from modelo import crear as crear_modelo
from animaciones import pose

def main():
    c.SALIDA=c.RAIZ/'revisiones/codex/sirviente_v2/activos'
    c.REV=c.RAIZ/'revisiones/codex/sirviente_v2'
    datos=json.loads((BASE/'diseno.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    rig=crear_rig()
    mat=c.material_imagen('Tela_y_planos_low_poly',c.SALIDA/'sirviente_color.png')
    objeto=crear_modelo(mat,rig)
    c.crear_carta(rig)
    camara=c.estudio()
    bpy.context.scene.cycles.samples=16
    bpy.context.scene.render.resolution_x=720
    bpy.context.scene.render.resolution_y=1000
    pose(rig,'reposo',0,datos)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(c.REV/'estudio.blend'),compress=True)
    vistas=[('cuerpo',(-2.5,-5,2.25),(0,0,.91),1.90),
            ('rostro',(-1.3,-4,1.85),(0,-.015,1.58),.49),
            ('espalda',(2.5,5,2.15),(0,0,.91),1.90)]
    for nombre,pos,mira,escala in vistas:
        if '--vistas' in sys.argv and nombre not in sys.argv[sys.argv.index('--vistas')+1].split(','):continue
        camara.location=pos
        camara.rotation_euler=(Vector(mira)-camara.location).to_track_quat('-Z','Y').to_euler()
        camara.data.ortho_scale=escala
        bpy.context.scene.render.filepath=str(c.REV/(nombre+'.png'))
        bpy.ops.render.render(write_still=True)
    print('ESTUDIO_LISTO',len(objeto.data.vertices),'vértices',flush=True)

if __name__=='__main__':main()
