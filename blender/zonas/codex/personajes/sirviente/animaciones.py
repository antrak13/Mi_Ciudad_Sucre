"""Clips horneados sin dependencias de IK en el motor. Locomoción en sitio, 24 fps."""
import math
import bpy
from mathutils import Vector, Quaternion
from esqueleto import ik_dos, orientar, rotar, dedos, desplazar


def limpiar(rig):
    for p in rig.pose.bones:
        p.location=(0,0,0)
        p.rotation_quaternion=(1,0,0,0)
        p.scale=(1,1,1)


def suave(t):
    t=max(0,min(1,t))
    return t*t*(3-2*t)


def gesto(t):
    return suave(t/.26)*(1-suave((t-.72)/.28))


def mano_pecho(rig,respirar=0):
    bpy.context.view_layer.update()
    pecho=rig.pose.bones['pecho']
    base=pecho.matrix @ pecho.bone.matrix_local.inverted()
    ik_dos(rig,'brazo_izq','antebrazo_izq',base @ Vector((.168,-.157,1.158+respirar)),base @ Vector((.35,-.04,1.04)))
    orientar(rig,'mano_izq',base @ Vector((.155,-.154,1.236+respirar)))
    dedos(rig,'izq',-.82)
    # Pulgar sobre el canto de la solapa; los otros dedos sujetan el forro.
    rotar(rig,'pulgar_1_izq',.15,0,.25)


