class_name Interfaz
extends CanvasLayer
## Interfaz del juego, construida por código:
## HUD (mira, acción, misión, tiempo, avisos), fichas históricas con sus fuentes,
## diálogos, decisiones con "Lo que realmente pasó", diario de fichas y pantalla final.

const COLOR_FONDO := Color(0.09, 0.075, 0.06, 0.95)
const COLOR_DORADO := Color(0.82, 0.68, 0.42)
const COLOR_TEXTO := Color(0.95, 0.92, 0.86)
const COLOR_TENUE := Color(0.74, 0.69, 0.61)
const HEX_TENUE := "#bdb3a2"
const HEX_DORADO := "#d1ad6b"
const HEX_ESTADO := {
	"verificada": "#7fc27f",
	"fuentes_difieren": "#ecb54f",
	"por_verificar": "#e7766b",
}
const HEX_TIPO_FUENTE := {
	"oficial": "#7fc27f",
	"prensa": "#8fb3e0",
	"academica": "#c9a0e6",
	"enciclopedia": "#e7766b",
}

var jugador: Jugador
var gestor: GestorMisiones

var _tema: Theme
var _accion: Label
var _titulo_mision: Label
var _objetivos: RichTextLabel
var _tiempo: Label
var _avisos: VBoxContainer
var _capa_modal: ColorRect
var _panel_modal: PanelContainer
var _modal_abierto := false
var _diario_abierto := false
var _cronista_abierto := false
var _cliente_cronista: ClienteCronista
var _historial_cronista: Array[Dictionary] = []   # {quien, texto, fuentes} de esta partida


func _ready() -> void:
	layer = 10
	_tema = _crear_tema()
	_construir_hud()
	_construir_modal()
	_cliente_cronista = ClienteCronista.new()
	add_child(_cliente_cronista)


func configurar(nuevo_jugador: Jugador, nuevo_gestor: GestorMisiones) -> void:
	jugador = nuevo_jugador
	gestor = nuevo_gestor
	jugador.enfoque_cambiado.connect(func(texto: String) -> void: _accion.text = texto)
	gestor.mision_actualizada.connect(_al_actualizar_mision)
	gestor.tiempo_actualizado.connect(_al_actualizar_tiempo)
	gestor.escena_completada.connect(_mostrar_final)
	EstadoJuego.solicitud_ficha.connect(mostrar_ficha)
	EstadoJuego.solicitud_dialogo.connect(abrir_dialogo)
	EstadoJuego.solicitud_decision.connect(abrir_decision)
	EstadoJuego.aviso.connect(avisar)
	EstadoJuego.ficha_desbloqueada.connect(_al_desbloquear_ficha)
	_mostrar_bienvenida()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("diario"):
		if _diario_abierto:
			_cerrar_modal()
		elif not _modal_abierto:
			_mostrar_diario()
		get_viewport().set_input_as_handled()
	elif event is InputEventKey and event.pressed and not event.echo:
		var tecla := (event as InputEventKey).physical_keycode
		if tecla == KEY_C and not _modal_abierto and get_tree().get_first_node_in_group("cronista") != null:
			abrir_cronista()
			get_viewport().set_input_as_handled()
		elif tecla == KEY_ESCAPE and _cronista_abierto:
			_cerrar_cronista()
			get_viewport().set_input_as_handled()


# --- El cronista: preguntas libres sobre la historia ----------------------------

