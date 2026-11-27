"""Escultura nueva desde Simplified low-poly historical messenger (1).png.

Grandes planos continuos, dos botones, ojos planos y nariz de cuña. Ninguna esfera.
Las proporciones se miden desde sombrero y suelo de la figura coloreada (18..1005 px).
"""
import math
import bpy
from mathutils import Vector
from malla import Malla
from esqueleto import datos_mano

CONTORNO=[(-.72,-1),(.72,-1),(1,-.60),(1,.60),(.72,1),(-.72,1),(-1,.60),(-1,-.60)]


def seccion(x,y,z,rx,ry):
    return [(x+a*rx,y+b*ry,z) for a,b in CONTORNO]


def cuerpo_peso(z):
    if z<=1.045:return 'pelvis'
    if z<1.20:return {'columna':.80,'pecho':.20}
    return 'pecho'


def pieza(m,puntos,rol,peso,grosor=.003):
    """Una pieza de tela con cantos; reverso separado, sin hojas coplanares."""
    detras=[(x,y+grosor,z) for x,y,z in puntos]
    m.poligono(puntos,rol,peso)
    m.poligono(list(reversed(detras)),rol,peso)
    for i in range(len(puntos)):
        j=(i+1)%len(puntos)
        m.poligono([puntos[i],detras[i],detras[j],puntos[j]],rol,peso)


def miembro(m,puntos,anchos,fondos,rol,pesos):
    """Prisma de sección rectangular con chaflanes y caras frontales anchas."""
    anillos=[]
    for i,p in enumerate(puntos):
        d=(Vector(puntos[min(i+1,len(puntos)-1)])-Vector(puntos[max(0,i-1)])).normalized()
        u=d.cross(Vector((0,1,0))).normalized()
        v=d.cross(u).normalized()
        anillos.append([Vector(p)+a*anchos[i]*u+b*fondos[i]*v for a,b in CONTORNO])
    return m.anillos(anillos,rol,pesos)


def camisa_y_cuello(m):
    m.anillos([seccion(0,0,z,w,d) for z,w,d in [(1.014,.110,.064),(1.16,.118,.067),(1.31,.126,.066)]],
              'camisa',[cuerpo_peso(z) for z in (1.014,1.16,1.31)])
    m.anillos([seccion(0,.009,z,w,d) for z,w,d in [(1.382,.040,.037),(1.438,.042,.038),(1.545,.043,.041)]],
              'piel',['pecho','cuello',{'cuello':.4,'cabeza':.6}])
    pieza(m,[(-.043,-.045,1.420),(.043,-.045,1.420),(0,-.083,1.302)],'piel','pecho')
    # Frente marfil y escote en V; sin tapeta ni botones añadidos.
    for sg in (-1,1):
        m.poligono([(sg*.108,-.067,1.020),(sg*.118,-.067,1.310),(sg*.075,-.055,1.387),
                    (sg*.043,-.052,1.412),(0,-.085,1.302),(0,-.081,1.020)],'camisa',{'columna':.5,'pecho':.5})
        pieza(m,[(sg*.042,-.039,1.427),(sg*.079,-.060,1.389),
                 (sg*.033,-.096,1.326),(sg*.021,-.071,1.385)],'camisa','pecho')
    m.anillos([seccion(0,0,z,.139,.081) for z in (1.003,1.044)],'cinto','pelvis')


