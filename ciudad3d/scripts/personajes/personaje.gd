class_name Personaje
extends Node3D
## Un personaje de la ciudad: su modelo (GLB bajado de datos/personajes/), su mecánica (ciclo de clips), su manera de
## moverse (datos "movimiento", ver abajo), la cabeza que sigue al caminante cuando está cerca y el giro del cuerpo hacia
## él durante un encuentro.
## Los datos vienen de datos/personajes.json (contenido/personajes.json + personas/encuentros/guiones.md).
## Convención de los modelos: frente en +Z, origen entre los pies.

const HUESOS_CABEZA := ["DEF-head", "cabeza", "head", "Head"]   # Rigify, esqueleto del sirviente y otros
const GIRO_CABEZA_MAX := deg_to_rad(65.0)
const VEL_GIRO := 4.0                    # 1/s, giro del cuerpo (exponencial)

var datos: Dictionary
var id := ""
var anim: AnimationPlayer
var _mecanica: Array = []
var _paso := 0
var _rumbo_reposo := 0.0
var _rumbo_objetivo := 0.0
var _hablando := false
var _gesto_en_curso := false
var _mirar := LookAtModifier3D.new()
var _objetivo := Marker3D.new()
var _atencion := 0.0
var _atencion_objetivo := 0.0

# ------------------------------------------------------------------------------------------------- movimiento
## datos "movimiento" (contenido/personajes.json):
##   modo "pasear"     va de un punto a otro de su ronda; en cada parada hace 'paradas' clips de su mecánica. Si el
##                     caminante se le acerca (< DETENERSE) se para y lo mira: así se le puede hablar.
##   modo "huir"       pasea, pero cuando el caminante se acerca (< 'distancia') corre ('clip_huir') a otro punto, se
##                     esconde y se asoma; después de 'huidas' veces se deja alcanzar un rato (el niño del caballito).
##   modo "apartarse"  pasea pegado a las paredes; si el caminante se acerca, se hace a un lado ('clip_huir' corto) y
##                     sigue (el sirviente mudo).
##   modo "rondar"     trota entre puntos; si el caminante está cerca, da vueltas alrededor de él (el perro).
##   "acompana": <id>  (fuera de "movimiento") sigue a ese personaje a un paso, detrás y a un lado.
## Los clips de andar no traen desplazamiento: el cuerpo lo mueve este script, a 'vel' m/s.
## La ronda (puntos de suelo libre, fuera de la calzada y a la vista desde su lugar) la arma Encuentros al colocarlo.
const DETENERSE := 3.6
const REANUDAR := 6.0
const CLIPS_ANDAR := ["caminar", "caminar_rapido", "huir", "trotar", "sigilo", "fanfarron_caminar", "paseo_beneficencia",
	"galopar_palo", "correr_falda", "rodear_jugador"]
enum Estado { PARADA, ANDANDO, DETENIDO, HUYENDO, RODEANDO, ACOMPANANDO }
var ronda: Array[Vector3] = []             # ronda[0] = su lugar
var guia: Personaje                        # a quién acompaña
var _mov: Dictionary = {}
var _estado := Estado.PARADA
var _destino := Vector3.ZERO
var _i_ronda := 0
var _clips_parada := 0
var _vel := 1.0
var _clip_andando := ""
var _huidas := 0
var _calma := 0.0                          # s que se deja alcanzar después de huir
var _t_rodeo := 0.0
var _ang_rodeo := 0.0
var _jugador := Vector3(INF, 0, INF)
var _t_suelo := 0.0
var _y_suelo := NAN

