// Interacciones vinculadas al encuadre original de cada fotografía.
// Proyección cover compartida por foto, contorno y superficie de pulsación.
(() => {
  const hero = document.querySelector('.opening'), body = document.body;
  const svg = hero.querySelector('.landmark-svg'), trigger = hero.querySelector('[data-landmark]');
  const light = hero.querySelector('.scene-light');
  const pointer = hero.querySelector('.scene-pointer');
  const panel = hero.querySelector('[data-city-panel]');
  const heroWorkPanel = hero.querySelector('[data-hero-panel]');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const b = body.dataset.variant === 'B';
  const shape = b ? {
    width: 1532, height: 1026,
    points: [[1205,813],[1205,730],[1213,730],[1213,700],[1220,700],[1220,624],[1212,624],[1212,610],[1223,610],[1223,584],[1229,584],[1229,567],[1236,567],[1236,553],[1230,553],[1230,539],[1240,539],[1240,521],[1245,521],[1245,534],[1255,534],[1285,486],[1285,476],[1291,476],[1291,487],[1321,535],[1333,535],[1333,519],[1339,519],[1339,538],[1347,538],[1347,552],[1340,552],[1340,569],[1349,569],[1349,586],[1355,586],[1355,610],[1364,610],[1364,625],[1357,625],[1357,700],[1371,700],[1371,719],[1362,719],[1362,813]],
    details: 'M1220 624H1357 M1220 700H1357 M1213 730H1362 M1230 553H1347 M1229 584H1349 M1260 653V681 M1292 653V681 M1321 653V681 M1280 582L1280 593L1290 593'
  } : {
    width: 1673, height: 940,
    points: [[572,728],[572,547],[565,547],[565,532],[578,532],[578,500],[584,500],[584,398],[578,398],[578,380],[591,380],[591,313],[584,313],[584,282],[599,282],[599,228],[607,228],[607,208],[612,208],[612,176],[619,176],[619,198],[633,198],[654,143],[654,129],[651,129],[651,113],[641,113],[641,108],[651,108],[651,99],[657,99],[657,108],[668,108],[668,113],[657,113],[657,129],[660,129],[660,143],[684,198],[698,198],[698,176],[704,176],[704,208],[713,208],[713,228],[720,228],[720,282],[729,282],[729,313],[721,313],[721,380],[734,380],[734,398],[728,398],[728,500],[738,500],[738,532],[752,532],[752,547],[740,547],[740,728]],
    details: 'M584 398H728 M578 532H738 M599 282H720 M607 228H713 M614 340V365 M648 340V365 M684 340V365 M621 455V480 M654 455V480 M691 455V480 M654 249V263L665 263'
  };
  if(b){
    const tower=shape.points;
    shape.points=[[68,847],[72,822],[80,822],[80,806],[94,806],[94,792],[101,792],[101,819],[127,819],[132,785],[139,785],[139,760],[146,760],[146,734],[151,734],[151,712],[161,712],[163,692],[170,692],[172,683],[180,683],[183,695],[192,695],[195,714],[205,714],[205,755],[214,755],[214,785],[225,785],[232,760],[244,740],[261,722],[280,709],[302,702],[316,700],[316,690],[323,690],[324,681],[334,681],[340,690],[340,701],[361,704],[384,716],[407,737],[423,764],[429,785],[442,785],[442,776],[450,776],[450,797],[477,797],[477,785],[487,785],[487,797],[520,797],[520,780],[532,780],[532,795],[552,795],[552,780],[563,780],[563,746],[576,746],[580,732],[588,720],[602,709],[609,698],[609,691],[617,691],[618,701],[629,713],[642,730],[647,746],[658,746],[658,782],[670,782],[670,797],[697,797],[697,782],[706,782],[706,794],[734,794],[734,779],[744,779],[744,797],[774,797],[774,785],[784,785],[784,800],[1010,800],[1018,789],[1029,783],[1044,780],[1057,782],[1070,791],[1076,801],[1108,803],[1118,790],[1143,794],[1154,805],[1205,813],...tower.slice(1),[1390,819],[1390,844],[1424,864],[1416,916],[1373,932],[1000,932],[921,917],[900,922],[860,919],[803,910],[597,924],[399,910],[215,911],[215,861],[68,861]];
    shape.details+=' M215 820H1200 M236 780Q245 705 331 702Q409 709 429 785 M565 746H650 M580 733Q613 686 647 746 M1015 801H1075 M1112 816L1183 840 M87 838H215 M446 851H1040 M326 704V778 M303 707L280 778 M352 707L384 778';
  }
  const d = 'M' + shape.points.map(p => p.join(',')).join('L') + 'Z';
  svg.setAttribute('viewBox', `0 0 ${shape.width} ${shape.height}`);
  svg.querySelectorAll('path:not(.outline-details)').forEach(path => path.setAttribute('d', d));
  svg.querySelector('.outline-details').setAttribute('d', shape.details);
  const xs = shape.points.map(p => p[0]), ys = shape.points.map(p => p[1]);
  const box = { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
  trigger.style.clipPath = 'polygon(' + shape.points.map(p => `${(p[0] - box.x) / box.w * 100}% ${(p[1] - box.y) / box.h * 100}%`).join(',') + ')';
  let projection,panelAnchor,lastMouse,dismissedAt;
  function fit() {
    const w = hero.clientWidth, h = hero.clientHeight;
    const scale = Math.max(w / shape.width, h / shape.height);
    const pos = b ? (w <= 760 ? .90 : .64) : (w <= 760 ? .39 : .40);
    const x = (w - shape.width * scale) * pos, y = (h - shape.height * scale) * .5;
    projection = { x, y, scale };
    Object.assign(svg.style, { width: shape.width * scale + 'px', height: shape.height * scale + 'px', left: x + 'px', top: y + 'px' });
    const tx = x + box.x * scale, ty = y + box.y * scale, tw = box.w * scale, th = box.h * scale;
    Object.assign(trigger.style, { left: tx + 'px', top: ty + 'px', width: tw + 'px', height: th + 'px' });
    if(!panel.hidden)positionPanel();
    // Publicado para revisar alineación en escritorio, móvil y diferentes relaciones de aspecto.
    hero.sceneProjection = { ...projection, box: { x: tx, y: ty, w: tw, h: th } };
  }
  new ResizeObserver(fit).observe(hero); fit();
  let closeTimer, pinned=false;
  function positionPanel(){
    if(!panelAnchor)return;
    const rect=hero.getBoundingClientRect(),button=panel.querySelector('[data-enter]');
    const point={x:panelAnchor.x-rect.left,y:panelAnchor.y-rect.top};
    button.style.alignSelf='';
    panel.classList.remove('panel-below');
    panel.style.left='0px';panel.style.top='0px';
    let local=button.getBoundingClientRect(),card=panel.getBoundingClientRect();
    let bx=local.left-card.left+local.width/2,by=local.top-card.top+local.height/2;
    if(point.y-by<8){
      panel.classList.add('panel-below');local=button.getBoundingClientRect();card=panel.getBoundingClientRect();
      bx=local.left-card.left+local.width/2;by=local.top-card.top+local.height/2;
    }
    const left=Math.max(8,Math.min(hero.clientWidth-card.width-8,point.x-bx));
    const top=Math.max(8,Math.min(hero.clientHeight-card.height-8,point.y-by));
    panel.style.left=left+'px';panel.style.top=top+'px';
    const actual=button.getBoundingClientRect();
    if(panelAnchor.x>actual.right){button.style.alignSelf='flex-end';}
  }
  function setActive(active) {
    clearTimeout(closeTimer);
    hero.classList.toggle('landmark-active', active);
    trigger.dataset.active = String(active);
    trigger.setAttribute('aria-expanded',String(active));
    panel.hidden=!active;panel.inert=!active;
  }
  function openAt(event,force=false){
    if(!panel.hidden&&!force){clearTimeout(closeTimer);return;}
    const rect=trigger.getBoundingClientRect();
    panelAnchor=event&&Number.isFinite(event.clientX)&&event.clientX!==0?{x:event.clientX,y:event.clientY}:{x:rect.left+rect.width/2,y:rect.top+rect.height*.4};
    setActive(true);positionPanel();
  }
  function scheduleClose(event){
    if(event&&Number.isFinite(event.clientX))lastMouse={x:event.clientX,y:event.clientY};
    clearTimeout(closeTimer);closeTimer=setTimeout(()=>{
      const r=panel.getBoundingClientRect();
      const overPanel=lastMouse&&lastMouse.x>=r.left&&lastMouse.x<=r.right&&lastMouse.y>=r.top&&lastMouse.y<=r.bottom;
      if(!pinned&&!overPanel&&!trigger.matches(':focus')&&!panel.contains(document.activeElement))setActive(false);
    },260);
  }
  trigger.addEventListener('pointerenter', event => { if(event.pointerType==='mouse'&&(!dismissedAt||Math.hypot(event.clientX-dismissedAt.x,event.clientY-dismissedAt.y)>34))openAt(event); });
  trigger.addEventListener('pointerleave',scheduleClose);
  trigger.addEventListener('focus', () => {if(!dismissedAt)openAt();});
  trigger.addEventListener('blur',scheduleClose);
  trigger.addEventListener('click',event=>{dismissedAt=null;pinned=true;openAt(event,event.pointerType==='touch');panel.querySelector('[data-enter]').focus({preventScroll:true});});
  panel.addEventListener('pointerenter',()=>clearTimeout(closeTimer));panel.addEventListener('pointerleave',scheduleClose);
  panel.addEventListener('focusin',()=>clearTimeout(closeTimer));panel.addEventListener('focusout',scheduleClose);
  const closePanel=(suppress=false)=>{pinned=false;if(suppress)dismissedAt=lastMouse||panelAnchor;setActive(false);};
  panel.querySelector('[data-panel-close]').addEventListener('click',()=>{closePanel(true);trigger.focus({preventScroll:true});});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden){event.preventDefault();event.stopImmediatePropagation();closePanel(true);trigger.focus({preventScroll:true});}});
  document.addEventListener('pointerdown',event=>{if(!panel.hidden&&!panel.contains(event.target)&&event.target!==trigger)closePanel();});
  let frame = 0, lastPoint;
  function update() {
    frame = 0; if (!lastPoint) return;
    const rect = hero.getBoundingClientRect(), x = lastPoint.x - rect.left, y = lastPoint.y - rect.top;
    const onControl = lastPoint.target.closest('button,a,summary,[data-city-panel]');
    const enabled = !body.classList.contains('ambiente-pausado') && !motion.matches;
    hero.classList.toggle('scene-awake', enabled);
    hero.classList.toggle('pointer-visible', enabled && (!onControl || onControl === trigger));
    light.style.setProperty('--lx', x + 'px'); light.style.setProperty('--ly', y + 'px');
    pointer.style.transform = `translate(${x}px,${y}px)`;
  }
  hero.addEventListener('pointermove', event => {
    if (event.pointerType !== 'mouse' || body.classList.contains('entering')) return;
    lastMouse={x:event.clientX,y:event.clientY};
    if(dismissedAt&&Math.hypot(event.clientX-dismissedAt.x,event.clientY-dismissedAt.y)>34){dismissedAt=null;if(event.target===trigger)openAt(event);}
    hero.classList.add('mouse-present');
    lastPoint = { x: event.clientX, y: event.clientY, target: event.target };
    if (!frame) frame = requestAnimationFrame(update);
  });
  hero.addEventListener('pointerleave', event => { hero.classList.remove('scene-awake', 'pointer-visible');scheduleClose(event); });
  new MutationObserver(() => {
    if (body.classList.contains('ambiente-pausado') || body.classList.contains('entering')) hero.classList.remove('scene-awake', 'pointer-visible');
    if(body.classList.contains('entering'))closePanel();
  }).observe(body, { attributes: true, attributeFilter: ['class'] });
  const nav=document.querySelector('.project-nav'),header=document.querySelector('.clean-header');
  const syncHeader=()=>{const onPaper=scrollY>hero.clientHeight-header.offsetHeight-24;header.classList.toggle('header-on-paper',onPaper);if(!onPaper)nav.querySelectorAll('[aria-current]').forEach(link=>link.removeAttribute('aria-current'));};
  addEventListener('scroll',syncHeader,{passive:true});addEventListener('resize',syncHeader);syncHeader();
  const goToSection=(event)=>{
    const link=event.currentTarget,target=document.querySelector(link.hash);if(!target)return;
    event.preventDefault();closePanel();
    const top=scrollY+target.getBoundingClientRect().top-header.getBoundingClientRect().height-20;
    window.scrollTo({top,behavior:motion.matches?'instant':'smooth'});history.replaceState(null,'',link.hash);
  };
  nav.querySelectorAll('a').forEach(link=>link.addEventListener('click',goToSection));
  document.querySelector('.scroll-cue').addEventListener('click',goToSection);
  heroWorkPanel?.querySelector('.hero-work-more')?.addEventListener('click',goToSection);
  if(heroWorkPanel){
    const items=[...heroWorkPanel.querySelectorAll('[data-preview-item]')];
    const imgA=heroWorkPanel.querySelector('[data-bg-a]');
    const imgB=heroWorkPanel.querySelector('[data-bg-b]');
    const pTag=heroWorkPanel.querySelector('[data-preview-tag]');
    const pTitle=heroWorkPanel.querySelector('[data-preview-title]');
    const pDesc=heroWorkPanel.querySelector('[data-preview-desc]');
    let useA=true, autoIdx=0, autoTimer=null;

    const selectItem=(btn,manual=false)=>{
      if(manual && autoTimer){clearInterval(autoTimer);autoTimer=null;}
      items.forEach(el=>{
        const on=el===btn;
        el.classList.toggle('is-active',on);
        el.setAttribute('aria-selected',String(on));
      });
      const src=btn.dataset.src;
      if(src&&imgA&&imgB){
        const next=useA?imgB:imgA;
        const curr=useA?imgA:imgB;
        if(next.getAttribute('src')!==src)next.src=src;
        next.classList.add('is-visible');
        curr.classList.remove('is-visible');
        useA=!useA;
      }
      if(pTag)pTag.textContent=btn.dataset.tag||'';
      if(pTitle)pTitle.textContent=btn.dataset.title||'';
      if(pDesc)pDesc.textContent=btn.dataset.desc||'';
    };

    items.forEach((btn,idx)=>{
      btn.addEventListener('pointerenter',()=>{autoIdx=idx;selectItem(btn,true);});
      btn.addEventListener('focus',()=>{autoIdx=idx;selectItem(btn,true);});
      btn.addEventListener('click',()=>{autoIdx=idx;selectItem(btn,true);});
    });

    setTimeout(()=>{
      if(body.classList.contains('entrando'))return;
      hero.classList.add('opening-swapped');
      heroWorkPanel.hidden=false;
      heroWorkPanel.setAttribute('aria-hidden','false');
      void heroWorkPanel.offsetWidth;
      hero.classList.add('opening-panel-visible');
      if(!motion.matches && items.length>1){
        autoTimer=setInterval(()=>{
          if(body.classList.contains('entrando')||heroWorkPanel.hidden)return;
          autoIdx=(autoIdx+1)%items.length;
          selectItem(items[autoIdx],false);
        },4000);
      }
    },4200);
  }
  const sections=[...nav.querySelectorAll('a')].map(link=>({link,section:document.querySelector(link.hash)}));
  const sectionObserver=new IntersectionObserver(entries=>{
    for(const entry of entries){if(!entry.isIntersecting)continue;sections.forEach(({link,section})=>{if(section===entry.target)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});}
  },{rootMargin:'-15% 0px -55% 0px'});
  sections.forEach(({section})=>{if(section)sectionObserver.observe(section);});
  window.escenaLanding = { fit, shape, get projection() { return hero.sceneProjection; } };
})();