def chaqueta(m):
    # El torso, los frentes y los hombros son la misma superficie, abierta en el centro.
    filas=[]
    for z,w,d,izq,der in [(.951,.215,.103,-.014,.084),(1.045,.185,.091,-.024,.079),
                         (1.20,.190,.092,-.030,.069),(1.30,.186,.086,-.032,.053)]:
        filas.append([(izq,-d,z),(-w*.83,-d*.78,z),(-w,0,z),(-w*.83,d*.78,z),
                      (-w*.32,d,z),(w*.32,d,z),(w*.83,d*.78,z),(w,0,z),
                      (w*.83,-d*.78,z),(der,-d,z)])
    filas.append([(-.036,-.051,1.418),(-.146,-.062,1.368),(-.181,0,1.352),
                  (-.146,.065,1.370),(-.051,.055,1.412),(.051,.055,1.412),
                  (.146,.065,1.370),(.181,0,1.352),(.146,-.062,1.368),(.036,-.051,1.418)])
    ids=[[m.vertice(p,cuerpo_peso(p[2])) for p in f] for f in filas]
    for i in range(len(ids)-1):
        for j in range(9):m.cara((ids[i][j],ids[i][j+1],ids[i+1][j+1],ids[i+1][j]),'chaqueta')
    for lado in (0,9):
        for i in range(len(filas)-1):
            a,b=filas[i][lado],filas[i+1][lado]
            m.poligono([a,b,(b[0],b[1]+.004,b[2]),(a[0],a[1]+.004,a[2])],'chaqueta',cuerpo_peso((a[2]+b[2])/2))
    pieza(m,[(-.040,-.051,1.427),(-.100,-.071,1.386),(-.078,-.087,1.354),
             (-.104,-.088,1.346),(-.034,-.112,1.241),(-.050,-.100,1.340)],'chaqueta','pecho')
    pieza(m,[(.040,-.051,1.427),(.100,-.071,1.386),(.078,-.087,1.354),
             (.107,-.096,1.337),(.068,-.121,1.260),(.049,-.099,1.340)],'chaqueta','solapa_izq')
    # Panel de forro granate con espesor y bisagra propia.
    puntos=[(.080,-.108,1.301),(.133,-.108,1.300),(.208,-.122,.953),(.103,-.124,.951)]
    pieza(m,puntos,'forro','solapa_izq',.006)
    pieza(m,[(.132,-.110,1.302),(.141,-.109,1.300),(.217,-.124,.953),(.206,-.125,.951)],
          'chaqueta','solapa_izq')
    pieza(m,[(.075,-.134,1.184),(.135,-.131,1.191),(.147,-.131,1.104),(.086,-.135,1.099)],
          'forro','solapa_izq')
    for i in range(8):
        z=1.258-i*.038;x=.141+(1.30-z)*.145
        m.poligono([(x-.006,-.128,z+.001),(x+.002,-.128,z-.001),
                    (x+.002,-.129,z-.003),(x-.006,-.129,z-.001)],'costura','solapa_izq')
    # Exactamente dos botones octogonales, planos.
    for z in (1.167,1.030):
        x=-.043;y=-.111 if z>1.1 else -.108
        pts=[(x+.017*math.cos(i*math.tau/8),y,z+.017*math.sin(i*math.tau/8)) for i in range(8)]
        pieza(m,pts,'boton',cuerpo_peso(z),.005)


def brazos_y_manos(m):
    for sg,suf in [(1,'izq'),(-1,'der')]:
        br,ab,ma='brazo_'+suf,'antebrazo_'+suf,'mano_'+suf
        miembro(m,[(sg*.166,0,1.350),(sg*.201,-.002,1.320),(sg*.253,-.005,1.102),
                   (sg*.258,-.007,1.078),(sg*.290,-.025,.864)],
                [.047,.064,.054,.054,.047],[.058,.060,.051,.052,.043],'chaqueta',
                ['pecho',{'pecho':.15,br:.85},{br:.65,ab:.35},{br:.3,ab:.7},ab])
        miembro(m,[(sg*.290,-.025,.870),(sg*.292,-.026,.829)],[.040,.039],[.034,.034],'camisa',[ab,ab])
        miembro(m,[(sg*.292,-.026,.842),(sg*.292,-.028,.783),(sg*.292,-.030,.740)],
                [.033,.044,.039],[.025,.026,.022],'piel',[{ab:.25,ma:.75},ma,ma])
        for nombre,puntos in datos_mano(sg).items():
            b=[f'{nombre}_{i}_{suf}' for i in (1,2,3)]
            ancho=.010 if nombre not in ('pulgar','menique') else .009
            miembro(m,puntos,[ancho,ancho,ancho*.91,ancho*.75],[ancho*.82]*4,'piel',
                    [b[0],{b[0]:.5,b[1]:.5},{b[1]:.5,b[2]:.5},b[2]])


