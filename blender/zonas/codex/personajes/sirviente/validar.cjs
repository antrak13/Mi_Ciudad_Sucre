/* Validación del archivo exportado, no de una maqueta del rig. Instalar gltf-validator fuera del repo. */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const raiz=path.resolve(__dirname,'../../../../..');
const dir=path.join(raiz,'web/public/models/ciudad/codex/personajes/sirviente');
const rev=path.join(raiz,'revisiones/codex/sirviente_v2');
const archivo=fs.readFileSync(path.join(dir,'sirviente.glb'));
const longitud=archivo.readUInt32LE(12);
const gltf=JSON.parse(archivo.subarray(20,20+longitud));
const bin=archivo.subarray(28+longitud);
const config=JSON.parse(fs.readFileSync(path.join(dir,'sirviente.json')));
const tipos={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16};
const componentes={5121:[1,'readUInt8'],5123:[2,'readUInt16LE'],5125:[4,'readUInt32LE'],5126:[4,'readFloatLE']};
function leer(indice){
  const a=gltf.accessors[indice],v=gltf.bufferViews[a.bufferView];
  const [tam,metodo]=componentes[a.componentType],n=tipos[a.type],salida=[];
  for(let i=0;i<a.count;i++){
    const punto=[];for(let j=0;j<n;j++)punto.push(bin[metodo]((v.byteOffset||0)+(a.byteOffset||0)+i*(v.byteStride||tam*n)+j*tam));
    salida.push(punto);
  }
  return salida;
}
async function main(){
  const paquete=process.env.GLTF_VALIDATOR||'/tmp/miciudad-personajes-tools/node_modules/gltf-validator';
  const informe=await require(paquete).validateBytes(new Uint8Array(archivo),{maxIssues:1000});
  fs.writeFileSync(path.join(rev,'validacion_gltf.json'),JSON.stringify(informe,null,2));
  assert.equal(informe.issues.numErrors,0,'GLB con errores');
  assert.equal(informe.issues.numWarnings,0,'GLB con advertencias');
  const pruebas=[];
  function check(nombre,fn){fn();pruebas.push(nombre);}
  check('57 huesos con dedos completos',()=>{
    assert.equal(gltf.skins[0].joints.length,57);
    for(const suf of ['izq','der'])for(const dedo of ['pulgar','indice','medio','anular','menique'])for(let i=1;i<=3;i++)
      assert(gltf.nodes.some(n=>n.name===`${dedo}_${i}_${suf}`));
  });
  let triangulos=0;
  check('Piel sin vértices sin peso y máximo cuatro influencias',()=>{
    for(const mesh of gltf.meshes)for(const p of mesh.primitives){
      assert(p.attributes.JOINTS_0!==undefined&&p.attributes.WEIGHTS_0!==undefined);
      assert(p.attributes.WEIGHTS_1===undefined);
      for(const w of leer(p.attributes.WEIGHTS_0))assert(Math.abs(w.reduce((a,b)=>a+b,0)-1)<.00001);
      for(const j of leer(p.attributes.JOINTS_0))for(const v of j)assert(v<57);
      for(const v of leer(p.attributes.POSITION))for(const x of v)assert(Number.isFinite(x));
      triangulos+=gltf.accessors[p.indices].count/3;
    }
  });
  check('Dos mallas, dos imágenes embebidas y UV completos',()=>{
    assert.equal(gltf.meshes.length,2);assert.equal(gltf.images.length,2);
    for(const i of gltf.images)assert(i.bufferView!==undefined);
    for(const m of gltf.meshes)for(const p of m.primitives)assert(p.attributes.TEXCOORD_0!==undefined);
  });
  check('Diez clips con duración esperada y raíz inmóvil',()=>{
    assert.equal(gltf.animations.length,10);
    for(const [nombre,info] of Object.entries(config.movimiento)){
      const a=gltf.animations.find(a=>a.name===nombre);assert(a,`Falta ${nombre}`);
      const tiempos=leer(a.samplers[0].input).flat();
      assert(Math.abs(Math.max(...tiempos)-Math.round(info.duracion*24)/24)<.0001,nombre);
      for(const c of a.channels)if(gltf.nodes[c.target.node].name==='raiz'){
        const valores=leer(a.samplers[c.sampler].output);
        assert(valores.every(p=>p.every((v,i)=>Math.abs(v-valores[0][i])<.00001)),'La raíz se desplaza');
      }
    }
  });
  check('Bucles sin salto en las transformaciones de cierre',()=>{
    for(const a of gltf.animations.filter(a=>config.movimiento[a.name].bucle))for(const c of a.channels){
      const v=leer(a.samplers[c.sampler].output),x=v[0],y=v.at(-1);
      const directo=Math.max(...x.map((p,i)=>Math.abs(p-y[i])));
      const invertido=c.target.path==='rotation'?Math.max(...x.map((p,i)=>Math.abs(p+y[i]))):Infinity;
      assert(Math.min(directo,invertido)<.0001,`${a.name}/${gltf.nodes[c.target.node].name}/${c.target.path}`);
    }
  });
  check('Forro y carta articulados y con canales reales',()=>{
    const a=gltf.animations.find(a=>a.name==='mostrar_forro');
    for(const nombre of ['solapa_izq','carta'])assert(a.channels.some(c=>gltf.nodes[c.target.node].name===nombre));
    const s=a.channels.find(c=>gltf.nodes[c.target.node].name==='carta'&&c.target.path==='translation');
    const v=leer(a.samplers[s.sampler].output);
    assert(v.some(p=>p.some((x,i)=>Math.abs(x-v[0][i])>.09)));
  });
  const salida={resultado:'correcto',triangulos,bytes:archivo.length,pruebas,errores_gltf:0,advertencias_gltf:0};
  fs.writeFileSync(path.join(rev,'validacion_semantica.json'),JSON.stringify(salida,null,2));
  console.log(JSON.stringify(salida,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
