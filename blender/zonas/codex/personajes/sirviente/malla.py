"""Herramientas de malla con UV y pesos explícitos; no usa parentado automático."""
import math
import bpy
from mathutils import Vector

ROLES = ['chaqueta', 'calzon', 'sombrero', 'piel', 'camisa', 'forro', 'pelo', 'zapato',
         'suela', 'boton', 'papel', 'costura', 'ojo', 'iris', 'boca', 'cinto']


class Malla:
    def __init__(self):
        self.vertices, self.caras, self.pesos, self.uvs, self.roles = [], [], [], [], []
        self.suaves=set()

    def vertice(self, p, peso):
        self.vertices.append(tuple(p))
        self.pesos.append({peso: 1.0} if isinstance(peso, str) else peso)
        return len(self.vertices)-1

    def cara(self, inds, rol, uv=None):
        self.caras.append(tuple(inds))
        self.roles.append(rol)
        i = ROLES.index(rol)
        if uv is None:
            # Coordenadas físicas: cuadrados discretos sobre todas las piezas del traje.
            puntos = [Vector(self.vertices[j]) for j in inds]
            normal = (puntos[1]-puntos[0]).cross(puntos[2]-puntos[0])
            eje = max(range(3), key=lambda a: abs(normal[a]))
            ejes = [a for a in range(3) if a != eje]
            # Trasladar toda la cara junta. Aplicar módulo por vértice estiraría el tejido
            # en triángulos gigantes al cruzar el límite de una celda del atlas.
            uv = [[0,0] for p in puntos]
            for a in range(2):
                valores=[p[ejes[a]]*1.75 for p in puntos]
                minimo=min(valores); extension=max(valores)-minimo
                inicio=minimo % .90
                if inicio+extension>.96: inicio=.03
                escala=min(1,.90/max(.001,extension))
                for k,v in enumerate(valores): uv[k][a]=inicio+(v-minimo)*escala
        self.uvs.append([((i % 4 + .015 + u*.97)/4, (3-i//4+.015+v*.97)/4) for u, v in uv])

    def poligono(self, puntos, rol, peso):
        inds = [self.vertice(p, peso) for p in puntos]
        self.cara(inds, rol)
        return inds

    def anillos(self, anillos, rol, pesos, tapas=True):
        """Anillos ordenados antihorario vistos desde arriba. Pesos por anillo."""
        n = len(anillos[0])
        ids = [[self.vertice(p, pesos[k] if isinstance(pesos, list) else pesos) for p in ring]
               for k, ring in enumerate(anillos)]
        for k in range(len(ids)-1):
            for j in range(n):
                self.cara((ids[k][j], ids[k][(j+1) % n], ids[k+1][(j+1) % n], ids[k+1][j]), rol)
        if tapas:
            self.cara(list(reversed(ids[0])), rol)
            self.cara(ids[-1], rol)
        return ids

    def elipses(self, datos, rol, pesos, n=12, tapas=True):
        return self.anillos([[(x+rx*math.cos(a*math.tau/n), y+ry*math.sin(a*math.tau/n), z)
                              for a in range(n)] for x,y,z,rx,ry in datos], rol, pesos, tapas)

    def tubo(self, puntos, radios, rol, pesos, n=8, elipse=1, suave=False):
        inicio=len(self.caras)
        rings = []
        for k, p in enumerate(puntos):
            p = Vector(p)
            direccion = Vector(puntos[min(k+1,len(puntos)-1)])-Vector(puntos[max(k-1,0)])
            direccion.normalize()
            u = direccion.cross(Vector((0,1,0))).normalized()
            if u.length < .1:
                u = direccion.cross(Vector((1,0,0))).normalized()
            v = direccion.cross(u).normalized()
            rings.append([p+radios[k]*(u*math.cos(j*math.tau/n)+v*elipse*math.sin(j*math.tau/n)) for j in range(n)])
        resultado=self.anillos(rings, rol, pesos)
        if suave:self.suaves.update(range(inicio,len(self.caras)-2))
        return resultado

    def caja(self, centro, tamano, rol, peso, bisel=0):
        x,y,z = centro
        w,d,h = [t/2 for t in tamano]
        if not bisel:
            anillos = [[(x+sx*w,y+sy*d,z+sz*h) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))] for sz in (-1,1)]
        else:
            xy = [(-w+bisel,-d),(w-bisel,-d),(w,-d+bisel),(w,d-bisel),(w-bisel,d),(-w+bisel,d),(-w,d-bisel),(-w,-d+bisel)]
            anillos = [[(x+a,y+b,z+sz*h) for a,b in xy] for sz in (-1,1)]
        return self.anillos(anillos, rol, peso)

    def bola(self, centro, escala, rol, peso, n=10, m=6):
        x,y,z = centro
        rx,ry,rz = escala
        datos = []
        for k in range(m+1):
            a = -math.pi/2+.015+(math.pi-.03)*k/m
            datos.append((x,y,z+rz*math.sin(a),rx*math.cos(a),ry*math.cos(a)))
        return self.elipses(datos,rol,peso,n)

    def objeto(self, nombre, material, rig):
        mesh = bpy.data.meshes.new(nombre)
        mesh.from_pydata(self.vertices, [], self.caras)
        mesh.update()
        obj = bpy.data.objects.new(nombre, mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(material)
        uv = mesh.uv_layers.new(name='Atlas')
        for i,(face, coords, rol) in enumerate(zip(mesh.polygons, self.uvs, self.roles)):
            face.use_smooth=rol in ('piel','ojo','iris') or i in self.suaves
            for li, t in zip(face.loop_indices, coords):
                uv.data[li].uv = t
        grupos = {}
        for i,pesos in enumerate(self.pesos):
            total = sum(pesos.values())
            for nombre,peso in pesos.items():
                if peso > 0:
                    if nombre not in grupos:
                        grupos[nombre] = obj.vertex_groups.new(name=nombre)
                    grupos[nombre].add([i],peso/total,'REPLACE')
        # Los nodos de malla skinned son raíces en glTF. El modificador basta para
        # relacionarlos al armature; parentarlos además dispara NODE_SKINNED_MESH_NON_ROOT.
        mod = obj.modifiers.new('Deformacion_esqueleto', 'ARMATURE')
        mod.object = rig
        return obj