def piernas_y_zapatos(m):
    # Pelvis cerrada dentro de las perneras: la transición no es una lámina colgante.
    m.anillos([seccion(0,.005,z,w,d) for z,w,d in [(1.024,.140,.077),(.952,.156,.086),(.890,.115,.068)]],
              'calzon','pelvis')
    for sg,suf in [(1,'izq'),(-1,'der')]:
        mu,pi,pie='muslo_'+suf,'pierna_'+suf,'pie_'+suf
        m.anillos([seccion(sg*x,y,z,w,d) for x,y,z,w,d in [
            (.079,.004,1.016,.078,.079),(.091,.004,.932,.082,.087),
            (.106,0,.720,.078,.082),(.117,-.008,.480,.069,.072),(.117,-.008,.451,.069,.072)]],
            'calzon',[{'pelvis':.75,mu:.25},{'pelvis':.35,mu:.65},mu,{mu:.75,pi:.25},{mu:.55,pi:.45}])
        m.anillos([seccion(sg*.117,-.008,z,.075,.077) for z in (.426,.488)],
                  'calzon',[{mu:.25,pi:.75},{mu:.65,pi:.35}])
        m.anillos([seccion(sg*.117,-.008,z,.0755,.0775) for z in (.480,.488)],'chaqueta',{mu:.6,pi:.4})
        m.anillos([seccion(sg*x,y,z,w,d) for x,y,z,w,d in [
            (.117,-.008,.455,.045,.045),(.120,.006,.355,.046,.047),(.122,0,.149,.028,.032)]],
            'piel',[pi,pi,{pi:.85,pie:.15}])
        x=sg*.122
        cont=[(-.048,-.215),(.048,-.215),(.061,-.194),(.061,-.078),
              (.046,.063),(-.046,.063),(-.061,-.078),(-.061,-.194)]
        inferior=[(x+a,b,.026) for a,b in cont]
        superior=[(x+a*.94,b,.074 if b<-.15 else .115 if b<-.04 else .159) for a,b in cont]
        m.anillos([inferior,superior],'zapato',pie)
        m.anillos([[(x+a,b,z) for a,b in cont] for z in (0,.027)],'suela',pie)


def rostro(m):
    # Mejillas, mandíbula y frente de planos grandes. No se reutiliza la cabeza anterior.
    filas=[(1.453,.036,.059,.047),(1.482,.069,.080,.064),(1.526,.094,.085,.080),
           (1.575,.096,.087,.086),(1.617,.094,.086,.089),
           (1.660,.090,.080,.086),(1.692,.075,.065,.072)]
    rings=[]
    for z,w,frente,dorso in filas:
        centro=frente+(.003 if z>=1.575 else -.004 if z>=1.526 else 0)
        rings.append([(-w*.62,-frente,z),(-w*.18,-centro,z),(w*.18,-centro,z),
                      (w*.62,-frente,z),(w,-frente*.42,z),(w,dorso*.52,z),
                      (w*.60,dorso,z),(-w*.60,dorso,z),(-w,dorso*.52,z),(-w,-frente*.42,z)])
    m.anillos(rings,'piel','cabeza')
    puntos=[(-.008,-.087,1.580),(.008,-.087,1.580),(.013,-.089,1.542),
            (0,-.112,1.545),(-.013,-.089,1.542)]
    vi=[m.vertice(p,'cabeza') for p in puntos]
    for f in [(0,1,3),(1,2,3),(0,3,4),(4,3,2)]:m.cara([vi[i] for i in f],'piel')
    m.poligono([(-.020,-.0845,1.502),(-.006,-.0855,1.507),(.009,-.0855,1.506),
                (.020,-.0845,1.502),(.007,-.087,1.504),(-.006,-.087,1.505)],'boca','cabeza')
    for sg,suf in [(1,'izq'),(-1,'der')]:
        x=sg*.039
        cont=[(.0175*math.cos(i*math.tau/12),.015*math.sin(i*math.tau/12)) for i in range(12)]
        m.poligono([(x+a,-.091,1.593+b) for a,b in cont],'ojo','ojo_'+suf)
        m.poligono([(x-.005+.0095*math.cos(i*math.tau/10),-.0922,
                     1.594+.0142*math.sin(i*math.tau/10)) for i in range(10)],'iris','ojo_'+suf)
        m.poligono([(x-.023,-.087,1.624),(x-.022,-.087,1.637),
                    (x+.022,-.087,1.635),(x+.023,-.087,1.623)],'pelo','cabeza')
        oreja=[(sg*.089,-.011,1.574),(sg*.114,-.008,1.580),(sg*.125,-.003,1.555),
               (sg*.111,-.003,1.529),(sg*.090,-.012,1.534)]
        pieza(m,oreja,'piel','cabeza',.017)


