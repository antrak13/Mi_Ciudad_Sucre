class_name TourProcesion
extends Node3D
## La procesión de la Virgen de Guadalupe (La Plata, enero de 1602; Ocaña, fols. 232v–234v) para el tour: la Virgen en
## sus andas sobre los hombros de cuatro cargadores, el obispo Ramírez de Vergara incensando, fray Diego de Ocaña
## adelante y vecinos con cirios, todos al paso de la marcha (0,56 m/s) por la calle frente al atrio de la Catedral, con
## fieles que esperan a los lados. Formación: datos "procesion" del guion (la del visor de antigravity).
##
## Cada modelo se baja y se arma una sola vez (con el material de los personajes, que toma la luz de la ciudad: no se
## ven apagados) y los que se repiten son copias que comparten mallas, materiales y texturas.
## Este nodo es el centro de las andas, con su frente (+z) hacia donde marcha: la cámara del tour lo puede seguir.

var _d: Dictionary
var _plantillas := {}                    # figurante → Personaje armado (fuera del árbol)
var _miembros := []                      # [{nodo, anim, pos}] en la formación
var _fieles := []
var _virgen: Node3D
var _desde := Vector3.ZERO
var _hasta := Vector3.ZERO
var _rumbo := 0.0
var _avance := 0.0
var _largo := 1.0
var _marchando := false
var _t := 0.0
var _t_suelo := 0.0

## Baja y arma los modelos (await). Queda invisible hasta empezar().
func armar(d: Dictionary, figurantes: Dictionary) -> void:
	_d = d
	var usados := {"virgen": true}
	for m in d.get("integrantes", []) + d.get("fieles", []):
		usados[m["f"]] = true
	for f in usados:
		if not figurantes.has(f):
			continue
		var info: Dictionary = figurantes[f]
		var b: PackedByteArray = await Datos.bytes(info["archivo"], str(info.get("v", "")))
		if not is_instance_valid(self):
			return
		var p := Personaje.new()
		p.visible = false
		add_child(p)
		p.set_process(false)
		if p.armar({"id": f, "mecanica": []}, b):
			_plantillas[f] = p
		else:
			p.queue_free()
	var a: Array = d["desde"]
	var z: Array = d["hasta"]
	_desde = Vector3(a[0], 0, a[1])
	_hasta = Vector3(z[0], 0, z[1])
	_largo = maxf(_desde.distance_to(_hasta), 0.1)
	_rumbo = atan2(_hasta.x - _desde.x, _hasta.z - _desde.z)
	if _plantillas.has("virgen"):
		_virgen = _copia("virgen")
		add_child(_virgen)
	for m in d.get("integrantes", []):
		var n := _figura(m)
		if n != null:
			add_child(n["nodo"])
			n["pos"] = Vector3(m["pos"][0], 0, m["pos"][1])
			_miembros.append(n)
	for m in d.get("fieles", []):
		var n := _figura(m)
		if n == null:
			continue
		var en := Vector3(m["en"][0], 0, m["en"][1])
		var mira := Vector3(m["mira"][0], 0, m["mira"][1])
		var nodo: Node3D = n["nodo"]
		get_parent().add_child.call_deferred(nodo)     # los fieles quedan quietos en su lugar (no siguen a las andas)
		n["en"] = en
		n["rumbo"] = atan2(mira.x - en.x, mira.z - en.z)
		_fieles.append(n)
	for p in _plantillas.values():
		p.queue_free()
	_plantillas.clear()

func _exit_tree() -> void:
	for f in _fieles:
		if is_instance_valid(f["nodo"]):
			f["nodo"].queue_free()

## Copia de la escena del modelo (comparte recursos con la plantilla) sin el giro de cabeza de los encuentros.
func _copia(f: String) -> Node3D:
	var esc: Node3D = (_plantillas[f] as Node).get_child(0).duplicate()
	for m in esc.find_children("*", "LookAtModifier3D", true, false):
		m.queue_free()
	for m in esc.find_children("*", "Marker3D", true, false):
		m.queue_free()
	return esc

func _figura(m: Dictionary) -> Dictionary:
	if not _plantillas.has(m["f"]):
		return {}
	var nodo := Node3D.new()
	var esc := _copia(m["f"])
	nodo.add_child(esc)
	var anim: AnimationPlayer = null
	var lista := esc.find_children("*", "AnimationPlayer", true, false)
	if not lista.is_empty():
		anim = lista.front()
		for c in [m.get("clip", "reposo"), m.get("alterna", "")]:
			if c != "" and anim.has_animation(c):
				anim.get_animation(c).loop_mode = Animation.LOOP_LINEAR
		var clip: String = m.get("clip", "reposo")
		if not anim.has_animation(clip):
			clip = "reposo" if anim.has_animation("reposo") else ""
		if clip != "":
			anim.play(clip)
			anim.seek(float(m.get("desfase", 0.0)) * anim.get_animation(clip).length, true)
			if clip == "caminar":            # paso de procesión: el clip está hecho para ~1,2 m/s
				anim.speed_scale = float(_d.get("velocidad", 0.56)) / 1.2 * 1.25
	if m.has("cirio"):
		var c: Array = m["cirio"]
		nodo.add_child(_cirio(Vector3(c[0], c[1], c[2])))
	return {"nodo": nodo, "anim": anim, "clip": m.get("clip", ""), "alterna": m.get("alterna", ""), "y": NAN}

