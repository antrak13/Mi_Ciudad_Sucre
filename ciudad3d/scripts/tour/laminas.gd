class_name TourLaminas
extends CanvasLayer
## Lo que el tour pone sobre la imagen (debajo de la carta, que va en la capa 20):
## - barras de cine arriba y abajo;
## - el título de cada parada (como un intertítulo: número, nombre y lema en letra de imprenta antigua);
## - láminas de archivo montadas sobre papel al costado de la carta (fotografía, grabado o retrato, con su pie y su
##   fuente), que se acercan despacio (efecto Ken Burns);
## - el «fundido»: la lámina grande en el centro sobre la ciudad oscurecida, que se disuelve en la vista actual del
##   mismo lugar (antes y ahora);
## - el telón negro de los cortes.
## Las imágenes se bajan a demanda (Datos.bytes) y se guardan mientras dura el tour.

const NORMAL := preload("res://personajes/ui/fuentes/CormorantGaramond_wght.ttf")
const CURSIVA := preload("res://personajes/ui/fuentes/CormorantGaramond-Italic_wght.ttf")
const MARFIL := Color("#f6efe2")
const ORO := Color("#e9c46a")
const TINTA := Color("#34230f")
const TINTA_SUAVE := Color("#6f5c40")
const PAPEL := Color("#efe5cf")

var _raiz: Control
var _barra_arriba: ColorRect
var _barra_abajo: ColorRect
var _telon: ColorRect
var _titulo: VBoxContainer
var _titulo_n: Label
var _titulo_nombre: Label
var _titulo_lema: Label
var _lado: Control                     # lámina al costado (se rehace en cada una)
var _lado_id := ""
var _fundido: Control
var _texturas := {}                    # id → ImageTexture
var _bajando := {}
var _barras := false

func _ready() -> void:
	layer = 19
	_raiz = Control.new()
	_raiz.set_anchors_preset(Control.PRESET_FULL_RECT)
	_raiz.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_raiz)
	_barra_arriba = _rect(Color.BLACK)
	_barra_abajo = _rect(Color.BLACK)
	_titulo = VBoxContainer.new()
	_titulo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_titulo.alignment = BoxContainer.ALIGNMENT_CENTER
	_titulo.add_theme_constant_override("separation", 2)
	_titulo.modulate.a = 0.0
	_raiz.add_child(_titulo)
	_titulo_n = _etiqueta(CURSIVA, 500, ORO)
	_titulo_nombre = _etiqueta(NORMAL, 600, MARFIL)
	_titulo_lema = _etiqueta(CURSIVA, 500, Color(MARFIL, 0.85))
	for l in [_titulo_n, _titulo_nombre, _titulo_lema]:
		_titulo.add_child(l)
	_telon = _rect(Color.BLACK)
	_telon.set_anchors_preset(Control.PRESET_FULL_RECT)
	_telon.modulate.a = 0.0
	get_viewport().size_changed.connect(_acomodar)
	_acomodar()

func _rect(c: Color) -> ColorRect:
	var r := ColorRect.new()
	r.color = c
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_raiz.add_child(r)
	return r

func _fuente(f: FontFile, peso: int) -> FontVariation:
	var v := FontVariation.new()
	v.base_font = f
	v.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): peso}
	return v

func _etiqueta(f: FontFile, peso: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_override("font", _fuente(f, peso))
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.75))
	l.add_theme_constant_override("shadow_offset_x", 0)
	l.add_theme_constant_override("shadow_offset_y", 2)
	l.add_theme_constant_override("shadow_outline_size", 10)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func _tam() -> Vector2:
	return get_viewport().get_visible_rect().size

func _alto_barra() -> float:
	return roundf(_tam().y * 0.075)

func _acomodar() -> void:
	var t := _tam()
	var h := _alto_barra()
	_barra_arriba.size = Vector2(t.x, h)
	_barra_arriba.position = Vector2(0, 0 if _barras else -h)
	_barra_abajo.size = Vector2(t.x, h)
	_barra_abajo.position = Vector2(0, t.y - h if _barras else t.y)
	var base := clampf(t.y * 0.06, 26.0, 64.0)
	_titulo_n.add_theme_font_size_override("font_size", int(base * 0.42))
	_titulo_nombre.add_theme_font_size_override("font_size", int(base))
	_titulo_lema.add_theme_font_size_override("font_size", int(base * 0.5))
	_titulo.size = Vector2(t.x, t.y * 0.3)
	_titulo.position = Vector2(0, t.y * 0.14)

# ------------------------------------------------------------------------------------------------- barras, telón, títulos
func barras(v: bool) -> void:
	_barras = v
	var t := _tam()
	var h := _alto_barra()
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_property(_barra_arriba, "position:y", 0.0 if v else -h, 1.2)
	tw.tween_property(_barra_abajo, "position:y", t.y - h if v else t.y, 1.2)