func abrir_cronista() -> void:
	var caja := _caja()
	caja.add_child(_etiqueta("EL CRONISTA", 14, COLOR_DORADO))
	caja.add_child(_parrafo("Pregúntame por la Asamblea de 1825, la Casa de la Libertad o la historia de Charcas. Respondo solo con lo que dicen mis fuentes, y te digo cuáles son.", 19, COLOR_TENUE))
	var conversacion := VBoxContainer.new()
	conversacion.add_theme_constant_override("separation", 10)
	caja.add_child(conversacion)
	for mensaje in _historial_cronista:
		_agregar_mensaje(conversacion, mensaje)
	var fila := HBoxContainer.new()
	fila.add_theme_constant_override("separation", 10)
	var entrada := LineEdit.new()
	entrada.placeholder_text = "Escribe tu pregunta y presiona Enter"
	entrada.max_length = 300
	entrada.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	entrada.custom_minimum_size = Vector2(0, 44)
	fila.add_child(entrada)
	var enviar := func() -> void: _preguntar_al_cronista(entrada, conversacion)
	entrada.text_submitted.connect(func(_t: String) -> void: enviar.call())
	fila.add_child(_boton("Preguntar", enviar))
	caja.add_child(fila)
	caja.add_child(_boton("Cerrar (Esc)", _cerrar_cronista))
	_abrir_modal(caja, true)
	_cronista_abierto = true
	entrada.grab_focus.call_deferred()


func _cerrar_cronista() -> void:
	_cronista_abierto = false
	_cronista_hablando(false)
	_cerrar_modal()


func _preguntar_al_cronista(entrada: LineEdit, conversacion: VBoxContainer) -> void:
	var pregunta := entrada.text.strip_edges()
	if pregunta.is_empty() or not entrada.editable:
		return
	entrada.text = ""
	entrada.editable = false
	var tuya := {"quien": "tu", "texto": pregunta, "fuentes": []}
	_historial_cronista.append(tuya)
	_agregar_mensaje(conversacion, tuya)
	var pensando := _parrafo("El cronista busca en sus fuentes…", 18, COLOR_TENUE)
	conversacion.add_child(pensando)
	_cronista_hablando(true)
	var datos := await _cliente_cronista.preguntar(pregunta)
	if not is_instance_valid(conversacion):
		return   # se cerró la ventana mientras respondía
	pensando.queue_free()
	var suya := {"quien": "cronista", "texto": str(datos.get("error", datos.get("respuesta", ""))), "fuentes": datos.get("fuentes", [])}
	_historial_cronista.append(suya)
	_agregar_mensaje(conversacion, suya)
	entrada.editable = true
	entrada.grab_focus()
	get_tree().create_timer(4.0).timeout.connect(func() -> void: _cronista_hablando(false))


func _agregar_mensaje(conversacion: VBoxContainer, mensaje: Dictionary) -> void:
	var es_cronista := str(mensaje.get("quien", "")) == "cronista"
	var texto := _texto_enriquecido(20)
	texto.custom_minimum_size.x = 700
	var quien := "[color=%s][b]El cronista:[/b][/color] " % HEX_DORADO if es_cronista else "[b]Tú:[/b] "
	var bb := quien + _escapar(str(mensaje.get("texto", "")))
	for fuente: Dictionary in mensaje.get("fuentes", []):
		var detalle := "[%d] %s" % [int(fuente.get("n", 0)), _escapar(str(fuente.get("fuente", "")))]
		var url := str(fuente.get("url", ""))
		bb += "\n[color=%s][font_size=15]%s[/font_size][/color]" % [HEX_TENUE, ("[url=%s]%s[/url]" % [url, detalle]) if url.begins_with("https://") else detalle]
	texto.text = bb
	texto.meta_clicked.connect(func(meta: Variant) -> void:
		if str(meta).begins_with("https://"):
			OS.shell_open(str(meta)))
	conversacion.add_child(texto)


func _cronista_hablando(si: bool) -> void:
	var cronista := get_tree().get_first_node_in_group("cronista")
	if cronista != null:
		cronista.set("hablando", si)


# --- Pantallas -----------------------------------------------------------------