func _cirio(p: Vector3) -> Node3D:
	var g := Node3D.new()
	g.position = p
	var cera := MeshInstance3D.new()
	var cil := CylinderMesh.new()
	cil.top_radius = 0.016
	cil.bottom_radius = 0.018
	cil.height = 0.34
	cil.radial_segments = 8
	var m := StandardMaterial3D.new()
	m.albedo_color = Color("#efe4c8")
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	cil.material = m
	cera.mesh = cil
	cera.position.y = 0.08
	g.add_child(cera)
	var llama := MeshInstance3D.new()
	var esfera := SphereMesh.new()
	esfera.radius = 0.016
	esfera.height = 0.05
	esfera.radial_segments = 6
	esfera.rings = 3
	var ml := StandardMaterial3D.new()
	ml.albedo_color = Color(1.0, 0.78, 0.35)
	ml.emission_enabled = true
	ml.emission = Color(1.0, 0.7, 0.3)
	ml.emission_energy_multiplier = 3.0
	ml.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	esfera.material = ml
	llama.mesh = esfera
	llama.position.y = 0.27
	llama.name = "llama"
	g.add_child(llama)
	return g

## Arranca la marcha desde el principio del recorrido.
func empezar() -> void:
	_avance = 0.0
	_marchando = true
	_t_suelo = 0.0
	for f in _fieles:
		var nodo: Node3D = f["nodo"]
		nodo.global_position = f["en"] + Vector3.UP * _suelo(f["en"], 70.0)
		nodo.rotation.y = f["rumbo"]
	_colocar(0.0)

func _suelo(p: Vector3, y_previa: float) -> float:
	var est := get_world_3d().direct_space_state
	var h := est.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(p.x, 140.0, p.z), Vector3(p.x, -50.0, p.z), 1))
	return h["position"].y if not h.is_empty() else y_previa

func _colocar(dt: float) -> void:
	var centro := _desde.lerp(_hasta, clampf(_avance / _largo, 0.0, 1.0))
	var base := Basis(Vector3.UP, _rumbo)
	_t_suelo -= dt
	var medir := _t_suelo <= 0.0
	if medir:
		_t_suelo = 0.2
	var y_centro := global_position.y if _avance > 0.0 else 60.0
	if medir:
		y_centro = _suelo(centro, y_centro)
	global_transform = Transform3D(base, Vector3(centro.x, y_centro, centro.z))
	for m in _miembros:
		var nodo: Node3D = m["nodo"]
		var p: Vector3 = global_transform * (m["pos"] as Vector3)
		if medir or is_nan(m["y"]):
			m["y"] = _suelo(p, y_centro)
		nodo.global_position = Vector3(p.x, m["y"], p.z)
		nodo.rotation.y = _rumbo
	if _virgen != null:
		# mecido de las andas con el doble paso de la marcha (1,333 s), como en el visor
		var fase := _t / 1.3333 * TAU
		var alto := float(_d.get("altura_andas", 1.345))
		_virgen.position = Vector3(0, alto + (0.009 * sin(fase * 2.0) if _marchando else 0.0), 0)
		_virgen.rotation.z = 0.008 * sin(fase) if _marchando else 0.0

func _process(dt: float) -> void:
	if not visible:
		return
	_t += dt
	if _marchando:
		_avance += float(_d.get("velocidad", 0.56)) * dt
		if _avance >= _largo:
			_avance = _largo
			_marchando = false
			_alto()
	_colocar(dt)
	# las llamas titilan
	for m in _miembros + _fieles:
		var ll: Node = (m["nodo"] as Node3D).find_child("llama", true, false)
		if ll != null:
			(ll as Node3D).scale = Vector3.ONE * (1.0 + 0.18 * sin(_t * 23.0 + m["nodo"].get_instance_id() % 7))

## Llegan: alto, los acompañantes rezan y los cargadores se quedan firmes.
func _alto() -> void:
	for m in _miembros:
		var a: AnimationPlayer = m["anim"]
		if a == null:
			continue
		var c: String = m["clip"]
		a.speed_scale = 1.0
		if c.begins_with("cargar_andas"):
			a.seek(0.0, true)
			a.pause()
		elif a.has_animation("rezar_acompanar") and c != "llevar_vela":
			a.play("rezar_acompanar", 0.5)
