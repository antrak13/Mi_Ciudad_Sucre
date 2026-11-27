class_name PortalAsamblea1825
extends Node
## Puerta en el tiempo dentro del Salón de la Independencia: cerca de la vitrina del Acta aparece
## "[H] Vivir la Asamblea de 1825" y la tecla (o el botón) lleva al juego "Vive la Historia" (proyecto juego/,
## Escena 1: la Asamblea de 1825, que sesionó en este mismo salón).
## - En la web avisa a la página con el evento `sucre` {tipo: "viajar", destino: "asamblea_1825"}; la página
##   (web/src/ciudad/Experiencia.tsx) abre /asamblea.
## - En el escritorio abre el proyecto juego/ con el mismo ejecutable de Godot.
## Se agrega desde recorrido_casa_libertad.gd: add_child(PortalAsamblea1825.new()).

const POI := "POI_ACTA_INDEPENDENCIA"
const POSICION_RESPALDO := Vector3(0.0, 0.0, -45.8)   # centro del Salón si el marcador no aparece
const RADIO := 6.5
const MEDIO_ANCHO_SALON := 4.6                        # el Salón mide 9,2 m de ancho interior

var _jugador: Node3D
var _centro := POSICION_RESPALDO
var _capa: CanvasLayer
var _aviso: PanelContainer
var _cerca := false
var _viajando := false


func _ready() -> void:
	await get_tree().process_frame
	var padre := get_parent()
	_jugador = padre.get_node_or_null("Jugador") as Node3D
	var marcador := padre.find_child(POI, true, false) as Node3D
	if marcador != null:
		_centro = marcador.global_position
	_crear_aviso()


func _process(_dt: float) -> void:
	if _jugador == null or _viajando:
		return
	var p := _jugador.global_position
	var cerca := Vector2(p.x - _centro.x, p.z - _centro.z).length() < RADIO and absf(p.x - _centro.x) < MEDIO_ANCHO_SALON
	if cerca != _cerca:
		_cerca = cerca
		_aviso.visible = cerca


func _unhandled_input(ev: InputEvent) -> void:
	if _cerca and ev is InputEventKey and ev.pressed and not ev.echo and ev.physical_keycode == KEY_H:
		get_viewport().set_input_as_handled()
		viajar()


func viajar() -> void:
	if _viajando:
		return
	_viajando = true
	if OS.has_feature("web"):
		JavaScriptBridge.eval(
			"window.dispatchEvent(new CustomEvent('sucre', {detail: {tipo: 'viajar', destino: 'asamblea_1825'}}))", true)
		return
	var juego := ProjectSettings.globalize_path("res://").path_join("../juego").simplify_path()
	if not DirAccess.dir_exists_absolute(juego):
		push_warning("[PortalAsamblea1825] No se encontró el proyecto juego/ en %s" % juego)
		_viajando = false
		return
	OS.create_process(OS.get_executable_path(), ["--path", juego])
	get_tree().quit()


func _crear_aviso() -> void:
	_capa = CanvasLayer.new()
	_capa.layer = 15
	add_child(_capa)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.984, 0.976, 0.957, 0.95)
	sb.set_corner_radius_all(10)
	sb.border_width_top = 3
	sb.border_color = Color("#a9432d")
	sb.content_margin_left = 18
	sb.content_margin_right = 18
	sb.content_margin_top = 10
	sb.content_margin_bottom = 10
	_aviso = PanelContainer.new()
	_aviso.add_theme_stylebox_override("panel", sb)
	_aviso.visible = false
	_aviso.mouse_filter = Control.MOUSE_FILTER_STOP
	_aviso.gui_input.connect(func(ev: InputEvent):
		if ev is InputEventMouseButton and ev.pressed and ev.button_index == MOUSE_BUTTON_LEFT:
			viajar())
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 14)
	var tecla := Label.new()
	tecla.text = " H "
	tecla.add_theme_font_size_override("font_size", 26)
	tecla.add_theme_color_override("font_color", Color("#a9432d"))
	var vb := VBoxContainer.new()
	var titulo := Label.new()
	titulo.text = "Vivir la Asamblea de 1825"
	titulo.add_theme_font_size_override("font_size", 20)
	titulo.add_theme_color_override("font_color", Color("#2b1d16"))
	var detalle := Label.new()
	detalle.text = "En este salón se firmó el Acta de la Independencia"
	detalle.add_theme_font_size_override("font_size", 14)
	detalle.add_theme_color_override("font_color", Color("#5a463a"))
	vb.add_child(titulo)
	vb.add_child(detalle)
	hb.add_child(tecla)
	hb.add_child(vb)
	_aviso.add_child(hb)
	_aviso.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 96)
	_capa.add_child(_aviso)
