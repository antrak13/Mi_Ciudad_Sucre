"""Empaqueta el visor de Antigravity con los recursos de cada personaje."""
from shutil import copy2

from PIL import Image


def preparar_visor(raiz, personaje, zoom=1.):
    modelos = raiz / 'web/public/models/ciudad'
    ocana = modelos / 'antigravity/personajes/diego_de_ocana'
    salida = modelos / 'codex/personajes' / personaje
    salida.mkdir(parents=True, exist_ok=True)
    for archivo in ('visor.bundle.js', 'THREE-LICENSE.txt'):
        copy2(ocana / archivo, salida / archivo)

    html = (ocana / 'index.html').read_text()
    nav = ('      <div>\n'
           '        <div class="seccion-titulo">Personajes animados</div>\n'
           '        <div id="nav-personajes" class="rejilla"></div>\n'
           '      </div>\n\n')
    html = html.replace(nav, '')
    html = html.replace('<script src="visor.bundle.js"></script>', '''<script>
        let visorPersonaje;
        Object.defineProperty(window, '__visor', {
          get: () => visorPersonaje,
          set: (visor) => {
            visorPersonaje = visor;
            visor.camera.zoom = 0.88;
            visor.camera.updateProjectionMatrix();
            const metricas = document.getElementById('metricas');
            metricas.textContent = metricas.textContent.replace(' huesos UAL', ' huesos');
          },
        });
      </script>
      <script src="visor.bundle.js"></script>'''.replace('0.88', str(zoom)))
    (salida / 'index.html').write_text(html)

    with Image.open(raiz / 'personas' / personaje / 'diseno.png') as lamina:
        lamina.thumbnail((768, 1152))
        lamina.convert('RGB').save(salida / 'referencia.jpg', quality=92, optimize=True)
