import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { PersonajeAnimado } from './personaje_animado.mjs';
import configuracion from './diseno.json';

const $ = s => document.querySelector(s);
let sucio=true;
const canvas = $('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#b3a49a');
scene.fog = new THREE.Fog('#b3a49a', 8, 18);
const camera = new THREE.PerspectiveCamera(32, 1, .01, 80);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.target.set(0, .94, 0);
controls.minDistance = .22;
controls.maxDistance = 7;
controls.maxPolarAngle = Math.PI*.53;
scene.add(new THREE.HemisphereLight('#ffeed8', '#7c6a61', 1.9));
scene.add(new THREE.AmbientLight('#eadcc9', .65));
const light = new THREE.DirectionalLight('#fff0da', 3);
light.position.set(3, 5, 4);
light.castShadow = true;
light.shadow.mapSize.set(2048, 2048);
Object.assign(light.shadow.camera, {left:-2,right:2,top:3,bottom:-1,near:.1,far:12});
light.shadow.bias = -.0001;
light.shadow.normalBias = .008;
scene.add(light);
const fill = new THREE.DirectionalLight('#e1e7ff', 1.2);
fill.position.set(-3, 2, -2);scene.add(fill);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:'#ac9d93',roughness:1}));
ground.rotation.x=-Math.PI/2;ground.position.y=-.002;ground.receiveShadow=true;scene.add(ground);
const views = {
  estudio: [[-1.55,1.65,3.3],[0,.94,0]],
  frente: [[0,1.1,3.9],[0,.94,0]],
  perfil: [[3.9,1.1,0],[0,.94,0]],
  espalda: [[1.55,1.65,-3.3],[0,.94,0]],
  rostro: [[-.25,1.68,.88],[0,1.59,0]],
  forro: [[.95,1.5,.95],[.12,1.28,.08]],
};
function view(name) {
  sucio=true;
  const [p,t]=views[name];camera.position.fromArray(p);controls.target.fromArray(t);controls.update();
  document.querySelectorAll('[data-vista]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.vista===name)));
}
view('estudio');
let personaje, skeleton, current='reposo', paused=false, wire=false, automatic=false, timeScale=1;
const status = $('#estado');
function select(name) {
  if (!personaje) return;
  current=name;
  sucio=true;
  personaje.gestoActivo=false;
  personaje.reproducir(name);
  const info=configuracion.movimiento[name];
  $('#descripcion').textContent=info.velocidad_m_s ? `${info.velocidad_m_s.toLocaleString('es')} m/s · movimiento en sitio` : name==='reposo' ? 'Protege la carta y observa en silencio.' : 'Gesto silencioso · vuelve a reposo al terminar.';
  document.querySelectorAll('[data-clip]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.clip===name)));
}
document.querySelectorAll('[data-clip]').forEach(b=>b.addEventListener('click',()=>select(b.dataset.clip)));
document.querySelectorAll('[data-vista]').forEach(b=>b.addEventListener('click',()=>view(b.dataset.vista)));
$('#pausa').addEventListener('click',e=>{paused=!paused;e.currentTarget.textContent=paused?'Continuar':'Pausar';e.currentTarget.setAttribute('aria-pressed',String(paused));});
$('#esqueleto').addEventListener('click',e=>{if(skeleton){skeleton.visible=!skeleton.visible;sucio=true;e.currentTarget.setAttribute('aria-pressed',String(skeleton.visible));}});
$('#malla').addEventListener('click',e=>{wire=!wire;sucio=true;personaje?.objeto.traverse(o=>{if(o.isMesh)o.material.wireframe=wire;});e.currentTarget.setAttribute('aria-pressed',String(wire));});
$('#girar').addEventListener('click',e=>{automatic=!automatic;e.currentTarget.setAttribute('aria-pressed',String(automatic));});
$('#velocidad').addEventListener('input',e=>{timeScale=Number(e.target.value);$('#valor-velocidad').textContent=timeScale.toFixed(2)+'×';});
$('#tiempo').addEventListener('input',e=>{
  if(!personaje)return;
  const action=personaje.acciones.get(personaje.actual);
  action.time=Number(e.target.value)*action.getClip().duration;
  personaje.mixer.update(0);
  sucio=true;
  paused=true;$('#pausa').textContent='Continuar';$('#pausa').setAttribute('aria-pressed','true');
});
$('#referencia').addEventListener('click',()=>$('#lamina').showModal());
$('#cerrar-referencia').addEventListener('click',()=>$('#lamina').close());
$('#descoser').addEventListener('click',()=>{select('mostrar_forro');view('forro');});
new GLTFLoader().load('sirviente.glb', gltf=>{
  personaje=new PersonajeAnimado(gltf,configuracion,{clonar:false});
  personaje.objeto.traverse(o=>{
    if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false;}
  });
  scene.add(personaje.objeto);
  skeleton=new THREE.SkeletonHelper(personaje.objeto);skeleton.visible=false;
  skeleton.material.depthTest=false;skeleton.material.transparent=true;skeleton.material.opacity=.85;
  scene.add(skeleton);
  let triangles=0, bones=0;
  personaje.objeto.traverse(o=>{if(o.isBone)bones++;if(o.isMesh)triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;});
  $('#datos').textContent=`${Math.round(triangles).toLocaleString('es')} triángulos · ${bones} huesos · ${gltf.animations.length} clips`;
  status.textContent='Modelo listo';status.classList.add('listo');
  window.sirviente={personaje,gltf,scene,camera,renderer,controls,select,view,configuracion,
    get pausado(){return paused;}, set pausado(v){paused=v;},
    evaluar(nombre,t,dibujar=true){select(nombre);const a=personaje.acciones.get(nombre);personaje.mixer.stopAllAction();a.reset().play();a.time=t*a.getClip().duration;personaje.mixer.update(0);paused=true;if(dibujar)renderer.render(scene,camera);},
  };
},undefined,error=>{status.textContent='No se pudo cargar el modelo';console.error(error);});
function size(){const r=canvas.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();sucio=true;}
new ResizeObserver(size).observe(canvas);size();
let last;
renderer.setAnimationLoop(now=>{
  const dt=last===undefined?0:Math.min(.1,(now-last)/1000);last=now;
  if(personaje&&!paused)personaje.actualizar(dt*timeScale);
  if(automatic){camera.position.sub(controls.target).applyAxisAngle(new THREE.Vector3(0,1,0),dt*.25).add(controls.target);}
  if(personaje){
    const action=personaje.acciones.get(personaje.actual);
    $('#tiempo').value=action.time/action.getClip().duration;
    if(current!==personaje.actual){current=personaje.actual;document.querySelectorAll('[data-clip]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.clip===current)));}
  }
  const cambio=controls.update();
  if(!paused||automatic||cambio||sucio)renderer.render(scene,camera);
  sucio=false;
});
