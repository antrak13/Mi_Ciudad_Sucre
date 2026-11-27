class_name Personaje
extends Interactuable
## Personaje con el que se habla. Los diálogos están en el JSON de la escena.
## Si el jugador lleva el Acta y este personaje puede firmar, en vez de hablar firma.

## Tipo de evento que registra su firma: "firma" (diputado) o "firma_presidente".
@export var tipo_firma := ""
## Firmas de diputados que deben existir antes de que este personaje firme.
@export var firmas_requeridas := 0
@export var objeto_para_firmar := "acta"
## Modelo 3D del personaje (.glb de Blender). Reemplaza al hijo "Modelo" provisional.
@export var modelo: PackedScene
## Animación que se reproduce en bucle si el modelo trae un AnimationPlayer.
@export var animacion_reposo := "idle"
## Animación mientras conversa con el jugador (si el modelo la trae).
@export var animacion_hablar := "hablar"
## Gira la cabeza y el cuerpo hacia el jugador cuando está cerca.
@export var mirar_al_jugador := true

const RADIO_MIRAR := 5.0
const RADIO_SOLTAR := 6.5           # al alejarse más que esto, deja de hablar aunque el diálogo no se cerrara
const GIRO_POR_SEGUNDO := 4.0

var es_ficticio := false
var _etiqueta: Label3D
var _modelo: Node3D
var _reproductor: AnimationPlayer
var _jugador: Node3D
var _hablando := false


func _ready() -> void:
	_cargar_modelo()
	super()
	verbo = "Hablar con"
	add_to_group("personajes")
	EstadoJuego.solicitud_dialogo.connect(_al_empezar_dialogo)
	EstadoJuego.evento_registrado.connect(_al_registrar)


func _process(delta: float) -> void:
	if _modelo == null or not mirar_al_jugador:
		return
	if _jugador == null:
		_jugador = get_tree().get_first_node_in_group("jugador") as Node3D
		if _jugador == null:
			return
	var hacia := _jugador.global_position - global_position
	hacia.y = 0.0
	var distancia := hacia.length()
	if _hablando and distancia > RADIO_SOLTAR:
		_dejar_de_hablar()
	# Giro del modelo (no del cuerpo de colisión): hacia el jugador si está cerca, si no a su orientación original.
	var objetivo := 0.0
	if distancia < RADIO_MIRAR and distancia > 0.01:
		var local := global_transform.basis.inverse() * hacia
		objetivo = atan2(local.x, local.z)
	_modelo.rotation.y = lerp_angle(_modelo.rotation.y, objetivo, clampf(GIRO_POR_SEGUNDO * delta, 0.0, 1.0))


func _al_empezar_dialogo(personaje_id: String) -> void:
	if personaje_id != id_interaccion:
		return
	_hablando = true
	_reproducir(animacion_hablar)


func _al_registrar(tipo: String, id: String) -> void:
	if tipo == "hablar" and id == id_interaccion:
		_dejar_de_hablar()


func _dejar_de_hablar() -> void:
	_hablando = false
	_reproducir(animacion_reposo)


## Reproduce en bucle una animación del modelo con un fundido corto; si no la tiene, no hace nada.
func _reproducir(nombre: String) -> void:
	if _reproductor == null or not _reproductor.has_animation(nombre):
		return
	_reproductor.get_animation(nombre).loop_mode = Animation.LOOP_LINEAR
	_reproductor.play(nombre, 0.35)


## Recibe nombre, rol y si es ficticio desde los datos de la escena.
func configurar(datos: Dictionary) -> void:
	if datos.is_empty():
		push_warning("[Personaje] '%s' no está en el JSON de la escena." % id_interaccion)
		return
	nombre_visible = str(datos.get("nombre", nombre_visible))
	es_ficticio = bool(datos.get("ficticio", false))
	if ficha_id.is_empty():
		ficha_id = str(datos.get("ficha", ""))
	_crear_etiqueta(str(datos.get("rol", "")))


func texto_para(jugador: Jugador) -> String:
	if _puede_firmar(jugador):
		return "[E] Pedir la firma de %s" % nombre_visible
	return "[E] Hablar con %s" % nombre_visible


func interactuar(jugador: Jugador) -> void:
	if _puede_firmar(jugador):
		var firmadas := EstadoJuego.cantidad("firma", "*")
		if firmadas < firmas_requeridas:
			EstadoJuego.aviso.emit("%s: primero consiga %d firmas de diputados (lleva %d)." % [nombre_visible, firmas_requeridas, firmadas])
			return
		EstadoJuego.registrar(tipo_firma, id_interaccion)
		EstadoJuego.aviso.emit("%s firmó el Acta." % nombre_visible)
		return
	EstadoJuego.solicitud_dialogo.emit(id_interaccion)


func _puede_firmar(jugador: Jugador) -> bool:
	return not tipo_firma.is_empty() \
		and jugador.sostiene(objeto_para_firmar) \
		and EstadoJuego.cantidad(tipo_firma, id_interaccion) == 0


func _cargar_modelo() -> void:
	if modelo == null:
		return
	var provisional := get_node_or_null("Modelo")
	if provisional != null:
		remove_child(provisional)
		provisional.queue_free()
	var instancia := modelo.instantiate()
	instancia.name = "Modelo"
	add_child(instancia)
	_modelo = instancia as Node3D
	_reproductor = instancia.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if _reproductor == null:
		return
	if not _reproductor.has_animation(animacion_reposo) and not _reproductor.get_animation_list().is_empty():
		animacion_reposo = _reproductor.get_animation_list()[0]
	_reproducir(animacion_reposo)
	# Cada personaje arranca en otro punto del ciclo, para que no respiren todos a la vez.
	if _reproductor.is_playing():
		_reproductor.seek(randf() * _reproductor.current_animation_length, true)


func _crear_etiqueta(rol: String) -> void:
	if _etiqueta == null:
		_etiqueta = Label3D.new()
		_etiqueta.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		_etiqueta.font_size = 30
		_etiqueta.pixel_size = 0.0022
		_etiqueta.outline_size = 8
		_etiqueta.position = Vector3(0.0, 2.05, 0.0)
		_etiqueta.visibility_range_end = 9.0
		_etiqueta.visibility_range_end_margin = 1.0
		add_child(_etiqueta)
	var texto := nombre_visible
	if not rol.is_empty():
		texto += "\n" + rol
	if es_ficticio:
		texto += "\n(personaje ficticio)"
	_etiqueta.text = texto
