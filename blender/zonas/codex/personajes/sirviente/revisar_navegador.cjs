/* Revisión del GLB real con Chrome/CDP. No añade dependencias al proyecto. */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const raiz=path.resolve(__dirname,'../../../../..');
const rev=path.join(raiz,'revisiones/codex/sirviente_v2');
const pausa=ms=>new Promise(r=>setTimeout(r,ms));
async function main(){
  const tabs=await(await fetch('http://127.0.0.1:9348/json')).json();
  const tab=tabs.find(t=>t.type==='page');
  const ws=new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise(r=>ws.addEventListener('open',r,{once:true}));
  const pendientes=new Map(),errores=[],pruebas=[];let id=0;
  ws.addEventListener('message',e=>{
    const m=JSON.parse(e.data);
    if(m.id){const p=pendientes.get(m.id);if(p){pendientes.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}}
    if(m.method==='Runtime.exceptionThrown')errores.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  });
  const enviar=(method,params={})=>new Promise((resolve,reject)=>{const i=++id;pendientes.set(i,{resolve,reject});ws.send(JSON.stringify({id:i,method,params}));});
  async function evaluar(expression){const r=await enviar('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
  async function esperar(expression){for(let i=0;i<150;i++){if(await evaluar(expression))return;await pausa(200);}throw Error('No se cargó: '+expression);}
  async function captura(nombre){await pausa(250);const r=await enviar('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(rev,nombre+'.png'),Buffer.from(r.data,'base64'));}
  await enviar('Runtime.enable');await enviar('Page.enable');
  await enviar('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await enviar('Page.navigate',{url:'http://127.0.0.1:3024/models/ciudad/codex/personajes/sirviente/index.html'});
  await esperar('!!window.sirviente');
  const info=await evaluar(`({clips:sirviente.gltf.animations.map(a=>[a.name,a.duration]),mallas:sirviente.gltf.scene.children.map(x=>x.name),webgl:!!sirviente.renderer.getContext()})`);
  assert.equal(info.clips.length,10);assert(info.webgl);pruebas.push('GLB real cargado con diez clips');
  const res=await evaluar(`(()=>{
    const s=sirviente,p=s.personaje;
    const nombres=['reposo','caminar','caminar_rapido','sigilo','asentir','silencio','senalar','mirar_atras','apartarse','mostrar_forro'];
    const clips=[];
    for(const n of nombres){
      let minimo=Infinity,maximo=-Infinity,finito=true,maximoSuelo=-Infinity;
      for(let f=0;f<=12;f++){
        s.evaluar(n,f/12,false);p.objeto.updateMatrixWorld(true);let suelo=Infinity;
        p.objeto.traverse(o=>{if(o.isSkinnedMesh){o.skeleton.update();const v=o.position.clone();for(let i=0;i<o.geometry.attributes.position.count;i++){
          o.getVertexPosition(i,v);v.applyMatrix4(o.matrixWorld);
          finito&&=Number.isFinite(v.x)&&Number.isFinite(v.y)&&Number.isFinite(v.z);
          minimo=Math.min(minimo,v.y);maximo=Math.max(maximo,v.y);
          suelo=Math.min(suelo,v.y);
        }}});maximoSuelo=Math.max(maximoSuelo,suelo);
      }
      clips.push({nombre:n,minimo,maximo,maximoSuelo,finito});
    }
    s.evaluar('reposo',0);return clips;
  })()`);
  for(const r of res){assert(r.finito,r.nombre);assert(r.minimo>-.01,`${r.nombre} se hunde: ${r.minimo}`);assert(r.maximoSuelo<.015,`${r.nombre} flota: ${r.maximoSuelo}`);assert(r.maximo<2.1,`${r.nombre} deforma la malla`);}
  pruebas.push('13 poses por clip: malla finita, suelo entre -1 y +1,5 cm en cada pose');
  const mecanicas=await evaluar(`(()=>{
    const s=sirviente,p=s.personaje,m=p.objeto.getObjectByName('Sirviente_cuerpo');
    const movimientos=[];
    for(const n of ['caminar','caminar_rapido','sigilo']){
      s.evaluar(n,.15,false);p.objeto.updateMatrixWorld(true);const bone=p.objeto.getObjectByName('pie_izq');
      const a=bone.getWorldPosition(bone.position.clone());
      s.evaluar(n,.35,false);p.objeto.updateMatrixWorld(true);const b=bone.getWorldPosition(bone.position.clone());
      const v=-(b.z-a.z)/(.20*p.acciones.get(n).getClip().duration);
      movimientos.push({nombre:n,velocidadApoyo:v,referencia:s.configuracion.movimiento[n].velocidad_m_s,alturaA:a.y,alturaB:b.y});
    }
    s.evaluar('silencio',.5,false);p.objeto.updateMatrixWorld(true);m.skeleton.update();
    const h=m.skeleton.bones.findIndex(b=>b.name==='cabeza'),f=m.skeleton.bones.findIndex(b=>b.name==='indice_3_der');
    const boca=m.position.clone().set(0,1.5401,.0946).applyMatrix4(m.skeleton.boneInverses[h]).applyMatrix4(m.skeleton.bones[h].matrixWorld);
    let distanciaLabios=Infinity,cercano=null;
    const j=m.geometry.attributes.skinIndex,w=m.geometry.attributes.skinWeight;
    for(let i=0;i<j.count;i++)for(let k=0;k<4;k++)if(j.getComponent(i,k)===f&&w.getComponent(i,k)>.5){
      const v=m.position.clone();m.getVertexPosition(i,v);v.applyMatrix4(m.matrixWorld);const d=v.distanceTo(boca);if(d<distanciaLabios){distanciaLabios=d;cercano=v.toArray();}
    }
    return {movimientos,distanciaLabios,boca:boca.toArray(),indice:cercano};
  })()`);
  for(const r of mecanicas.movimientos){assert(Math.abs(r.velocidadApoyo-r.referencia)<.06,JSON.stringify(r));assert(Math.abs(r.alturaA-.135)<.006);assert(Math.abs(r.alturaB-.135)<.006);}
  assert(mecanicas.distanciaLabios<.035,`El índice no llega a los labios: ${JSON.stringify(mecanicas)}`);
  assert(mecanicas.indice[2]>=mecanicas.boca[2]-.003,'El índice atraviesa el rostro');
  pruebas.push('Velocidad del pie de apoyo coherente con navegación, tobillo a 13,5 cm e índice a menos de 3,5 cm de los labios');
  for(const v of ['estudio','espalda','rostro']){
    await evaluar(`sirviente.evaluar('reposo',0);sirviente.view('${v}')`);await captura('visor_'+v);
  }
  for(const n of ['caminar','silencio','senalar','mostrar_forro']){
    await evaluar(`sirviente.evaluar('${n}',.5);sirviente.view('${n==='mostrar_forro'?'forro':n==='silencio'||n==='senalar'?'rostro':'estudio'}')`);
    await captura('visor_'+n);
  }
  const acciones=await evaluar(`(()=>{
    const s=sirviente,p=s.personaje;
    s.evaluar('reposo',0);const anterior=p.objeto.getObjectByName('carta').position.clone();
    s.evaluar('mostrar_forro',.5);const distancia=anterior.distanceTo(p.objeto.getObjectByName('carta').position);
    p.reproducir('reposo',0);p.caminar(1.8);const marcha=p.actual;
    p.gesto('silencio');for(let i=0;i<200;i++)p.actualizar(1/60);const retorno=p.actual;
    const otra=new p.constructor(s.gltf,s.configuracion);s.scene.add(otra.objeto);
    s.evaluar('reposo',0);otra.gesto('senalar');otra.actualizar(1);
    p.objeto.updateMatrixWorld(true);otra.objeto.updateMatrixWorld(true);
    const q1=p.objeto.getObjectByName('brazo_der').quaternion.clone(),q2=otra.objeto.getObjectByName('brazo_der').quaternion;
    const independiente=1-Math.abs(q1.dot(q2));
    otra.destruir();s.scene.remove(otra.objeto);
    return {distancia,marcha,retorno,independiente};
  })()`);
  assert(acciones.distancia>.10);assert.equal(acciones.marcha,'caminar_rapido');assert.equal(acciones.retorno,'caminar_rapido');assert(acciones.independiente>.01);
  pruebas.push('Cambio de marcha, retorno tras gesto e instancias con esqueletos independientes');
  await evaluar(`document.querySelector('#esqueleto').click();sirviente.evaluar('caminar',.25);sirviente.view('estudio')`);await captura('visor_esqueleto');
  await evaluar(`document.querySelector('#esqueleto').click();document.querySelector('#malla').click()`);await captura('visor_topologia');
  await evaluar(`document.querySelector('#malla').click();document.querySelector('#referencia').click()`);
  assert(await evaluar(`document.querySelector('#lamina').open`));
  await evaluar(`document.querySelector('#cerrar-referencia').click()`);
  pruebas.push('Botones de esqueleto, topología y comparación con referencia');
  await enviar('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluar(`sirviente.evaluar('reposo',0);sirviente.view('estudio')`);await pausa(500);
  assert(await evaluar('document.documentElement.scrollWidth<=innerWidth'));
  await captura('visor_movil');pruebas.push('390 px sin desbordamiento');
  assert.equal(errores.length,0,errores.join('\n'));
  const informe={resultado:'correcto',pruebas,info,poses:res,mecanicas,acciones,errores};
  fs.writeFileSync(path.join(rev,'revision_navegador.json'),JSON.stringify(informe,null,2));
  console.log(JSON.stringify(informe,null,2));ws.close();
}
main().catch(e=>{console.error(e);process.exit(1);});
