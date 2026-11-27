# Personajes

Personas que caminan y hablan en la ciudad (los modelos los prepara codex en `blender/zonas/codex/personajes/`).
Cada personaje: una escena `.tscn` con su `CharacterBody3D`, su animación y, si habla, una zona registrada en el
autoload `Interaccion` (`Interaccion.registrar("personaje_id", area)`); escucha `Interaccion.accion` para abrir su
diálogo. Para caminar por las veredas: `NavigationAgent3D` sobre una malla de navegación de las veredas (por hacer).