func mostrar_ficha(ficha_id: String, al_cerrar: Callable = Callable()) -> void:
	var ficha := Fuentes.obtener_ficha(ficha_id)
	if ficha.is_empty():
		push_warning("[Interfaz] Ficha inexistente: %s" % ficha_id)
		if al_cerrar.is_valid():
			al_cerrar.call()
		return
	EstadoJuego.desbloquear_ficha(ficha_id)

	var caja := _caja()
	caja.add_child(_etiqueta("FICHA HISTÓRICA", 14, COLOR_TENUE))
	caja.add_child(_parrafo(str(ficha.get("titulo", "")), 30, COLOR_TEXTO))
	caja.add_child(_insignia_estado(ficha))

	var cuerpo := _texto_enriquecido(20)
	var bb := _escapar(str(ficha.get("texto", "")))
	if ficha.has("cita"):
		bb += "\n\n[color=%s][i]Texto de la fuente: “%s”[/i][/color]" % [HEX_TENUE, _escapar(str(ficha["cita"]))]
	if ficha.has("discrepancia"):
		bb += "\n\n[color=%s][b]Las fuentes no coinciden.[/b] %s[/color]" % [HEX_ESTADO["fuentes_difieren"], _escapar(str(ficha["discrepancia"]))]
	if ficha.has("nota"):
		bb += "\n\n[color=%s]Nota: %s[/color]" % [HEX_TENUE, _escapar(str(ficha["nota"]))]
	cuerpo.text = bb
	caja.add_child(cuerpo)

	caja.add_child(HSeparator.new())
	caja.add_child(_etiqueta("Fuentes", 18, COLOR_DORADO))
	caja.add_child(_lista_fuentes(Fuentes.fuentes_de(ficha)))
	caja.add_child(_etiqueta(_texto_revision(ficha), 14, COLOR_TENUE))

	var al_presionar := func() -> void:
		if al_cerrar.is_valid():
			al_cerrar.call()
		else:
			_cerrar_modal()
	caja.add_child(_boton("Volver" if al_cerrar.is_valid() else "Cerrar", al_presionar))
	_abrir_modal(caja, true)


func abrir_dialogo(id_personaje: String) -> void:
	var variante := gestor.dialogo_para(id_personaje)
	if variante.is_empty():
		return
	_mostrar_linea(id_personaje, variante, 0)


func abrir_decision(id_decision: String) -> void:
	var decision := gestor.decision(id_decision)
	if decision.is_empty():
		_cerrar_modal()
		return
	var caja := _caja()
	caja.add_child(_etiqueta("DECISIÓN", 14, COLOR_TENUE))
	caja.add_child(_parrafo(str(decision.get("pregunta", "")), 28, COLOR_TEXTO))
	caja.add_child(_parrafo(str(decision.get("contexto", "")), 18, COLOR_TENUE))
	for opcion: Dictionary in decision.get("opciones", []):
		var boton := _boton(str(opcion.get("texto", "")), func() -> void: _elegir(id_decision, decision, opcion))
		boton.custom_minimum_size.y = 50
		caja.add_child(boton)
	_abrir_modal(caja)


func avisar(texto: String) -> void:
	var etiqueta := _parrafo(texto, 18, COLOR_TEXTO)
	etiqueta.custom_minimum_size.x = 520
	etiqueta.add_theme_constant_override("outline_size", 6)
	etiqueta.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	_avisos.add_child(etiqueta)
	if _avisos.get_child_count() > 5:
		var primero := _avisos.get_child(0)
		_avisos.remove_child(primero)
		primero.queue_free()
	var tween := etiqueta.create_tween()
	tween.tween_interval(4.5)
	tween.tween_property(etiqueta, "modulate:a", 0.0, 0.8)
	tween.tween_callback(etiqueta.queue_free)