## Telón negro (await): true lo cierra, false lo abre.
func negro(v: bool, dur: float) -> void:
	var tw := create_tween()
	tw.tween_property(_telon, "modulate:a", 1.0 if v else 0.0, dur).set_trans(Tween.TRANS_SINE)
	await tw.finished

func titulo(n: int, total: int, nombre: String, lema: String) -> void:
	_titulo_n.text = "%s  ·  parada %d de %d" % [_romano(n), n, total]
	_titulo_nombre.text = nombre
	_titulo_lema.text = lema
	_titulo_lema.visible = lema != ""
	_titulo.pivot_offset = _titulo.size * 0.5
	_titulo.scale = Vector2(0.97, 0.97)
	var tw := create_tween()
	tw.tween_property(_titulo, "modulate:a", 1.0, 1.1).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(_titulo, "scale", Vector2.ONE, 5.5).set_trans(Tween.TRANS_SINE)
	tw.tween_interval(2.6)
	tw.tween_property(_titulo, "modulate:a", 0.0, 1.4).set_trans(Tween.TRANS_SINE)

static func _romano(n: int) -> String:
	return ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][clampi(n, 0, 10)]

# ------------------------------------------------------------------------------------------------- imágenes
## Baja la imagen de una lámina (si no está) — no espera.
func precargar(d: Dictionary) -> void:
	_textura(d)

func _textura(d: Dictionary) -> Texture2D:
	var id: String = d.get("id", "")
	if _texturas.has(id):
		return _texturas[id]
	if _bajando.has(id):
		while _bajando.has(id):
			await get_tree().process_frame
		return _texturas.get(id)
	_bajando[id] = true
	var b: PackedByteArray = await Datos.bytes(d.get("archivo", ""), str(d.get("v", "")))
	var tex: Texture2D = null
	var img := Image.new()
	if not b.is_empty() and img.load_jpg_from_buffer(b) == OK:
		img.generate_mipmaps()
		tex = ImageTexture.create_from_image(img)
	_texturas[id] = tex
	_bajando.erase(id)
	return tex

## Una lámina montada en papel: foto, pie y fuente. 'alto' en píxeles de la imagen.
func _montar(tex: Texture2D, d: Dictionary, alto_img: float, ancho_max: float) -> Control:
	var aspecto := float(tex.get_width()) / maxf(tex.get_height(), 1.0)
	var ancho_img := alto_img * aspecto
	if ancho_img > ancho_max:
		ancho_img = ancho_max
		alto_img = ancho_img / aspecto
	var margen := roundf(clampf(alto_img * 0.045, 8.0, 18.0))
	var t_pie := clampf(_tam().y * 0.024, 13.0, 22.0)
	var hoja := PanelContainer.new()
	var caja := StyleBoxFlat.new()
	caja.bg_color = PAPEL
	caja.set_content_margin_all(margen)
	caja.content_margin_bottom = margen * 0.8
	caja.shadow_color = Color(0, 0, 0, 0.45)
	caja.shadow_size = int(margen * 1.4)
	caja.shadow_offset = Vector2(0, margen * 0.4)
	caja.set_corner_radius_all(2)
	hoja.add_theme_stylebox_override("panel", caja)
	hoja.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", int(margen * 0.5))
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hoja.add_child(col)
	# la foto, recortada en su marco, se acerca despacio
	var marco := Control.new()
	marco.clip_contents = true
	marco.custom_minimum_size = Vector2(ancho_img, alto_img)
	marco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(marco)
	var foto := TextureRect.new()
	foto.texture = tex
	foto.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	foto.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	foto.size = Vector2(ancho_img, alto_img)
	foto.pivot_offset = foto.size * Vector2(randf_range(0.35, 0.65), randf_range(0.35, 0.6))
	foto.self_modulate = Color(1.0, 0.97, 0.9)          # papel viejo, sin teñir de sepia lo que es color
	foto.mouse_filter = Control.MOUSE_FILTER_IGNORE
	marco.add_child(foto)
	var tw := foto.create_tween()
	tw.tween_property(foto, "scale", Vector2(1.09, 1.09), 22.0).set_trans(Tween.TRANS_SINE)
	var pie := Label.new()
	pie.text = d.get("pie", "")
	pie.add_theme_font_override("font", _fuente(CURSIVA, 600))
	pie.add_theme_font_size_override("font_size", int(t_pie))
	pie.add_theme_color_override("font_color", TINTA)
	pie.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	pie.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	pie.custom_minimum_size.x = ancho_img
	col.add_child(pie)
	if d.get("fuente", "") != "":
		var fuente := Label.new()
		fuente.text = d["fuente"]
		fuente.add_theme_font_override("font", _fuente(NORMAL, 500))
		fuente.add_theme_font_size_override("font_size", int(t_pie * 0.66))
		fuente.add_theme_color_override("font_color", TINTA_SUAVE)
		fuente.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		fuente.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		fuente.custom_minimum_size.x = ancho_img
		col.add_child(fuente)
	return hoja

