class_name Puente
extends Node
## Puente con la página web que contiene a la ciudad (web/src/ciudad/PaginaCiudad.tsx). Solo hace algo en la web.
##
## Página → Godot: funciones en window.sucreGodot (entrar, ir, toma, capturar, marcas, origen, calidad, hora, tour).
## Godot → página: eventos 'sucre' en window ({tipo: "lista" | "posicion" | "rendimiento" | "captura" | "elegida" …}).
## La página reenvía "lista"/"entrar" a la portada (/inicio) por postMessage, como hacía el visor three.js.

var principal: Node
var _ventana: JavaScriptObject
var _retener := []           # las funciones creadas con create_callback deben seguir vivas
var _t := 0.0
var _avisada := false

func _ready() -> void:
	if not OS.has_feature("web"):
		return
	_ventana = JavaScriptBridge.get_interface("window")
	var obj: JavaScriptObject = JavaScriptBridge.create_object("Object")
	for nombre in ["entrar", "ir", "toma", "capturar", "marcas", "origen", "calidad", "hora", "pausar", "tour"]:
		var cb := JavaScriptBridge.create_callback(Callable(self, "_js_" + nombre))
		_retener.append(cb)
		obj[nombre] = cb
	_ventana.sucreGodot = obj
	emitir({"tipo": "cargada"})

## Valor de un parámetro de la dirección (?embebido, ?hora=noche…) o null. En el escritorio: variable SUCRE_<NOMBRE>.
static func parametro(nombre: String) -> Variant:
	if not OS.has_feature("web"):
		var v := OS.get_environment("SUCRE_" + nombre.to_upper())
		return v if v != "" else null
	var r = JavaScriptBridge.eval("(new URLSearchParams(window.location.search)).get('%s')" % nombre, true)
	return null if r == null else str(r)

func emitir(datos: Dictionary) -> void:
	if _ventana == null:
		return
	JavaScriptBridge.eval("window.dispatchEvent(new CustomEvent('sucre', {detail: %s}))" % JSON.stringify(datos), true)

var _ultima_fraccion := -1.0
## Avance de la carga (para la pantalla de inicio de la página).
func progreso(f: float) -> void:
	if absf(f - _ultima_fraccion) < 0.02:
		return
	_ultima_fraccion = f
	emitir({"tipo": "progreso", "fraccion": f})

## La ciudad está lista para entrar (a pie, con el suelo cargado): la portada puede revelar la ciudad.
func avisar_lista() -> void:
	if _avisada:
		return
	_avisada = true
	emitir({"tipo": "lista", "segundos": Time.get_ticks_msec() / 1000.0})
	if principal.embebido:
		# incrustada: se deja de dibujar hasta que la portada ordene entrar (no gasta la GPU mientras se lee la portada)
		get_tree().create_timer(0.5).timeout.connect(func(): RenderingServer.render_loop_enabled = false)

func _process(dt: float) -> void:
	if _ventana == null or principal.modo != principal.Modo.PIE or principal.tour.activo:
		return
	_t += dt
	if _t < 0.5:
		return
	_t = 0.0
	var j: Jugador = principal.jugador
	var p := j.global_position
	emitir({"tipo": "posicion", "x": p.x, "y": p.y + Jugador.ALTURA_OJOS, "z": p.z, "rumbo": -j.yaw, "inclinacion": j.pitch,
		"fps": Engine.get_frames_per_second(), "llamadas": RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		"triangulos": RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		"calidad": principal.calidad.nivel, "calle": principal.ui.calle_actual(),
		"fisica_ms": Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		"proceso_ms": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		"trafico_ms": principal.trafico.costo_ms, "gpu_ms": _gpu_ms()})

## Tiempo de GPU del último cuadro (ms): mide el costo de dibujar sin la física ni los scripts (los fps mezclan todo).
func _gpu_ms() -> float:
	var vp := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	return RenderingServer.viewport_get_measured_render_time_gpu(vp)

# ------------------------------------------------------------------------------------------------- llamadas de la página
func _arg(args: Array, i: int, defecto: Variant = null) -> Variant:
	return args[i] if args.size() > i and args[i] != null else defecto

func _js_entrar(_args: Array) -> void:
	RenderingServer.render_loop_enabled = true
	principal.ciudad.presupuesto_ms = Ciudad.PRESUPUESTO_MS
	principal.entrar_desde_portada()

func _js_pausar(args: Array) -> void:
	RenderingServer.render_loop_enabled = not bool(_arg(args, 0, true))

## ir(x, z): salto a un punto (coordenadas del mundo: x este, z = −norte).
func _js_ir(args: Array) -> void:
	principal._ir(float(_arg(args, 0, 0.0)), float(_arg(args, 1, 0.0)), principal.jugador.yaw)

## toma(x, y, z, rumbo, inclinacion): vuelve exactamente a una vista (posición guardada, revisiones).
func _js_toma(args: Array) -> void:
	principal.tomar(float(_arg(args, 0)), float(_arg(args, 1)), float(_arg(args, 2)), float(_arg(args, 3, 0.0)), float(_arg(args, 4, 0.0)))

## capturar(x0, y0, x1, y1): captura de la pantalla y datos del encuadre para una revisión (responde con un evento).
func _js_capturar(args: Array) -> void:
	principal.revision.capturar(Rect2(Vector2(float(args[0]), float(args[1])), Vector2(float(args[2]) - float(args[0]), float(args[3]) - float(args[1]))))

## marcas(json): revisiones a marcar en la escena ([{id, x, y, z, estado, elegida}] en coordenadas del lienzo).
func _js_marcas(args: Array) -> void:
	principal.revision.marcar(JSON.parse_string(str(_arg(args, 0, "[]"))))

## origen(nombre, visible): taller, mostrar u ocultar lo de un agente o los volúmenes del lienzo.
func _js_origen(args: Array) -> void:
	principal.ciudad.mostrar_origen(str(args[0]), bool(args[1]))

func _js_calidad(args: Array) -> void:
	principal.calidad.fijar(str(args[0]))

func _js_hora(_args: Array) -> void:
	principal.cambiar_hora()

## tour(): empieza el tour guiado, o lo termina si ya está en curso.
func _js_tour(_args: Array) -> void:
	if principal.tour.activo:
		principal.tour.salir()
	else:
		principal.iniciar_tour()
