class_name Cronista
extends CharacterBody3D
## El cronista acompaña al jugador por la escena: camina un paso atrás y a su izquierda, se detiene cuando el jugador
## se detiene y lo mira. Con C se le pregunta por la historia (interfaz.gd → abrir_cronista); mientras responde, gesticula.
## No bloquea al jugador (capa de colisión 0) y, si se queda atrás o atascado, reaparece cerca de él.

@export var modelo: PackedScene
## Dónde se ubica respecto del jugador (metros): atrás (+) y a la derecha (+) / izquierda (−).
@export var atras := 1.3
@export var al_lado := -1.0
@export var velocidad := 3.2

const VELOCIDAD_ALCANZAR := 5.6   # si queda a más de 4 m, apura el paso
const DISTANCIA_REAPARECER := 12.0
const ZANCADA := 1.25             # m por ciclo de la animación "caminar" (1,1 s): ajusta la cadencia a la velocidad

var hablando := false:
	set(v):
		hablando = v
		_actualizar_animacion(0.0)

var _jugador: Node3D
var _modelo: Node3D
var _anim: AnimationPlayer
var _actual := ""
var _gravedad := float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.8))
var _atascado := 0.0
var _ultima := Vector3.ZERO


func _ready() -> void:
	add_to_group("cronista")
	collision_layer = 0
	var forma := CollisionShape3D.new()
	var capsula := CapsuleShape3D.new()
	capsula.radius = 0.28
	capsula.height = 1.7
	forma.shape = capsula
	forma.position.y = 0.85
	add_child(forma)
	if modelo != null:
		_modelo = modelo.instantiate() as Node3D
		_modelo.name = "Modelo"
		add_child(_modelo)
		_anim = _modelo.find_child("AnimationPlayer", true, false) as AnimationPlayer
	var etiqueta := Label3D.new()
	etiqueta.text = "El cronista\n[C] preguntar"
	etiqueta.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	etiqueta.font_size = 26
	etiqueta.pixel_size = 0.0022
	etiqueta.outline_size = 8
	etiqueta.position = Vector3(0.0, 2.1, 0.0)
	etiqueta.visibility_range_end = 7.0
	add_child(etiqueta)
	_reproducir("reposo")


func _physics_process(delta: float) -> void:
	if _jugador == null:
		_jugador = get_tree().get_first_node_in_group("jugador") as Node3D
		if _jugador == null:
			return
		collision_mask = (_jugador as CollisionObject3D).collision_mask
	var base := _jugador.global_transform.basis
	var detras := Vector3(base.z.x, 0.0, base.z.z).normalized()
	var derecha := Vector3(base.x.x, 0.0, base.x.z).normalized()
	var objetivo := _jugador.global_position + detras * atras + derecha * al_lado
	var hacia := objetivo - global_position
	hacia.y = 0.0
	var distancia := hacia.length()

	if global_position.distance_to(_jugador.global_position) > DISTANCIA_REAPARECER or _atascado > 2.5:
		_reaparecer(objetivo)
		return

	var deseada := Vector3.ZERO
	if distancia > 0.4 and not hablando:
		var v := VELOCIDAD_ALCANZAR if distancia > 4.0 else velocidad
		deseada = hacia / distancia * minf(v, distancia * 2.5)
	velocity.x = move_toward(velocity.x, deseada.x, 9.0 * delta)
	velocity.z = move_toward(velocity.z, deseada.z, 9.0 * delta)
	velocity.y = -0.5 if is_on_floor() else velocity.y - _gravedad * delta
	move_and_slide()

	# Atasco: quiere avanzar pero no se mueve (una puerta, un escalón)
	if deseada.length() > 0.5 and global_position.distance_to(_ultima) < 0.01:
		_atascado += delta
	else:
		_atascado = 0.0
	_ultima = global_position

	# Mira hacia donde camina; quieto, hacia el jugador
	if _modelo != null:
		var horizontal := Vector3(velocity.x, 0.0, velocity.z)
		var mirar := horizontal if horizontal.length() > 0.3 else _jugador.global_position - global_position
		mirar.y = 0.0
		if mirar.length() > 0.05:
			_modelo.rotation.y = lerp_angle(_modelo.rotation.y, atan2(mirar.x, mirar.z), clampf(7.0 * delta, 0.0, 1.0))
	_actualizar_animacion(Vector3(velocity.x, 0.0, velocity.z).length())


func _reaparecer(objetivo: Vector3) -> void:
	global_position = objetivo + Vector3.UP * 0.3
	velocity = Vector3.ZERO
	_atascado = 0.0
	_ultima = global_position


func _actualizar_animacion(rapidez: float) -> void:
	if hablando:
		_reproducir("hablar")
	elif rapidez > 0.35:
		_reproducir("caminar")
		if _anim != null:
			_anim.speed_scale = clampf(rapidez * 1.1 / ZANCADA, 0.6, 2.2)
	else:
		_reproducir("reposo")


func _reproducir(nombre: String) -> void:
	if _anim == null or _actual == nombre or not _anim.has_animation(nombre):
		return
	_actual = nombre
	_anim.get_animation(nombre).loop_mode = Animation.LOOP_LINEAR
	if nombre != "caminar":
		_anim.speed_scale = 1.0
	_anim.play(nombre, 0.3)
