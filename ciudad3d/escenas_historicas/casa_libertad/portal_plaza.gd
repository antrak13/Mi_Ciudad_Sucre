class_name PortalCasaLibertad
extends Node3D
## Conecta la manzana M037 frente a la Plaza 25 de Mayo con el recorrido interior de Casa de la Libertad,
## sin interferir con las mallas ni colisiones de S_PLAZA25 / M037 de los demás integrantes.

const ESCENA_RECORRIDO := "res://escenas_historicas/casa_libertad/recorrido_casa_libertad.tscn"
const ID_PORTAL := "cl:entrar_museo_plaza"

var principal: Node
var _area: Area3D
var _capa: CanvasLayer
var _aviso: PanelContainer
var _texto: Label
var _paquete: PaqueteHistorico
var _esperando := false

func _ready() -> void:
	# Posición exacta en la vereda frente a la portada de Casa de la Libertad (Plaza 25 de Mayo)
	var base := CasaLibertadMuseo.POSICION_PLAZA_25
	var normal_plaza := Vector3(sin(CasaLibertadMuseo.ROTACION_Y_PLAZA_25), 0.0, cos(CasaLibertadMuseo.ROTACION_Y_PLAZA_25))
	global_position = base + normal_plaza * 2.1 + Vector3(0.0, 1.2, 0.0)

	_area = Area3D.new()
	_area.name = "PortalEntradaMuseo"
	_area.collision_layer = 0
	_area.collision_mask = 8
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 3.2
	cs.shape = sph
	_area.add_child(cs)
	add_child(_area)

	_crear_banner()
	# recursos del museo: en la web se descargan aparte, en segundo plano, con la plaza ya a la vista
	_paquete = PaqueteHistorico.new()
	_paquete.name = "PaqueteHistorico"
	add_child(_paquete)
	_paquete.avance.connect(_al_avanzar)
	_paquete.listo.connect(_al_listo)
	Interaccion.registrar(ID_PORTAL, _area)
	Interaccion.entro.connect(_on_entro)
	Interaccion.salio.connect(_on_salio)
	Interaccion.accion.connect(_on_accion)

func _exit_tree() -> void:
	Interaccion.quitar(ID_PORTAL)

func _crear_banner() -> void:
	_capa = CanvasLayer.new()
	_capa.layer = 15
	add_child(_capa)

	_aviso = PanelContainer.new()
	_aviso.visible = false
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.984, 0.976, 0.957, 0.96)
	sb.set_corner_radius_all(10)
	sb.border_width_top = 3
	sb.border_color = Color("#a9432d")
	sb.content_margin_left = 18
	sb.content_margin_right = 18
	sb.content_margin_top = 10
	sb.content_margin_bottom = 10
	_aviso.add_theme_stylebox_override("panel", sb)

	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	var lbl := Label.new()
	_texto = lbl
	lbl.text = "Casa de la Libertad · Presiona [E] para entrar al museo"
	lbl.add_theme_font_size_override("font_size", 18)
	lbl.add_theme_color_override("font_color", Color("#2b1d16"))
	var btn := Button.new()
	btn.text = "Entrar [E]"
	btn.add_theme_font_size_override("font_size", 16)
	btn.pressed.connect(func(): Interaccion.usar())
	hb.add_child(lbl)
	hb.add_child(btn)
	_aviso.add_child(hb)
	_capa.add_child(_aviso)

func _on_entro(id: String) -> void:
	if id != ID_PORTAL:
		return
	if not _esperando:
		_texto.text = "Casa de la Libertad · Presiona [E] para entrar al museo"
	_aviso.visible = true
	_aviso.reset_size()
	var vp := get_viewport().get_visible_rect().size
	_aviso.position = Vector2((vp.x - _aviso.size.x) * 0.5, vp.y - _aviso.size.y - 28.0)

func _on_salio(id: String) -> void:
	if id == ID_PORTAL:
		_aviso.visible = false

func _on_accion(id: String) -> void:
	if id != ID_PORTAL:
		return
	if not PaqueteHistorico.disponible():
		# llegó antes que la descarga: se entra apenas termine
		_esperando = true
		_texto.text = "Casa de la Libertad · Preparando el museo…"
		_aviso.visible = true
		_paquete.descargar()
		return
	_entrar()

func _al_avanzar(f: float) -> void:
	if _esperando:
		_texto.text = "Casa de la Libertad · Preparando el museo… %d %%" % int(f * 100.0)

func _al_listo() -> void:
	if _esperando:
		_esperando = false
		_entrar()

func _entrar() -> void:
	_aviso.visible = false
	get_tree().set_meta("desde_plaza_casa_libertad", true)
	var entrar := func(): get_tree().change_scene_to_file(ESCENA_RECORRIDO)
	if principal != null and principal.ui != null:
		principal.ui.fundir(entrar)
	else:
		entrar.call()
