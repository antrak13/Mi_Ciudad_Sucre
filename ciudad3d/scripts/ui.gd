class_name Interfaz
extends CanvasLayer
## Interfaz táctil (equivale a web/src/ciudad/interfaz): pantalla de inicio con barra de carga y las dos puertas (ver desde el
## aire / caminar), marca, nombre de la calle, minimapa, controles de la vista aérea y de la caminata (joystick digital).

signal entrar_aereo
signal entrar_pie
signal zoom(factor: float)
signal norte
signal caminar_aqui
signal ver_aire
signal mirar(dx: float, dy: float)
signal mover(v: Vector2, correr: bool)
signal minimapa_ir(x: float, z: float)
signal minimapa_desplazar(dx: float, dz: float)
signal cambiar_hora
signal iniciar_tour

const CAL := Color("#fbf9f4")
const TINTA := Color("#2b1d16")
const TINTA_SUAVE := Color("#6b5a4e")
const ROJO := Color("#a9432d")
const ROJO_OSCURO := Color("#7f2f1f")
const ROJO_CLARO := Color("#fbe3e3")
const ORO := Color("#c9a45c")
const MARFIL := Color("#f4ead6")
const TEJA := Color("#c0623f")
const RADIO_JOY := 90.0
const SENS_TACTIL := 0.006

var minimapa: Minimapa
var _raiz: Control
var _inicio: Control
var _barra: ProgressBar
var _detalle: Label
var _puertas: HBoxContainer
var _hud: Control
var _calle_panel: PanelContainer
var _calle_label: Label
var _calle_mapa: Label
var _controles_aire: Control
var _controles_pie: Control
var _pie_activo := false
var _joy_id := -1
var _joy_origen := Vector2.ZERO
var _joy_pos := Vector2.ZERO
var _joy_dibujo: Control
var _mirar_id := -1
var _boton_hora: Button
var _telon: ColorRect

func _ready() -> void:
	layer = 10
	_raiz = Control.new()
	_raiz.set_anchors_preset(Control.PRESET_FULL_RECT)
	_raiz.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_raiz)
	_crear_hud()
	_crear_inicio()
	get_viewport().size_changed.connect(_zona_segura)
	_zona_segura()

## Deja libres las muescas de cámara y las barras del sistema: el HUD vive dentro del área segura de la pantalla.
func _zona_segura() -> void:
	if not OS.has_feature("android"):
		return
	var seg := DisplayServer.get_display_safe_area()
	var ventana := Vector2(DisplayServer.window_get_size())
	var vp := get_viewport().get_visible_rect().size
	if seg.size.x <= 0 or ventana.x <= 0:
		return
	var k := vp.x / ventana.x
	_hud.offset_left = maxf(0.0, (seg.position.x) * k)
	_hud.offset_top = maxf(0.0, (seg.position.y) * k)
	_hud.offset_right = -maxf(0.0, (ventana.x - seg.end.x) * k)
	_hud.offset_bottom = -maxf(0.0, (ventana.y - seg.end.y) * k)

# ----------------------------------------------------------------------------------------------- estilos
func _caja(color := CAL, borde_sup := 0, radio := 14) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = color
	s.set_corner_radius_all(radio)
	s.shadow_color = Color(0.17, 0.11, 0.09, 0.28)
	s.shadow_size = 10
	s.shadow_offset = Vector2(0, 4)
	if borde_sup > 0:
		s.border_width_top = borde_sup
		s.border_color = ROJO
	s.content_margin_left = 16
	s.content_margin_right = 16
	s.content_margin_top = 8
	s.content_margin_bottom = 8
	return s

func _boton(texto: String, rojo: bool, ancho := 0.0) -> Button:
	var b := Button.new()
	b.text = texto
	b.add_theme_font_size_override("font_size", 22)
	var base := _caja(ROJO if rojo else CAL)
	base.content_margin_top = 12
	base.content_margin_bottom = 12
	var presionado := _caja(ROJO_OSCURO if rojo else Color("#fbf1c4"))
	presionado.content_margin_top = 12
	presionado.content_margin_bottom = 12
	for est in ["normal", "hover", "focus"]:
		b.add_theme_stylebox_override(est, base)
	b.add_theme_stylebox_override("pressed", presionado)
	var tinta := Color.WHITE if rojo else TINTA
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(c, tinta)
	if ancho > 0.0:
		b.custom_minimum_size.x = ancho
	return b

func _etiqueta(texto: String, tam: int, color := TINTA) -> Label:
	var l := Label.new()
	l.text = texto
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", color)
	return l

# ----------------------------------------------------------------------------------------------- pantalla de inicio
func _serif(tam: int, cursiva := false) -> SystemFont:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Georgia", "Noto Serif", "DejaVu Serif", "serif"])
	f.font_italic = cursiva
	return f

## Pantalla de inicio al estilo de la portada web (concepto B): la ciudad de fondo, marca discreta arriba, titular en serif
## abajo a la izquierda y dos accesos sobrios; sin tarjeta ni iconos infantiles.
func _crear_inicio() -> void:
	_inicio = Control.new()
	_inicio.set_anchors_preset(Control.PRESET_FULL_RECT)
	_raiz.add_child(_inicio)
	# degradado oscuro de abajo hacia arriba (para leer el texto sobre la ciudad)
	var grad := Gradient.new()
	grad.set_color(0, Color(0.09, 0.15, 0.12, 0.92))
	grad.set_color(1, Color(0.09, 0.15, 0.12, 0.38))
	grad.add_point(0.5, Color(0.09, 0.15, 0.12, 0.78))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill_from = Vector2(0, 1)
	gt.fill_to = Vector2(0, 0.0)
	var velo := TextureRect.new()
	velo.name = "velo"
	velo.texture = gt
	velo.stretch_mode = TextureRect.STRETCH_SCALE
	velo.set_anchors_preset(Control.PRESET_FULL_RECT)
	_inicio.add_child(velo)
	var margen := MarginContainer.new()
	margen.set_anchors_preset(Control.PRESET_FULL_RECT)
	for lado in ["left", "right"]:
		margen.add_theme_constant_override("margin_" + lado, 64)
	margen.add_theme_constant_override("margin_top", 40)
	margen.add_theme_constant_override("margin_bottom", 44)
	_inicio.add_child(margen)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	margen.add_child(col)
	var marca := HBoxContainer.new()
	marca.add_theme_constant_override("separation", 14)
	var m1 := _etiqueta("MiCiudad", 30, MARFIL)
	m1.add_theme_font_override("font", _serif(30))
	var m2 := _etiqueta("SUCRE", 14, Color(MARFIL, 0.8))
	marca.add_child(m1)
	marca.add_child(m2)
	col.add_child(marca)
	var relleno := Control.new()
	relleno.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(relleno)
	for linea in ["La ciudad que ves.", "Las historias"]:
		var t := _etiqueta(linea, 56, MARFIL)
		t.add_theme_font_override("font", _serif(56))
		t.add_theme_constant_override("line_spacing", -6)
		col.add_child(t)
	var t3 := _etiqueta("que te faltan.", 56, MARFIL)
	t3.add_theme_font_override("font", _serif(56, true))
	col.add_child(t3)
	var sep := Control.new()
	sep.custom_minimum_size.y = 14
	col.add_child(sep)
	_barra = ProgressBar.new()
	_barra.show_percentage = false
	_barra.custom_minimum_size = Vector2(420, 4)
	var fondo := StyleBoxFlat.new()
	fondo.bg_color = Color(MARFIL, 0.22)
	fondo.set_corner_radius_all(2)
	var lleno := StyleBoxFlat.new()
	lleno.bg_color = ORO
	lleno.set_corner_radius_all(2)
	_barra.add_theme_stylebox_override("background", fondo)
	_barra.add_theme_stylebox_override("fill", lleno)
	_barra.max_value = 1.0
	col.add_child(_barra)
	_detalle = _etiqueta("Armando la ciudad…", 16, Color(MARFIL, 0.8))
	col.add_child(_detalle)
	_puertas = HBoxContainer.new()
	_puertas.add_theme_constant_override("separation", 14)
	_puertas.visible = false
	var b2 := _boton_sobrio("Caminar sus calles", true)
	b2.pressed.connect(func(): entrar_pie.emit())
	var b3 := _boton_sobrio("Hacer el tour guiado", false)
	b3.pressed.connect(func():
		entrar_pie.emit()
		iniciar_tour.emit())
	var b1 := _boton_sobrio("Ver desde el aire", false)
	b1.pressed.connect(func(): entrar_aereo.emit())
	_puertas.add_child(b2)
	_puertas.add_child(b3)
	b1.free()      # vista aérea desactivada por ahora
	col.add_child(_puertas)

func _boton_sobrio(texto: String, principal: bool) -> Button:
	var b := Button.new()
	b.text = texto
	b.add_theme_font_size_override("font_size", 22)
	var base := StyleBoxFlat.new()
	base.set_corner_radius_all(6)
	base.content_margin_left = 26
	base.content_margin_right = 26
	base.content_margin_top = 13
	base.content_margin_bottom = 13
	if principal:
		base.bg_color = MARFIL
	else:
		base.bg_color = Color(1, 1, 1, 0.0)
		base.set_border_width_all(2)
		base.border_color = Color(MARFIL, 0.75)
	var pres := base.duplicate() as StyleBoxFlat
	pres.bg_color = TEJA if principal else Color(1, 1, 1, 0.16)
	for est in ["normal", "hover", "focus"]:
		b.add_theme_stylebox_override(est, base)
	b.add_theme_stylebox_override("pressed", pres)
	var tinta := Color("#1f3128") if principal else MARFIL
	for c in ["font_color", "font_hover_color", "font_focus_color"]:
		b.add_theme_color_override(c, tinta)
	b.add_theme_color_override("font_pressed_color", Color.WHITE)
	return b

func poner_hora(es_noche: bool) -> void:
	_boton_hora.text = "Día" if es_noche else "Noche"

## Fundido a negro, ejecuta 'cambio' en lo más oscuro y vuelve a mostrar (equivale al fundido de la web).
func fundir(cambio: Callable) -> void:
	if _telon == null:
		_telon = ColorRect.new()
		_telon.color = Color(0, 0, 0, 0)
		_telon.set_anchors_preset(Control.PRESET_FULL_RECT)
		_telon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var capa := CanvasLayer.new()
		capa.layer = 30
		add_child(capa)
		capa.add_child(_telon)
	var t := create_tween()
	t.tween_property(_telon, "color:a", 1.0, 0.26)
	t.tween_callback(cambio)
	t.tween_interval(0.12)
	t.tween_property(_telon, "color:a", 0.0, 0.4)

func progreso(f: float, texto: String) -> void:
	_barra.value = f
	_detalle.text = texto

func lista() -> void:
	_barra.visible = false
	_detalle.visible = false
	_puertas.visible = true

func ocultar_inicio() -> void:
	_inicio.visible = false
	_hud.visible = true

func hud_visible(v: bool) -> void:
	_hud.visible = v

func calle_actual() -> String:
	return _calle_label.text

# ----------------------------------------------------------------------------------------------- HUD
func _crear_hud() -> void:
	_hud = Control.new()
	_hud.set_anchors_preset(Control.PRESET_FULL_RECT)
	_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hud.visible = false
	_raiz.add_child(_hud)
	# marca (arriba a la izquierda)
	var marca := PanelContainer.new()
	marca.add_theme_stylebox_override("panel", _caja())
	marca.position = Vector2(16, 14)
	_hud.add_child(marca)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 10)
	marca.add_child(h)
	var bandera := Control.new()
	bandera.custom_minimum_size = Vector2(30, 20)
	bandera.draw.connect(func():
		bandera.draw_rect(Rect2(0, 0, 30, 20), Color.WHITE)
		bandera.draw_polygon(PackedVector2Array([Vector2(1, 0), Vector2(4, 0), Vector2(29, 17), Vector2(29, 20), Vector2(26, 20), Vector2(1, 3)]), [ROJO])
		bandera.draw_polygon(PackedVector2Array([Vector2(29, 0), Vector2(26, 0), Vector2(1, 17), Vector2(1, 20), Vector2(4, 20), Vector2(29, 3)]), [ROJO])
		bandera.draw_circle(Vector2(15, 10), 2.6, ORO))
	h.add_child(bandera)
	var nm := _etiqueta("MiCiudad", 24)
	nm.add_theme_font_override("font", _serif(24))
	h.add_child(nm)
	h.add_child(_etiqueta("SUCRE", 14, TINTA_SUAVE))
	# hora del día (arriba a la derecha)
	_boton_hora = _boton("Noche", false)
	_boton_hora.pressed.connect(func(): cambiar_hora.emit())
	var caja_hora := VBoxContainer.new()
	caja_hora.add_theme_constant_override("separation", 8)
	caja_hora.add_child(_boton_hora)
	var boton_tour := _boton("Tour", false)
	boton_tour.pressed.connect(func(): iniciar_tour.emit())
	caja_hora.add_child(boton_tour)
	_hud.add_child(caja_hora)
	caja_hora.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT, Control.PRESET_MODE_MINSIZE, 16)
	# minimapa debajo de la marca
	minimapa = Minimapa.new()
	minimapa.position = Vector2(16, 78)
	minimapa.ir_a.connect(func(x, z): minimapa_ir.emit(x, z))
	minimapa.desplazar.connect(func(dx, dz): minimapa_desplazar.emit(dx, dz))
	_hud.add_child(minimapa)
	_calle_mapa = _etiqueta("", 15, TINTA)
	_calle_mapa.position = Vector2(16, 254)
	_hud.add_child(_calle_mapa)
	# nombre de la calle (arriba al centro, a pie)
	_calle_panel = PanelContainer.new()
	_calle_panel.add_theme_stylebox_override("panel", _caja(CAL, 3))
	_calle_panel.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_calle_panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_calle_panel.position.y = 16
	_calle_panel.visible = false
	_calle_label = _etiqueta("", 26)
	_calle_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_calle_panel.add_child(_calle_label)
	_hud.add_child(_calle_panel)
	# controles de la vista aérea (abajo a la derecha)
	_controles_aire = Control.new()
	_controles_aire.set_anchors_preset(Control.PRESET_FULL_RECT)
	_controles_aire.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hud.add_child(_controles_aire)
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	v.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	v.grow_vertical = Control.GROW_DIRECTION_BEGIN
	v.position = Vector2(-16, -16)
	v.add_theme_constant_override("separation", 12)
	_controles_aire.add_child(v)
	var caja := PanelContainer.new()
	caja.add_theme_stylebox_override("panel", _caja(CAL, 0, 12))
	var vv := VBoxContainer.new()
	caja.add_child(vv)
	for par in [["+", 0.6], ["−", 1.6]]:
		var b := Button.new()
		b.text = par[0]
		b.flat = true
		b.custom_minimum_size = Vector2(56, 52)
		b.add_theme_font_size_override("font_size", 28)
		b.add_theme_color_override("font_color", TINTA)
		var f: float = par[1]
		b.pressed.connect(func(): zoom.emit(f))
		vv.add_child(b)
	var bn := Button.new()
	bn.text = "N"
	bn.flat = true
	bn.custom_minimum_size = Vector2(56, 52)
	bn.add_theme_font_size_override("font_size", 24)
	bn.add_theme_color_override("font_color", ROJO)
	bn.pressed.connect(func(): norte.emit())
	vv.add_child(bn)
	v.add_child(caja)
	var caminar := _boton("Caminar aquí", true)
	caminar.pressed.connect(func(): caminar_aqui.emit())
	v.add_child(caminar)
	# controles de la caminata
	_controles_pie = Control.new()
	_controles_pie.set_anchors_preset(Control.PRESET_FULL_RECT)
	_controles_pie.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_controles_pie.visible = false
	_hud.add_child(_controles_pie)
	# vista aérea desactivada por ahora: sin botón "Ver desde el aire" para salir de la caminata (la señal ver_aire queda)
	_joy_dibujo = Control.new()
	_joy_dibujo.set_anchors_preset(Control.PRESET_FULL_RECT)
	_joy_dibujo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_joy_dibujo.draw.connect(_dibujar_joystick)
	_controles_pie.add_child(_joy_dibujo)