def pose(rig,nombre,t,datos):
    limpiar(rig)
    respirar=.002*math.sin(t*math.tau)
    desplazar(rig,'pecho',z=respirar)
    rotar(rig,'cabeza',0,0,-.94)
    desplazar(rig,'pelvis',z=-.006)
    for suf,sg in [('izq',1),('der',-1)]:
        y=.014*sg
        ik_dos(rig,'muslo_'+suf,'pierna_'+suf,(sg*.152,y,.135),(sg*.12,-.45,.46))
        orientar(rig,'pie_'+suf,(sg*.173,y-.159,.065))
    dedos(rig,'der',.10)
    mano_pecho(rig,respirar)
    if nombre in ('caminar','caminar_rapido','sigilo'):
        info=datos['movimiento'][nombre]
        fase=t*math.tau
        sigilo=nombre=='sigilo'
        rapido=nombre=='caminar_rapido'
        dur=round(info['duracion']*24)/24; velocidad=info['velocidad_m_s']
        apoyo=.56 if not sigilo else .64
        amplitud=velocidad*dur*apoyo/2
        desplazar(rig,'pelvis',x=.009*math.sin(fase),z=(-.096 if not sigilo else -.13)+.015*math.cos(fase*2))
        rotar(rig,'columna', .09 if rapido else .05 if not sigilo else .16,0,.025*math.sin(fase))
        rotar(rig,'pecho',0,0,-.04*math.sin(fase))
        for suf,sg,desfase in [('izq',1,0),('der',-1,.5)]:
            p=(t+desfase)%1
            if p<apoyo:
                u=p/apoyo
                y=-amplitud+2*amplitud*u
                z=.135
                inclinacion=0
            else:
                u=(p-apoyo)/(1-apoyo)
                y=amplitud-2*amplitud*suave(u)
                z=.135+(.093 if rapido else .065 if not sigilo else .035)*math.sin(math.pi*u)
                inclinacion=.25*math.sin(math.pi*u)
            objetivo=(sg*.122,y,z)
            ik_dos(rig,'muslo_'+suf,'pierna_'+suf,objetivo,(sg*.11,-.65,.53))
            orientar(rig,'pie_'+suf,(sg*.122,y-.160,z-.070+inclinacion*.09))
        # El mensajero protege la carta con la izquierda y balancea solo la mano libre.
        ik_dos(rig,'brazo_der','antebrazo_der',(-.295,-.01+.11*math.sin(fase),.85),(-.29,-.10,1.08))
        orientar(rig,'mano_der',(-.295,-.02+.11*math.sin(fase),.771))
        mano_pecho(rig,respirar-.012)
        rotar(rig,'cabeza',-.03,0,-.94+.035*math.sin(fase))
    elif nombre=='asentir':
        rotar(rig,'cabeza',.18*math.sin(t*math.tau*2)*gesto(t),0,-.94)
    elif nombre in ('silencio','senalar'):
        g=gesto(t)
        objetivo=Vector((-.292,-.025,.842)).lerp(Vector((-.025,-.137,1.3721) if nombre=='silencio' else (-.41,-.35,1.28)),g)
        ik_dos(rig,'brazo_der','antebrazo_der',objetivo,(-.35,-.15,1.06))
        destino=objetivo+Vector((0,.010,.079) if nombre=='silencio' else (-.020,-.077,.005))
        # Interpolar la dirección de la palma, para que el brazo no salte al iniciar el gesto.
        direccion=Vector((0,-.005,-.079)).lerp(destino-objetivo,g)
        orientar(rig,'mano_der',objetivo+direccion)
        dedos(rig,'der',.10-g*1.05,indice=.10*(1-g))
        if nombre=='silencio':
            rotar(rig,'cabeza',.035*g,0,-.94*(1-g))
    elif nombre=='mirar_atras':
        g=gesto(t)
        rotar(rig,'columna',0,0,-.28*g)
        rotar(rig,'pecho',0,0,-.26*g)
        rotar(rig,'cuello',0,0,-.30*g)
        rotar(rig,'cabeza',-.04*g,0,-.94-.40*g)
        mano_pecho(rig,respirar)
    elif nombre=='apartarse':
        g=gesto(t)
        desplazar(rig,'pelvis',x=.09*g,z=-.006-.04*g)
        rotar(rig,'columna',0,-.14*g,.14*g)
        rotar(rig,'pecho',.02*g,0,.30*g)
        for suf,sg in [('izq',1),('der',-1)]:
            ik_dos(rig,'muslo_'+suf,'pierna_'+suf,(sg*.152+.045*g,0,.135),(sg*.12,-.4,.46))
            orientar(rig,'pie_'+suf,(sg*.173+.045*g,-.160,.065))
        rotar(rig,'cabeza',0,0,-.94-.15*g)
        mano_pecho(rig,respirar)
    elif nombre=='mostrar_forro':
        g=gesto(t)
        rotar(rig,'solapa_izq',0,-.85*g,-.10*g)
        rig.pose.bones['carta'].location.y=.115*g
        rig.pose.bones['carta'].location.z=-.018*g
        bpy.context.view_layer.update()
        pecho=rig.pose.bones['pecho'];base=pecho.matrix @ pecho.bone.matrix_local.inverted()
        objetivo=base @ Vector((.168+.10*g,-.157-.04*g,1.158))
        ik_dos(rig,'brazo_izq','antebrazo_izq',objetivo,base @ Vector((.40,-.03,1.04)))
        orientar(rig,'mano_izq',base @ Vector((.155+.10*g,-.154-.04*g,1.236)))
        dedos(rig,'izq',-.82+.22*g)
        rotar(rig,'cabeza',.14*g,0,-.94+.88*g)
    bpy.context.view_layer.update()


def crear(rig,datos):
    escena=bpy.context.scene
    escena.render.fps=24
    rig.animation_data_create()
    acciones=[]
    for nombre,info in datos['movimiento'].items():
        action=bpy.data.actions.new(nombre)
        rig.animation_data.action=action
        total=round(info['duracion']*24)
        for frame in range(total+1):
            escena.frame_set(frame)
            pose(rig,nombre,frame/total,datos)
            for pb in rig.pose.bones:
                pb.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=pb.name)
                if pb.name in ('pelvis','pecho','carta'):
                    pb.keyframe_insert(data_path='location',frame=frame,group=pb.name)
        # Interpolación lineal del horneado; el origen de cada clip es siempre el mismo.
        for capa in action.layers:
            for tira in capa.strips:
                for bolsa in tira.channelbags:
                    for curva in bolsa.fcurves:
                        for k in curva.keyframe_points:
                            k.interpolation='LINEAR'
        action.use_fake_user=True
        acciones.append(action)
        rig.animation_data.action=None
        track=rig.animation_data.nla_tracks.new()
        track.name=nombre
        strip=track.strips.new(nombre,0,action)
        strip.action_frame_start=0
        strip.action_frame_end=total
        track.mute=True
    rig.animation_data.action=None
    limpiar(rig)
    escena.frame_set(0)
    print('Clips:',', '.join(a.name for a in acciones))
    return acciones