func _mostrar_bienvenida() -> void:
	var datos := gestor.datos
	var caja := _caja()
	caja.add_child(_etiqueta("VIVE LA HISTORIA · CASA DE LA LIBERTAD", 14, COLOR_TENUE))
	caja.add_child(_parrafo(str(datos.get("titulo", "")), 34, COLOR_TEXTO))
	caja.add_child(_parrafo(str(datos.get("subtitulo", "")), 18, COLOR_DORADO))
	caja.add_child(_parrafo(str(datos.get("aviso_recreacion", "")), 17, COLOR_TENUE))
	caja.add_child(HSeparator.new())
	var controles := _texto_enriquecido(17)
	controles.text = "[b]WASD[/b] moverse   [b]Shift[/b] correr   [b]Espacio[/b] saltar   [b]E[/b] usar\n[b]R[/b] inspeccionar lo que tienes en la mano   [b]Tab[/b] diario de fichas y fuentes\n[b]C[/b] pregúntale al cronista, que camina contigo\nHaz clic en la pantalla para controlar la cámara. [b]Esc[/b] libera el ratón."
	caja.add_child(controles)
	caja.add_child(_boton("Comenzar", _cerrar_modal))
	_abrir_modal(caja)


func _mostrar_diario() -> void:
	var caja := _caja()
	caja.add_child(_etiqueta("DIARIO", 14, COLOR_TENUE))
	caja.add_child(_parrafo("Fichas desbloqueadas: %d" % EstadoJuego.fichas_desbloqueadas.size(), 28, COLOR_TEXTO))
	if EstadoJuego.fichas_desbloqueadas.is_empty():
		caja.add_child(_parrafo("Todavía no hay fichas. Habla con los personajes y observa los objetos.", 18, COLOR_TENUE))
	else:
		var lista := _texto_enriquecido(19)
		var bb := ""
		for id_ficha: String in EstadoJuego.fichas_desbloqueadas:
			var ficha := Fuentes.obtener_ficha(id_ficha)
			bb += "[url=ficha:%s]%s[/url]  [color=%s]%s[/color]\n" % [
				id_ficha, _escapar(str(ficha.get("titulo", id_ficha))),
				HEX_ESTADO.get(ficha.get("estado", ""), HEX_TENUE), Fuentes.etiqueta_estado(ficha)]
		lista.text = bb
		lista.meta_clicked.connect(func(meta: Variant) -> void:
			var enlace := str(meta)
			if enlace.begins_with("ficha:"):
				mostrar_ficha(enlace.trim_prefix("ficha:"), _mostrar_diario))
		caja.add_child(lista)
		caja.add_child(HSeparator.new())
		caja.add_child(_etiqueta("Fuentes citadas", 18, COLOR_DORADO))
		caja.add_child(_lista_fuentes(Fuentes.fuentes_de_fichas(EstadoJuego.fichas_desbloqueadas)))
	caja.add_child(_boton("Cerrar", _cerrar_modal))
	_abrir_modal(caja, true)
	_diario_abierto = true


func _mostrar_final(escena: Dictionary) -> void:
	_tiempo.text = ""
	_titulo_mision.text = "Escena completada"
	_objetivos.text = ""
	var cierre: Dictionary = escena.get("cierre", {})
	var caja := _caja()
	caja.add_child(_etiqueta("ESCENA COMPLETADA", 14, COLOR_TENUE))
	caja.add_child(_parrafo(str(cierre.get("titulo", "")), 32, COLOR_TEXTO))
	caja.add_child(_parrafo(str(cierre.get("texto", "")), 19, COLOR_TEXTO))

	caja.add_child(HSeparator.new())
	caja.add_child(_etiqueta("Tus decisiones frente a lo que pasó", 18, COLOR_DORADO))
	var resumen := _texto_enriquecido(18)
	var bb := ""
	var decisiones: Dictionary = escena.get("decisiones", {})
	for id_decision: String in decisiones:
		var decision: Dictionary = decisiones[id_decision]
		var elegida := str(EstadoJuego.decisiones.get(id_decision, ""))
		var texto_elegido := "sin responder"
		for opcion: Dictionary in decision.get("opciones", []):
			if str(opcion.get("id", "")) == elegida:
				texto_elegido = str(opcion.get("texto", ""))
		var ficha := Fuentes.obtener_ficha(str(decision.get("ficha_resultado", "")))
		bb += "[b]%s[/b]\nTu respuesta: %s\nLo que pasó: [url=ficha:%s]%s[/url]\n\n" % [
			_escapar(str(decision.get("pregunta", ""))), _escapar(texto_elegido),
			decision.get("ficha_resultado", ""), _escapar(str(ficha.get("titulo", "")))]
	resumen.text = bb
	resumen.meta_clicked.connect(func(meta: Variant) -> void:
		mostrar_ficha(str(meta).trim_prefix("ficha:"), _mostrar_final.bind(escena)))
	caja.add_child(resumen)

	var fuentes := Fuentes.fuentes_de_fichas(EstadoJuego.fichas_desbloqueadas)
	var oficiales := fuentes.filter(func(f: Dictionary) -> bool: return f.get("tipo", "") == "oficial").size()
	caja.add_child(HSeparator.new())
	caja.add_child(_etiqueta("Fuentes de esta escena", 18, COLOR_DORADO))
	caja.add_child(_parrafo("%d fichas desbloqueadas · %d fuentes citadas (%d oficiales)" % [
		EstadoJuego.fichas_desbloqueadas.size(), fuentes.size(), oficiales], 16, COLOR_TENUE))
	caja.add_child(_lista_fuentes(fuentes))

	var reiniciar := func() -> void:
		EstadoJuego.reiniciar()
		get_tree().reload_current_scene()
	caja.add_child(_boton("Jugar de nuevo", reiniciar))
	_abrir_modal(caja, true)


# --- Diálogos y decisiones -----------------------------------------------------

func _mostrar_linea(id_personaje: String, variante: Dictionary, indice: int) -> void:
	var lineas: Array = variante.get("lineas", [])
	if indice >= lineas.size():
		_cerrar_modal()
		_terminar_dialogo(id_personaje, variante)
		return
	var linea: Dictionary = lineas[indice]
	var info := gestor.personaje(id_personaje)
	var caja := _caja()
	caja.add_child(_parrafo(str(info.get("nombre", id_personaje)), 26, COLOR_DORADO))
	var rol := str(info.get("rol", ""))
	if bool(info.get("ficticio", false)):
		rol += " · personaje ficticio"
	caja.add_child(_etiqueta(rol, 15, COLOR_TENUE))
	caja.add_child(_parrafo(str(linea.get("texto", "")), 22, COLOR_TEXTO))
	caja.add_child(HSeparator.new())

	var botones := HBoxContainer.new()
	botones.add_theme_constant_override("separation", 12)
	var id_ficha := str(linea.get("ficha", ""))
	if id_ficha.is_empty():
		caja.add_child(_parrafo("Recreación: esta línea no es un dato histórico.", 14, COLOR_TENUE))
	else:
		EstadoJuego.desbloquear_ficha(id_ficha)
		var ficha := Fuentes.obtener_ficha(id_ficha)
		var fuentes := Fuentes.fuentes_de(ficha)
		var origen := str(fuentes[0].get("institucion", "")) if not fuentes.is_empty() else ""
		caja.add_child(_parrafo("Diálogo recreado. Dato histórico respaldado por: %s" % origen, 14, COLOR_TENUE))
		botones.add_child(_boton("Ver ficha y fuente", func() -> void:
			mostrar_ficha(id_ficha, _mostrar_linea.bind(id_personaje, variante, indice))))
	botones.add_child(_boton("Continuar", _mostrar_linea.bind(id_personaje, variante, indice + 1)))
	caja.add_child(botones)
	_abrir_modal(caja)


func _terminar_dialogo(id_personaje: String, variante: Dictionary) -> void:
	EstadoJuego.registrar("hablar", id_personaje)
	var fin: Dictionary = variante.get("al_terminar", {})
	if fin.has("entregar"):
		var id_objeto := str(fin["entregar"])
		var datos_objeto := gestor.objeto(id_objeto)
		EstadoJuego.registrar("tomar", id_objeto)
		EstadoJuego.desbloquear_ficha(str(datos_objeto.get("ficha", "")))
		avisar("Recibiste: %s" % datos_objeto.get("nombre", id_objeto))
	if fin.has("decision") and not EstadoJuego.decisiones.has(str(fin["decision"])):
		abrir_decision(str(fin["decision"]))


func _elegir(id_decision: String, decision: Dictionary, opcion: Dictionary) -> void:
	EstadoJuego.tomar_decision(id_decision, str(opcion.get("id", "")))
	var caja := _caja()
	caja.add_child(_etiqueta("TU DECISIÓN", 14, COLOR_TENUE))
	caja.add_child(_parrafo(str(opcion.get("texto", "")), 28, COLOR_TEXTO))
	caja.add_child(_parrafo(str(opcion.get("reaccion", "")), 19, COLOR_TEXTO))
	var continuar := func() -> void:
		var siguiente := str(decision.get("siguiente", ""))
		if siguiente.is_empty():
			_cerrar_modal()
		else:
			abrir_decision(siguiente)
	caja.add_child(_boton("Lo que realmente pasó", func() -> void:
		mostrar_ficha(str(decision.get("ficha_resultado", "")), continuar)))
	_abrir_modal(caja)


# --- HUD -----------------------------------------------------------------------

func _al_actualizar_mision(mision: Dictionary, objetivos: Array) -> void:
	_titulo_mision.text = str(mision.get("titulo", ""))
	var bb := "[color=%s]%s[/color]\n" % [HEX_TENUE, _escapar(str(mision.get("descripcion", "")))]
	for objetivo: Dictionary in objetivos:
		if objetivo["cumplido"]:
			bb += "[color=#7fc27f][s]%s[/s][/color]\n" % _escapar(str(objetivo["texto"]))
		else:
			bb += "- %s\n" % _escapar(str(objetivo["texto"]))
	_objetivos.text = bb
	if float(mision.get("tiempo_limite", 0)) <= 0.0:
		_tiempo.text = ""


func _al_actualizar_tiempo(segundos: float) -> void:
	var total := ceili(segundos)
	_tiempo.text = "Tiempo %d:%02d" % [total / 60, total % 60]
	_tiempo.add_theme_color_override("font_color", Color(0.95, 0.4, 0.35) if total <= 30 else COLOR_TEXTO)


func _al_desbloquear_ficha(ficha_id: String) -> void:
	var ficha := Fuentes.obtener_ficha(ficha_id)
	avisar("Nueva ficha en el diario: %s  [Tab]" % ficha.get("titulo", ficha_id))


# --- Construcción --------------------------------------------------------------

func _construir_hud() -> void:
	var raiz := Control.new()
	raiz.theme = _tema
	raiz.set_anchors_preset(Control.PRESET_FULL_RECT)
	raiz.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(raiz)

	var centro := CenterContainer.new()
	centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	centro.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(centro)
	var mira := _etiqueta("+", 24, Color(1, 1, 1, 0.85))
	mira.add_theme_constant_override("outline_size", 4)
	mira.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.7))
	centro.add_child(mira)

	_accion = _etiqueta("", 22, COLOR_TEXTO)
	_accion.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_accion.add_theme_constant_override("outline_size", 8)
	_accion.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	_accion.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_accion.offset_top = -120
	_accion.offset_bottom = -80
	raiz.add_child(_accion)

	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _estilo(Color(0.06, 0.05, 0.04, 0.72), 0, 16))
	panel.position = Vector2(20, 20)
	panel.custom_minimum_size = Vector2(420, 0)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(panel)
	var caja_mision := VBoxContainer.new()
	panel.add_child(caja_mision)
	_titulo_mision = _etiqueta("", 21, COLOR_DORADO)
	caja_mision.add_child(_titulo_mision)
	_objetivos = _texto_enriquecido(16)
	caja_mision.add_child(_objetivos)

	_tiempo = _etiqueta("", 28, COLOR_TEXTO)
	_tiempo.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_tiempo.add_theme_constant_override("outline_size", 8)
	_tiempo.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	_tiempo.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_tiempo.offset_left = -260
	_tiempo.offset_right = -24
	_tiempo.offset_top = 20
	_tiempo.offset_bottom = 60
	raiz.add_child(_tiempo)

	_avisos = VBoxContainer.new()
	_avisos.alignment = BoxContainer.ALIGNMENT_END
	_avisos.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_avisos.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_avisos.offset_left = 20
	_avisos.offset_right = 560
	_avisos.offset_top = -300
	_avisos.offset_bottom = -20
	raiz.add_child(_avisos)


func _construir_modal() -> void:
	_capa_modal = ColorRect.new()
	_capa_modal.theme = _tema
	_capa_modal.color = Color(0, 0, 0, 0.55)
	_capa_modal.set_anchors_preset(Control.PRESET_FULL_RECT)
	_capa_modal.visible = false
	add_child(_capa_modal)
	var centro := CenterContainer.new()
	centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	_capa_modal.add_child(centro)
	_panel_modal = PanelContainer.new()
	_panel_modal.add_theme_stylebox_override("panel", _estilo(COLOR_FONDO, 2, 28))
	_panel_modal.custom_minimum_size = Vector2(780, 0)
	centro.add_child(_panel_modal)


func _abrir_modal(contenido: Control, con_desplazamiento := false) -> void:
	for hijo in _panel_modal.get_children():
		_panel_modal.remove_child(hijo)
		hijo.queue_free()
	if con_desplazamiento:
		var desplazable := ScrollContainer.new()
		desplazable.custom_minimum_size = Vector2(740, 540)
		desplazable.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
		contenido.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		desplazable.add_child(contenido)
		_panel_modal.add_child(desplazable)
	else:
		_panel_modal.add_child(contenido)
	_capa_modal.visible = true
	_modal_abierto = true
	_diario_abierto = false
	if jugador != null:
		jugador.controles_activos = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_enfocar_ultimo_boton.call_deferred(contenido)


func _cerrar_modal() -> void:
	for hijo in _panel_modal.get_children():
		_panel_modal.remove_child(hijo)
		hijo.queue_free()
	_capa_modal.visible = false
	_modal_abierto = false
	_diario_abierto = false
	if jugador != null:
		jugador.controles_activos = true
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _enfocar_ultimo_boton(contenido: Control) -> void:
	if not is_instance_valid(contenido) or not contenido.is_inside_tree():
		return
	var botones := contenido.find_children("*", "Button", true, false)
	if not botones.is_empty():
		(botones.back() as Button).grab_focus()


func _lista_fuentes(fuentes: Array) -> RichTextLabel:
	var lista := _texto_enriquecido(17)
	var bb := ""
	for fuente: Dictionary in fuentes:
		var tipo := str(fuente.get("tipo", ""))
		var detalle := str(fuente.get("titulo", ""))
		if fuente.has("autor"):
			detalle += ", " + str(fuente["autor"])
		if fuente.has("publicado"):
			detalle += " (%s)" % _fecha(str(fuente["publicado"]))
		bb += "[color=%s][b]%s[/b][/color]  %s\n" % [HEX_TIPO_FUENTE.get(tipo, HEX_TENUE), Fuentes.etiqueta_tipo(fuente).to_upper(), _escapar(str(fuente.get("institucion", "")))]
		bb += "[url=%s]%s[/url]\n" % [fuente.get("url", ""), _escapar(detalle)]
		bb += "[color=%s]%s · consultado el %s[/color]\n\n" % [HEX_TENUE, str(fuente.get("url", "")).trim_prefix("https://"), _fecha(str(fuente.get("consultado", "")))]
	lista.text = bb.strip_edges()
	lista.meta_clicked.connect(func(meta: Variant) -> void:
		var enlace := str(meta)
		if enlace.begins_with("https://"):
			OS.shell_open(enlace))
	return lista


func _insignia_estado(ficha: Dictionary) -> Control:
	var estado := str(ficha.get("estado", ""))
	var etiqueta := _etiqueta(Fuentes.etiqueta_estado(ficha).to_upper(), 14, Color.html(HEX_ESTADO.get(estado, HEX_TENUE)))
	var contenedor := HBoxContainer.new()
	contenedor.add_child(etiqueta)
	return contenedor


func _texto_revision(ficha: Dictionary) -> String:
	var revision: Dictionary = ficha.get("revision", {})
	if Fuentes.esta_aprobada(ficha):
		return "Revisada por %s el %s." % [revision.get("revisor", ""), _fecha(str(revision.get("fecha", "")))]
	return "Revisión docente pendiente."


func _caja() -> VBoxContainer:
	var caja := VBoxContainer.new()
	caja.add_theme_constant_override("separation", 12)
	return caja


func _etiqueta(texto: String, tamano: int, color: Color) -> Label:
	var etiqueta := Label.new()
	etiqueta.text = texto
	etiqueta.add_theme_font_size_override("font_size", tamano)
	etiqueta.add_theme_color_override("font_color", color)
	etiqueta.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return etiqueta


func _parrafo(texto: String, tamano: int, color: Color) -> Label:
	var etiqueta := _etiqueta(texto, tamano, color)
	etiqueta.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return etiqueta


func _texto_enriquecido(tamano: int) -> RichTextLabel:
	var texto := RichTextLabel.new()
	texto.bbcode_enabled = true
	texto.fit_content = true
	texto.scroll_active = false
	texto.custom_minimum_size.x = 380
	texto.add_theme_font_size_override("normal_font_size", tamano)
	texto.add_theme_font_size_override("bold_font_size", tamano)
	texto.add_theme_font_size_override("italics_font_size", tamano)
	texto.add_theme_color_override("default_color", COLOR_TEXTO)
	return texto


func _boton(texto: String, al_presionar: Callable) -> Button:
	var boton := Button.new()
	boton.text = texto
	boton.custom_minimum_size = Vector2(0, 44)
	boton.pressed.connect(al_presionar)
	return boton


func _estilo(fondo: Color, borde: int, margen: int) -> StyleBoxFlat:
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = fondo
	estilo.border_color = COLOR_DORADO
	estilo.set_border_width_all(borde)
	estilo.set_corner_radius_all(10)
	estilo.set_content_margin_all(margen)
	return estilo


func _crear_tema() -> Theme:
	var tema := Theme.new()
	tema.default_font_size = 18
	var normal := _estilo(Color(0.2, 0.16, 0.11, 1.0), 1, 10)
	var encima := _estilo(Color(0.32, 0.25, 0.15, 1.0), 2, 10)
	var presionado := _estilo(Color(0.45, 0.35, 0.2, 1.0), 2, 10)
	tema.set_stylebox("normal", "Button", normal)
	tema.set_stylebox("hover", "Button", encima)
	tema.set_stylebox("focus", "Button", encima)
	tema.set_stylebox("pressed", "Button", presionado)
	tema.set_color("font_color", "Button", COLOR_TEXTO)
	tema.set_color("font_hover_color", "Button", Color.WHITE)
	tema.set_color("font_focus_color", "Button", Color.WHITE)
	tema.set_font_size("font_size", "Button", 19)
	return tema


func _escapar(texto: String) -> String:
	return texto.replace("[", "[lb]")


func _fecha(iso: String) -> String:
	var partes := iso.split("-")
	if partes.size() != 3:
		return iso
	return "%s/%s/%s" % [partes[2], partes[1], partes[0]]