func modo(pie: bool) -> void:
	_pie_activo = pie
	_controles_aire.visible = not pie
	_controles_pie.visible = pie
	_calle_panel.visible = pie and _calle_label.text != ""
	_calle_mapa.visible = not pie
	_soltar_todo()

func poner_calle(nombre: String) -> void:
	if _pie_activo:
		if nombre != _calle_label.text:
			_calle_label.text = nombre
			_calle_panel.visible = nombre != ""
			_calle_panel.reset_size()
			_calle_panel.position.x = (get_viewport().get_visible_rect().size.x - _calle_panel.size.x) / 2.0
	else:
		_calle_mapa.text = nombre

func _soltar_todo() -> void:
	_joy_id = -1
	_mirar_id = -1
	mover.emit(Vector2.ZERO, false)
	_joy_dibujo.queue_redraw()

# ----------------------------------------------------------------------------------------------- joystick y mirar
func _dibujar_joystick() -> void:
	if _joy_id < 0:
		return
	_joy_dibujo.draw_circle(_joy_origen, RADIO_JOY, Color(1, 1, 1, 0.16))
	_joy_dibujo.draw_arc(_joy_origen, RADIO_JOY, 0, TAU, 40, Color(1, 1, 1, 0.55), 3.0, true)
	_joy_dibujo.draw_circle(_joy_pos, 34, Color(1, 1, 1, 0.55))
	_joy_dibujo.draw_arc(_joy_pos, 34, 0, TAU, 28, Color(1, 1, 1, 0.9), 2.0, true)

func _sobre_ui(p: Vector2) -> bool:
	for c in [minimapa, _calle_panel]:
		if c != null and c.visible and c.get_global_rect().has_point(p):
			return true
	var hov := get_viewport().gui_get_hovered_control()
	return hov is BaseButton

func _input(ev: InputEvent) -> void:
	if not _pie_activo or _inicio.visible:
		return
	var tam := get_viewport().get_visible_rect().size
	if ev is InputEventScreenTouch:
		var t: InputEventScreenTouch = ev
		var p := t.position * (tam.x / get_viewport().get_visible_rect().size.x)
		if t.pressed:
			if _sobre_ui(p) or p.y > tam.y - 120.0 and p.x > tam.x - 330.0:
				return
			if p.x < tam.x * 0.5 and _joy_id < 0:
				_joy_id = t.index
				_joy_origen = p
				_joy_pos = p
			elif p.x >= tam.x * 0.5 and _mirar_id < 0:
				_mirar_id = t.index
		else:
			if t.index == _joy_id:
				_joy_id = -1
				mover.emit(Vector2.ZERO, false)
				_joy_dibujo.queue_redraw()
			elif t.index == _mirar_id:
				_mirar_id = -1
	elif ev is InputEventScreenDrag:
		var d: InputEventScreenDrag = ev
		if d.index == _joy_id:
			var v := d.position - _joy_origen
			var largo := minf(v.length(), RADIO_JOY)
			_joy_pos = _joy_origen + (v.normalized() * largo if v.length() > 0.001 else Vector2.ZERO)
			var n := Vector2(v.x, -v.y) / RADIO_JOY
			if n.length() > 1.0:
				n = n.normalized()
			mover.emit(n, n.length() > 0.95)
			_joy_dibujo.queue_redraw()
		elif d.index == _mirar_id:
			mirar.emit(d.relative.x * SENS_TACTIL, d.relative.y * SENS_TACTIL)
