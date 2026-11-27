import { AnimationMixer, LoopOnce, LoopRepeat } from 'three';
import { clone } from 'three/addons/utils/SkeletonUtils.js';

/** Instancia independiente. El juego aporta navegación, colisiones y percepción. */
export class PersonajeAnimado {
  constructor(gltf, configuracion, { clonar = true } = {}) {
    this.objeto = clonar ? clone(gltf.scene) : gltf.scene;
    this.configuracion = configuracion;
    this.mixer = new AnimationMixer(this.objeto);
    this.acciones = new Map(gltf.animations.map(clip => [clip.name, this.mixer.clipAction(clip)]));
    this.actual = null;
    this.gestoActivo = false;
    this.locomocion = 'reposo';
    this.velocidad = 0;
    this.mixer.addEventListener('finished', () => {
      this.gestoActivo = false;
      this.reproducir(this.locomocion);
    });
    this.reproducir('reposo', 0);
  }

  reproducir(nombre, fundido = .18) {
    const accion = this.acciones.get(nombre);
    if (!accion) throw new Error(`Clip inexistente: ${nombre}`);
    if (this.actual === nombre) return accion;
    const anterior = this.acciones.get(this.actual);
    accion.reset().setEffectiveWeight(1).setEffectiveTimeScale(1);
    const bucle = this.configuracion.movimiento[nombre].bucle;
    accion.setLoop(bucle ? LoopRepeat : LoopOnce, bucle ? Infinity : 1);
    accion.clampWhenFinished = !bucle;
    accion.enabled = true;
    accion.play();
    if (anterior && fundido > 0) anterior.crossFadeTo(accion, fundido, false);
    else if (anterior) anterior.stop();
    this.actual = nombre;
    return accion;
  }

  /** Velocidad REAL de navegación, en m/s; no mueve el objeto por su cuenta. */
  caminar(velocidad = 0, sigilo = false) {
    if (!Number.isFinite(velocidad)) throw new Error('La velocidad debe ser finita');
    this.velocidad = Math.abs(velocidad);
    const nombre = this.velocidad < .035 ? 'reposo' : sigilo ? 'sigilo' : this.velocidad > 1.45 ? 'caminar_rapido' : 'caminar';
    this.locomocion = nombre;
    if (!this.gestoActivo) {
      const accion = this.reproducir(nombre);
      const referencia = this.configuracion.movimiento[nombre].velocidad_m_s;
      accion.setEffectiveTimeScale(referencia ? this.velocidad / referencia : 1);
    }
  }

  gesto(nombre) {
    const info = this.configuracion.movimiento[nombre];
    if (!info || info.bucle) throw new Error(`Se esperaba un gesto: ${nombre}`);
    this.gestoActivo = true;
    // Permitir repetir el mismo gesto sin acumular acciones.
    if (this.actual === nombre) this.actual = null;
    this.reproducir(nombre);
  }

  actualizar(dt) {
    if (!Number.isFinite(dt) || dt < 0) throw new Error('dt debe ser finito y positivo');
    // No perder tiempo en pantallas lentas. El motor puede limitar dt al volver de pausa.
    this.mixer.update(dt);
  }

  destruir() {
    this.mixer.stopAllAction();
    this.mixer.uncacheRoot(this.objeto);
    // Geometría y materiales pertenecen al recurso compartido, no a esta instancia.
  }
}