def pelo(m):
    # El casquete cierra el cráneo bajo el sombrero inclinado: no queda piel calva ni aire entre ambos.
    m.anillos([seccion(0,.009,z,rx,ry)
               for z,rx,ry in [(1.673,.091,.085),(1.688,.080,.075),(1.698,.054,.050)]],
              'pelo','cabeza')
    angulos=[-.22+i*(math.pi+.44)/8 for i in range(9)]
    rings=[]
    for z,w,d in [(1.452,.095,.095),(1.585,.108,.105),(1.681,.088,.083)]:
        rings.append([(w*math.cos(a),.009+d*math.sin(a),z+(.060*abs(math.cos(a)) if z<1.5 else 0)) for a in angulos])
    ids=[[m.vertice(p,'cabeza') for p in ring] for ring in rings]
    for k in range(2):
        for j in range(8):m.cara((ids[k][j],ids[k][j+1],ids[k+1][j+1],ids[k+1][j]),'pelo')
    for puntos in [
        [(-.096,-.037,1.679),(-.075,-.075,1.677),(-.087,-.048,1.570),(-.107,-.021,1.592)],
        [(-.075,-.075,1.680),(-.025,-.083,1.681),(-.059,-.089,1.648),(-.084,-.076,1.635)],
        [(-.025,-.083,1.681),(.025,-.083,1.682),(-.004,-.089,1.661),(-.038,-.088,1.648)],
        [(.025,-.083,1.682),(.075,-.073,1.680),(.101,-.035,1.580),(.072,-.063,1.601),(.040,-.085,1.645)],
        [(.075,-.073,1.680),(.100,-.028,1.674),(.105,-.018,1.577),(.086,-.036,1.580)]]:
        pieza(m,puntos,'pelo','cabeza',.009)


def sombrero(m):
    inicio=len(m.vertices)
    n=8;rings=[]
    for r in (.105,.310):
        ring=[]
        for i in range(n):
            a=math.tau*(i+.5)/n
            z=1.681
            ring.append((r*math.cos(a),r*.81*math.sin(a)+.004,z))
        rings.append(ring)
    m.anillos(rings,'sombrero','cabeza',tapas=False)
    m.anillos([[(x,y,z-.009) for x,y,z in ring] for ring in rings],'suela','cabeza',tapas=False)
    m.anillos([[(x,y,z-.009) for x,y,z in rings[-1]],rings[-1]],'sombrero','cabeza',tapas=False)
    datos=[(1.680,.112,.099),(1.703,.111,.097),(1.789,.095,.080),(1.810,.072,.069)]
    corona=[[(rx*math.cos(math.tau*(i+.5)/8),.008+ry*math.sin(math.tau*(i+.5)/8),z) for i in range(8)] for z,rx,ry in datos]
    m.anillos(corona,'sombrero','cabeza')
    # Un plano octogonal inclinado, sin deformar el ala como pétalos. Su raíz
    # atraviesa el casquete de pelo y la cabeza queda alojada dentro de la copa.
    from mathutils import Matrix
    giro=Matrix.Rotation(-.36,3,'X')
    pivote=Vector((0,.008,1.681))
    for i in range(inicio,len(m.vertices)):
        m.vertices[i]=tuple(pivote+giro @ (Vector(m.vertices[i])-pivote)+Vector((0,0,.038)))


def crear(material,rig):
    m=Malla()
    camisa_y_cuello(m);chaqueta(m);brazos_y_manos(m);piernas_y_zapatos(m)
    inicio_cabeza=len(m.vertices)
    rostro(m);pelo(m)
    # Medido sobre la comparación a la misma altura: la cabeza de la lámina es más ancha,
    # y el mentón queda tres centímetros por encima de la primera escultura de estudio.
    for i in range(inicio_cabeza,len(m.vertices)):
        x,y,z=m.vertices[i]
        m.vertices[i]=(x*1.15,y*1.10,1.454+(z-1.454)*1.10+.030)
    sombrero(m)
    obj=m.objeto('Sirviente_cuerpo',material,rig)
    for p in obj.data.polygons:p.use_smooth=False
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj
