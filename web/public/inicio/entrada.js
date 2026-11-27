// Portada MiCiudad: cielo animado sobre la fotografía, silueta interactiva (escena.js) y paso a la ciudad 3D real.
// La ciudad se carga en segundo plano (iframe /ciudad?embebido) mientras se lee la portada: al entrar ya está lista y no hay
// pantalla de carga. La entrada es un travelling hacia la torre que se funde en una luz cálida de la que emerge la plaza.
(() => {
  const reducido = matchMedia('(prefers-reduced-motion: reduce)');
  const lienzo = document.querySelector('[data-clouds]');
  const cielo = lienzo ? new CieloSucre(lienzo, '/inicio/img/panorama.jpg') : null;
  const pausar = () => { document.body.classList.toggle('ambiente-pausado', reducido.matches); if (cielo) cielo.paused = reducido.matches; };
  pausar(); reducido.addEventListener('change', pausar);

  // La ciudad 3D es para computadora; en celular y tableta se lleva a la instalación de la app.
  const nav = navigator;
  const movil = !!(nav.userAgentData && nav.userAgentData.mobile) || /Android|iPhone|iPad|iPod|Mobile/i.test(nav.userAgent)
    || (/Macintosh/.test(nav.userAgent) && nav.maxTouchPoints > 1);
  if (movil) {
    document.querySelectorAll('[data-enter]').forEach(b => b.addEventListener('click', () => { location.href = '/inicio/instalar.html'; }));
    return;
  }

  // --- precarga de la ciudad, a escondidas
  let lista = false, marco = null;
  // avance real de la descarga de la ciudad: se muestra sobre la luz si la entrada tiene que esperar
  const avance = document.createElement('p'); avance.className = 'avance-entrada'; avance.setAttribute('aria-live', 'polite');
  avance.innerHTML = '<span>Preparando la ciudad</span><i><b></b></i>';
  let fraccion = 0;
  window.addEventListener('message', e => {
    if (e.origin !== location.origin || !e.data) return;
    if (e.data.sucre === 'lista') lista = true;
    else if (e.data.sucre === 'avance') { fraccion = Math.max(fraccion, +e.data.fraccion || 0); avance.style.setProperty('--avance', fraccion.toFixed(3)); }
  });
  const precargar = () => {
    marco = document.createElement('iframe');
    marco.id = 'ciudad-fondo'; marco.title = 'Ciudad 3D de Sucre'; marco.setAttribute('aria-hidden', 'true');
    marco.allow = 'fullscreen'; marco.src = '/ciudad?embebido';
    document.body.append(marco);
  };
  // la ciudad empieza a bajar apenas la portada se dibujó (antes esperaba 900 ms más)
  if (document.readyState === 'complete') precargar(); else addEventListener('load', precargar, { once: true });

  const luz = document.createElement('div'); luz.className = 'luz-entrada';
  const vineta = document.createElement('div'); vineta.className = 'vineta-entrada';
  document.body.append(vineta, luz, avance);

  let entrando = false;
  const entrar = () => {
    if (entrando) return; entrando = true;
    const hero = document.querySelector('.opening'), gatillo = document.querySelector('[data-landmark]');
    // el travelling apunta al edificio descubierto (o a la torre si se entró por otro botón)
    const r = gatillo.getBoundingClientRect(), h = hero.getBoundingClientRect();
    const fx = Math.round(r.left + r.width * (r.width > h.width * .5 ? .86 : .5) - h.left), fy = Math.round(r.top + r.height * .35 - h.top);
    document.documentElement.style.setProperty('--fx', fx + 'px'); document.documentElement.style.setProperty('--fy', fy + 'px');
    scrollTo({ top: 0, behavior: 'instant' });
    document.body.classList.add('entrando');
    if (!marco) precargar();
    const t0 = performance.now(), duracion = reducido.matches ? 500 : 2900;
    const esperar = () => {
      if (performance.now() - t0 < duracion || !lista) {
        if (performance.now() - t0 > duracion) document.body.classList.add('esperando-ciudad');
        return requestAnimationFrame(esperar);
      }
      document.body.classList.remove('esperando-ciudad');
      // la ciudad empieza a dibujar (a la plaza, de cara al monumento) detrás de la luz y se enfoca al revelarse
      document.body.classList.add('revelando');
      marco.contentWindow.postMessage({ sucre: 'entrar' }, location.origin);
      setTimeout(() => { document.body.classList.add('dentro'); marco.focus(); marco.contentWindow.focus();
        // el teclado va al lienzo de Godot: con el foco en el <body> del iframe no se podía caminar hasta hacer clic
        const lienzo = marco.contentDocument && marco.contentDocument.getElementById('ciudad3d'); if (lienzo) lienzo.focus();
        // y si una tecla queda en la portada (el foco no pasó al iframe), se le reenvía al lienzo
        const reenviar = (ev) => { const l = marco.contentDocument && marco.contentDocument.getElementById('ciudad3d'); if (!l) return;
          marco.contentWindow.focus(); l.focus(); l.dispatchEvent(new KeyboardEvent(ev.type, ev)); ev.preventDefault(); };
        addEventListener('keydown', reenviar); addEventListener('keyup', reenviar);
        setTimeout(() => document.body.classList.remove('revelando'), 60); }, 650);
      setTimeout(() => { document.querySelector('[data-page]').style.display = 'none'; document.querySelector('.clean-header').style.display = 'none'; hero.style.display = 'none'; }, 3600);
    };
    esperar();
  };
  document.querySelectorAll('[data-enter]').forEach(b => b.addEventListener('click', entrar));
})();
