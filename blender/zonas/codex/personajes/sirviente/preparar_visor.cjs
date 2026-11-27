const path=require('node:path');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const raiz=path.resolve(__dirname,'../../../../..');
const requireWeb=createRequire(path.join(raiz,'web/package.json'));
const salida=path.join(raiz,'web/public/models/ciudad/codex/personajes/sirviente');
const bundler=requireWeb('next/dist/compiled/webpack/webpack');
bundler.init();
bundler.webpack({mode:'production',entry:path.join(__dirname,'visor.js'),output:{path:salida,filename:'visor.bundle.js'},
  resolve:{modules:[path.join(raiz,'web/node_modules')]},optimization:{minimize:false},performance:{hints:false},devtool:false},
  async(error,stats)=>{
    if(error||stats.hasErrors()){console.error(error||stats.toString({all:false,errors:true}));process.exitCode=1;return;}
    const {minify}=requireWeb('next/dist/compiled/terser');
    const file=path.join(salida,'visor.bundle.js');
    const result=await minify(fs.readFileSync(file,'utf8'),{compress:{passes:1},mangle:true,format:{comments:/^!/}});
    fs.writeFileSync(file,result.code);
    for(const nombre of ['index.html','personaje_animado.mjs','LEEME.md'])
      if(fs.existsSync(path.join(__dirname,nombre)))fs.copyFileSync(path.join(__dirname,nombre),path.join(salida,nombre));
    const datos=JSON.parse(fs.readFileSync(path.join(__dirname,'diseno.json'),'utf8'));
    const original=path.join(raiz,datos.referencia);
    if(fs.existsSync(original))fs.copyFileSync(original,path.join(salida,'referencia.png'));
    else if(!fs.existsSync(path.join(salida,'referencia.png')))throw new Error('Falta la nueva referencia del personaje');
    fs.copyFileSync(path.join(raiz,'web/node_modules/three/LICENSE'),path.join(salida,'THREE-LICENSE.txt'));
    console.log('Visor del personaje preparado:',file);
  });