## Lámina al costado (a la derecha, arriba de la carta). Si es la misma que ya está, no hace nada.
func lado(d: Dictionary) -> void:
	var id: String = d.get("id", "")
	if id == _lado_id:
		return
	ocultar_lado()
	_lado_id = id
	var tex: Texture2D = await _textura(d)
	while _titulo.modulate.a > 0.02 and _lado_id == id:     # no tapa el título de la parada
		await get_tree().process_frame
	if tex == null or _lado_id != id:
		return
	var t := _tam()
	var alto_libre := t.y * 0.66 - _alto_barra()            # entre la barra de arriba y la carta
	var hoja := _montar(tex, d, alto_libre * 0.72, t.x * 0.42)
	_raiz.add_child(hoja)
	_raiz.move_child(hoja, _titulo.get_index())          # bajo el título y el telón
	hoja.reset_size()
	var x := t.x - hoja.size.x - t.x * 0.045
	var y := _alto_barra() + maxf((alto_libre - hoja.size.y) * 0.4, 8.0)
	hoja.pivot_offset = hoja.size * 0.5
	hoja.rotation = deg_to_rad(randf_range(1.0, 2.2) * (1 if randf() < 0.5 else -1))
	hoja.position = Vector2(x + 60.0, y)
	hoja.modulate.a = 0.0
	var tw := hoja.create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_property(hoja, "position:x", x, 0.9)
	tw.tween_property(hoja, "modulate:a", 1.0, 0.6)
	_lado = hoja

func ocultar_lado() -> void:
	_lado_id = ""
	if _lado == null or not is_instance_valid(_lado):
		return
	var h := _lado
	_lado = null
	var tw := h.create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	tw.tween_property(h, "modulate:a", 0.0, 0.5)
	tw.tween_property(h, "position:x", h.position.x + 40.0, 0.5)
	tw.chain().tween_callback(h.queue_free)

## Antes y ahora: la lámina grande al centro sobre la ciudad en penumbra; después se disuelve y queda la ciudad.
func fundido(d: Dictionary, quieta := 4.5, disolver := 3.2) -> void:
	var tex: Texture2D = await _textura(d)
	if tex == null:
		return
	if _fundido != null and is_instance_valid(_fundido):
		_fundido.queue_free()
	var t := _tam()
	var capa := Control.new()
	capa.set_anchors_preset(Control.PRESET_FULL_RECT)
	capa.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_raiz.add_child(capa)
	_raiz.move_child(capa, _titulo.get_index())          # bajo el título y el telón
	var sombra := ColorRect.new()
	sombra.color = Color(0.03, 0.025, 0.02, 0.82)
	sombra.set_anchors_preset(Control.PRESET_FULL_RECT)
	sombra.mouse_filter = Control.MOUSE_FILTER_IGNORE
	capa.add_child(sombra)
	var alto_libre := t.y * 0.70 - _alto_barra()
	var hoja := _montar(tex, d, alto_libre * 0.80, t.x * 0.7)
	capa.add_child(hoja)
	hoja.reset_size()
	hoja.position = Vector2((t.x - hoja.size.x) * 0.5, _alto_barra() + maxf((alto_libre - hoja.size.y) * 0.45, 6.0))
	hoja.pivot_offset = hoja.size * 0.5
	hoja.rotation = deg_to_rad(-0.8)
	capa.modulate.a = 0.0
	_fundido = capa
	var tw := capa.create_tween()
	tw.tween_property(capa, "modulate:a", 1.0, 0.8).set_trans(Tween.TRANS_SINE)
	tw.tween_interval(quieta)
	# la foto se desvanece primero sobre la penumbra, y después la penumbra deja ver la ciudad de hoy
	tw.tween_property(hoja, "modulate:a", 0.0, disolver).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(hoja, "scale", Vector2(1.06, 1.06), disolver)
	tw.parallel().tween_property(sombra, "color:a", 0.0, disolver * 1.15).set_trans(Tween.TRANS_SINE)
	tw.tween_callback(capa.queue_free)

func ocultar_todo() -> void:
	ocultar_lado()
	if _fundido != null and is_instance_valid(_fundido):
		_fundido.queue_free()
	_titulo.modulate.a = 0.0
	barras(false)
