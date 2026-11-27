"""Lo que comparten las dos variantes de Moxó."""
from kit_personaje import cuerpo_desde_ual as _cuerpo_desde_ual

ALTURA_M = 1.58  # «bajo de estatura, un tanto grueso» (Q-0398-1)


def cuerpo_desde_ual(anatomia, *args, **kw):
    """Los zapatos de Moxó ya están planos en el suelo en la malla: conservan esa orientación. `anatomia.ALZADO`: el
    pie que en la malla está algo levantado (normalizado)."""
    alzado = {h: a * ALTURA_M for h, a in getattr(anatomia, 'ALZADO', {}).items()}
    return _cuerpo_desde_ual(*args, pies_como_malla=True, alzado=alzado, **kw)
