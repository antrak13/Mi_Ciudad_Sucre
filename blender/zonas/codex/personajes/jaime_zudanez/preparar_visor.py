"""Empaqueta el visor común con la lámina del Jaime Zudáñez."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent))

from visor_ual import preparar_visor

preparar_visor(BASE.parents[4], BASE.name, zoom=.92)