## Arma el personaje con los bytes del GLB. false si no se pudo leer.
func armar(d: Dictionary, bytes: PackedByteArray) -> bool:
	datos = d
	id = d["id"]
	name = id
	var doc := GLTFDocument.new()
	var estado := GLTFState.new()
	if bytes.is_empty() or doc.append_from_buffer(bytes, "", estado) != OK:
		push_warning("personaje %s: no se pudo leer el modelo" % id)
		return false
	var escena := doc.generate_scene(estado)
	add_child(escena)
	anim = escena.find_children("*", "AnimationPlayer", true, false).front() if not escena.find_children("*", "AnimationPlayer", true, false).is_empty() else null
	for m in escena.find_children("*", "MeshInstance3D", true, false):
		(m as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		_ajustar_materiales(m as MeshInstance3D)
	if anim != null:
		for nombre in anim.get_animation_list():
			anim.get_animation(nombre).loop_mode = Animation.LOOP_LINEAR if nombre in CLIPS_ANDAR else Animation.LOOP_NONE
		anim.animation_finished.connect(_fin_clip)
	var esqueletos := escena.find_children("*", "Skeleton3D", true, false)
	if not esqueletos.is_empty():
		_montar_mirada(esqueletos.front())
	# en la mecánica (clips de una vez) no entran los de andar: esos van en "movimiento"
	_mecanica = (d.get("mecanica", ["reposo"]) as Array).filter(func(c): return anim != null and anim.has_animation(c) and not (c in CLIPS_ANDAR))
	_paso = randi() % maxi(1, _mecanica.size())
	_mov = d.get("movimiento", {})
	_clips_parada = randi_range(1, int(_mov.get("paradas", 2)))
	_siguiente()
	return true

func _clip(nombre: String, otro := "caminar") -> String:
	if anim != null and anim.has_animation(nombre):
		return nombre
	return otro if anim != null and anim.has_animation(otro) else ""

## Cerca de quién está el caminante (lo llama Encuentros en cada cuadro).
func caminante(p: Vector3) -> void:
	_jugador = p

## Material de los personajes: shaders/personaje.gdshader, con la misma luz que la ciudad (la escena no tiene luz
## ambiente: con el material estándar el lado en sombra quedaba negro, y los modelos de Tripo además venían como metal
## porque no traen metallicFactor). Sus texturas, que el GLB cargado en tiempo de ejecución trae sin mipmaps (granuladas a
## distancia), se rehacen con mipmaps.
const SHADER := preload("res://shaders/personaje.gdshader")
var _texturas := {}                        # textura original → con mipmaps (compartida entre sus materiales)
var _materiales := {}                      # material del GLB → el nuevo
func _ajustar_materiales(m: MeshInstance3D) -> void:
	if m.mesh == null:
		return
	for i in m.mesh.get_surface_count():
		var orig := m.get_active_material(i) as BaseMaterial3D
		if orig == null:
			continue
		if not _materiales.has(orig):
			var mat := ShaderMaterial.new()
			mat.shader = SHADER
			var tex := orig.get_texture(BaseMaterial3D.TEXTURE_ALBEDO)
			if tex != null:
				mat.set_shader_parameter("albedo", _con_mipmaps(tex))
			mat.set_shader_parameter("tinte", orig.albedo_color)
			var nor := orig.get_texture(BaseMaterial3D.TEXTURE_NORMAL)
			if orig.normal_enabled and nor != null:
				mat.set_shader_parameter("relieve", _con_mipmaps(nor))
				mat.set_shader_parameter("con_relieve", true)
				mat.set_shader_parameter("fuerza_relieve", minf(orig.normal_scale, 0.6))   # el relieve horneado de Tripo ensucia de cerca
			_materiales[orig] = mat
		m.set_surface_override_material(i, _materiales[orig])

func _con_mipmaps(t: Texture2D) -> Texture2D:
	if _texturas.has(t):
		return _texturas[t]
	var img := t.get_image()
	var r: Texture2D = t
	if img != null and not img.has_mipmaps():
		if img.is_compressed():
			img.decompress()
		img.generate_mipmaps()
		r = ImageTexture.create_from_image(img)
	_texturas[t] = r
	return r

## Pone los pies en p mirando hacia el punto 'mira_a' (x, z) de sus datos.
func colocar(p: Vector3) -> void:
	global_position = p
	var m: Array = datos["lugar"].get("mira_a", [p.x, p.z - 1.0])
	_rumbo_reposo = rumbo_hacia(Vector3(m[0], p.y, m[1]))
	_rumbo_objetivo = _rumbo_reposo
	rotation.y = _rumbo_reposo

func rumbo_hacia(q: Vector3) -> float:
	var d := q - global_position
	return atan2(d.x, d.z)

# ------------------------------------------------------------------------------------------------- mirada
func _montar_mirada(esq: Skeleton3D) -> void:
	var cabeza := ""
	for h in HUESOS_CABEZA:
		if esq.find_bone(h) >= 0:
			cabeza = h
			break
	if cabeza == "":
		return
	add_child(_objetivo)
	_mirar.bone_name = cabeza
	_mirar.forward_axis = SkeletonModifier3D.BONE_AXIS_PLUS_Z
	_mirar.use_angle_limitation = true
	_mirar.symmetry_limitation = true
	_mirar.primary_limit_angle = GIRO_CABEZA_MAX * 2.0
	_mirar.secondary_limit_angle = deg_to_rad(50.0)
	_mirar.duration = 0.35
	_mirar.influence = 0.0
	esq.add_child(_mirar)
	_mirar.target_node = _mirar.get_path_to(_objetivo)

## Que mire (con la cabeza) a un punto del mundo; null = vuelve a su mecánica.
func mirar(punto) -> void:
	if punto == null:
		_atencion_objetivo = 0.0
		return
	if not _objetivo.is_inside_tree():         # modelo sin hueso de cabeza: no gira la cabeza
		return
	_objetivo.global_position = punto
	_atencion_objetivo = 1.0

# ------------------------------------------------------------------------------------------------- encuentro
## Empieza a hablar con alguien que está en 'hacia': gira el cuerpo y pasa a 'hablar'.
func empezar_encuentro(hacia: Vector3) -> void:
	_hablando = true
	_estado = Estado.DETENIDO
	if anim != null:
		anim.speed_scale = 1.0
	_rumbo_objetivo = rumbo_hacia(hacia)
	gesto(datos.get("gesto_invita", ""))

func terminar_encuentro() -> void:
	_hablando = false
	_rumbo_objetivo = _rumbo_reposo
	_gesto_en_curso = false
	_estado = Estado.PARADA
	_clips_parada = 1
	_calma = 25.0                          # recién hablaron: no sale corriendo enseguida
	if anim != null and anim.has_animation("asentir"):
		_tocar("asentir")
	else:
		_siguiente()

## Un gesto puntual (clip de una vez); después vuelve a 'hablar' o a la mecánica.
func gesto(nombre: String) -> void:
	if anim == null or nombre == "" or not anim.has_animation(nombre) or nombre in datos.get("omitir_gestos", []):
		if _hablando and not _gesto_en_curso:
			_tocar("hablar" if anim != null and anim.has_animation("hablar") else "reposo")
		return
	_gesto_en_curso = true
	_tocar(nombre)

func _tocar(clip: String) -> void:
	if anim != null and anim.has_animation(clip):
		anim.play(clip, 0.3)

func _fin_clip(_nombre: StringName) -> void:
	_gesto_en_curso = false
	if _hablando:
		_tocar("hablar" if anim.has_animation("hablar") else "reposo")
		return
	if _estado == Estado.PARADA and _puede_andar():
		_clips_parada -= 1
		if _clips_parada <= 0:
			_andar_a_siguiente()
			return
	_siguiente()

func _siguiente() -> void:
	if _mecanica.is_empty():
		_tocar("reposo")
		return
	_paso = (_paso + 1) % _mecanica.size()
	_tocar(_mecanica[_paso])

func _puede_andar() -> bool:
	return ronda.size() >= 2 or guia != null

func _andar_a_siguiente() -> void:
	if guia != null:
		_estado = Estado.ACOMPANANDO
		return
	_i_ronda = (_i_ronda + 1 + randi() % maxi(1, ronda.size() - 1)) % ronda.size()
	_ir(ronda[_i_ronda], _clip(str(_mov.get("clip", "caminar"))), float(_mov.get("vel", 1.0)), Estado.ANDANDO)

func _ir(destino: Vector3, clip: String, vel: float, estado: int) -> void:
	_destino = destino
	_vel = vel
	_estado = estado
	_clip_andando = clip
	if clip != "":
		anim.play(clip, 0.25)
		# el paso del clip acompaña la velocidad (clips hechos para ~1,2 m/s al caminar, ~3 m/s al correr)
		var base := 3.0 if clip in ["huir", "trotar", "correr_falda", "galopar_palo", "caminar_rapido"] else 1.2
		anim.speed_scale = clampf(vel / base, 0.6, 1.6)

func _parar(clips: int) -> void:
	_estado = Estado.PARADA
	_clips_parada = clips
	if anim != null:
		anim.speed_scale = 1.0
	_siguiente()

func _mover(dt: float) -> void:
	var yo := global_position
	var al_jugador := Vector2(_jugador.x - yo.x, _jugador.z - yo.z).length()
	var modo: String = _mov.get("modo", "pasear")
	_calma = maxf(_calma - dt, 0.0)
	# reacciones al caminante
	if not _hablando and ronda.size() >= 2:
		if modo == "huir" and _estado != Estado.HUYENDO and _calma <= 0.0 \
				and al_jugador < float(_mov.get("distancia", 6.0)):
			if _huidas < int(_mov.get("huidas", 2)):
				_huidas += 1
				var lejos := ronda[0]
				for q in ronda:                   # el punto más alejado del caminante
					if Vector2(q.x - _jugador.x, q.z - _jugador.z).length() > Vector2(lejos.x - _jugador.x, lejos.z - _jugador.z).length():
						lejos = q
				_ir(lejos, _clip(str(_mov.get("clip_huir", "huir")), "caminar_rapido"), float(_mov.get("vel_huir", 3.2)), Estado.HUYENDO)
				return
			_huidas = 0                           # cansado: se deja alcanzar un rato
			_calma = 40.0
		if modo == "apartarse" and _estado == Estado.ANDANDO and _calma <= 0.0 and al_jugador < 2.8:
			var lado := Vector3(_jugador.z - yo.z, 0, -(_jugador.x - yo.x)).normalized() * 1.6
			_calma = 12.0
			_ir(yo + lado, _clip(str(_mov.get("clip_huir", "apartarse")), "caminar_rapido"), 1.8, Estado.HUYENDO)
			return
		if modo == "rondar" and _estado != Estado.RODEANDO and _calma <= 0.0 and al_jugador < 5.0:
			_estado = Estado.RODEANDO
			_t_rodeo = 7.0
			_ang_rodeo = atan2(yo.x - _jugador.x, yo.z - _jugador.z)
			_ir(yo, _clip("rodear_jugador", "trotar"), 2.0, Estado.RODEANDO)
		if modo != "huir" or _calma > 0.0:
			if _estado == Estado.ANDANDO and al_jugador < DETENERSE:
				_estado = Estado.DETENIDO
				anim.speed_scale = 1.0
				_tocar("reposo")
				_rumbo_objetivo = rumbo_hacia(_jugador)
			elif _estado == Estado.DETENIDO and al_jugador > REANUDAR:
				_parar(1)
	match _estado:
		Estado.ANDANDO, Estado.HUYENDO:
			_avanzar(dt)
		Estado.RODEANDO:
			_t_rodeo -= dt
			_ang_rodeo += dt * 0.7
			_destino = _jugador + Vector3(sin(_ang_rodeo), 0, cos(_ang_rodeo)) * 2.6
			if _t_rodeo <= 0.0 or al_jugador > 9.0:
				_calma = 20.0
				_parar(2)
			else:
				_avanzar(dt, false)
		Estado.ACOMPANANDO:
			if not is_instance_valid(guia):
				guia = null
				_parar(1)
				return
			var detras := guia.global_position - guia.global_basis.z * 1.3 + guia.global_basis.x * 0.9
			var lejos := Vector2(detras.x - yo.x, detras.z - yo.z).length()
			if lejos > 0.5:
				if _clip_andando == "" or not anim.is_playing() or anim.current_animation != _clip_andando:
					_ir(detras, _clip(str(_mov.get("clip", "caminar"))), 1.0, Estado.ACOMPANANDO)
				_destino = detras
				_vel = clampf(lejos * 1.2, 0.4, 2.5)
				_avanzar(dt, false)
			elif anim.current_animation == _clip_andando:
				_clip_andando = ""
				anim.speed_scale = 1.0
				_siguiente()
				_rumbo_objetivo = guia.rotation.y

## Un paso hacia _destino; al llegar, para (o sigue si 'terminar' es false).
func _avanzar(dt: float, terminar := true) -> void:
	var yo := global_position
	var d := Vector3(_destino.x - yo.x, 0, _destino.z - yo.z)
	var largo := d.length()
	if largo < 0.15:
		if terminar:
			if _estado == Estado.HUYENDO and _mov.get("modo", "") == "huir":
				_parar(1)
				gesto(str(_mov.get("al_llegar", "asomarse")))   # se esconde y se asoma
				_gesto_en_curso = false
			else:
				_parar(randi_range(1, int(_mov.get("paradas", 2))))
		return
	var paso := minf(_vel * dt, largo)
	var nuevo := yo + d / largo * paso
	_t_suelo -= dt
	if _t_suelo <= 0.0 or is_nan(_y_suelo):
		_t_suelo = 0.15
		var est := get_world_3d().direct_space_state
		var h := est.intersect_ray(PhysicsRayQueryParameters3D.create(nuevo + Vector3.UP * 2.0, nuevo + Vector3.DOWN * 3.0, 1))
		if not h.is_empty():
			_y_suelo = h["position"].y
	if not is_nan(_y_suelo):
		nuevo.y = lerpf(yo.y, _y_suelo, 1.0 - exp(-12.0 * dt))
	global_position = nuevo
	_rumbo_objetivo = atan2(d.x, d.z)

func _process(dt: float) -> void:
	if (_puede_andar() or _mov.get("modo", "") == "rondar") and anim != null and not _hablando:
		_mover(dt)
	rotation.y = lerp_angle(rotation.y, _rumbo_objetivo, 1.0 - exp(-VEL_GIRO * dt))
	_atencion = move_toward(_atencion, _atencion_objetivo, dt * 2.0)
	_mirar.influence = smoothstep(0.0, 1.0, _atencion)
