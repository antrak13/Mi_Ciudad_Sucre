class_name Tour
extends Node
## Tour guiado del centro histórico (guion: tour/guion.json → datos/tour.json, ver herramientas/tour.py).
##
## Es un documental dentro de la ciudad: la cámara recorre cada parada con movimientos continuos (curvas suaves a
## velocidad pareja, con un leve pulso de cámara en mano), vuela de una parada a otra mientras aparece su título, y el
## cronista narra en la carta de los encuentros (una frase por vez, al ritmo de su voz). Las láminas de archivo
## (fotografías de 1925, grabados, retratos) acompañan cada frase y algunas se disuelven en la vista actual del mismo
## lugar. Escenas: la procesión de la Virgen de Guadalupe (1602) y el eco de la campana de San Francisco (1809).
##
## Sin botones: Esc (o «atrás» en el celular) sale; Espacio, Intro o un toque en la carta adelantan la frase; ← → pasan
## a la toma anterior o siguiente; arrastrar mira alrededor (al soltar, la cámara vuelve sola a su encuadre).

signal _evento(que: String)             # "siguiente" (frase), "toma+", "toma-", "salir"

const VEL_VUELO := 38.0                  # m/s de crucero entre paradas
const MIN_RUTA := 6.0                    # s mínimos de una ruta de cámara
const PAUSA_FRASE := 0.6                 # = Carta.PAUSA_TRAS_VOZ
const RADIO_CARGA := 140.0
const ESPERA_CARGA_MAX := 9.0

var principal: Node
var ciudad: Ciudad
var jugador: Jugador
var interfaz: Interfaz
var puente: Puente
var trafico: Trafico
var encuentros: Encuentros

var activo := false
var foco := Vector3.ZERO                 # la ciudad carga alrededor de este punto mientras dura el tour

var _datos: Dictionary = {}
var _camara: Camera3D
var _carta: Carta
var _laminas: TourLaminas
var _efectos: TourEfectos
var _escenas := {}                       # nombre → nodo de la escena (procesión, eco)
var _procesion_lista := false
var _hora_previa := "dia"
var _saliendo := false
var _pedido_salir := false
var _t := 0.0

# movimiento de cámara en curso: tipo "ruta" (claves recorridas en 'dur' s) o "quieta"
var _mov := {}
var _pose := {"ojos": Vector3.ZERO, "mira": Vector3.FORWARD, "fov": 60.0}
var _mirar_off := Vector2.ZERO          # mirar alrededor con el ratón o el dedo (rad)
var _arrastrando := false
var _t_suelto := 0.0

# ------------------------------------------------------------------------------------------------- entrar / salir
func iniciar() -> void:
	if activo:
		return
	activo = true
	_saliendo = false
	_pedido_salir = false
	if _datos.is_empty():
		var d = await Datos.json("tour.json")
		if not (d is Dictionary):
			push_warning("tour: no se pudo leer tour.json")
			activo = false
			return
		_datos = d
	_hora_previa = Hora.actual
	jugador.activo = false
	jugador.velocity = Vector3.ZERO
	jugador.entrada = Vector2.ZERO
	interfaz.hud_visible(false)
	puente.emitir({"tipo": "tour", "activo": true})
	trafico.visible = false
	trafico.process_mode = Node.PROCESS_MODE_DISABLED
	_personajes_visibles(false)
	Hora.niebla_a_pie(false)
	_camara = Camera3D.new()
	_camara.near = 0.15
	_camara.far = 6000.0
	add_child(_camara)
	var actual := get_viewport().get_camera_3d()
	_camara.global_transform = actual.global_transform
	_camara.fov = actual.fov
	_pose = {"ojos": actual.global_position, "mira": actual.global_position - actual.global_basis.z * 30.0, "fov": actual.fov}
	_mov = {}
	_camara.make_current()
	foco = actual.global_position
	_carta = Carta.new()
	_carta.name = "CartaTour"
	add_child(_carta)
	_carta.siguiente.connect(func(): _evento.emit("siguiente"))
	_carta.elegido.connect(func(_i): _pedir("salir"))
	_laminas = TourLaminas.new()
	_laminas.name = "Laminas"
	add_child(_laminas)
	_efectos = TourEfectos.new()
	_efectos.name = "Efectos"
	add_child(_efectos)
	_laminas.barras(true)
	_precargar_procesion()
	_recorrido()

func salir() -> void:
	if activo and not _saliendo:
		_pedir("salir")

func _pedir(que: String) -> void:
	if que == "salir":
		_pedido_salir = true
	_evento.emit(que)

func _terminar() -> void:
	_saliendo = true
	_carta.voz.callar()
	_efectos.callar()
	if _carta.abierta:
		_carta.cerrar()
	_laminas.ocultar_todo()
	await _laminas.negro(true, 0.7)
	for e in _escenas.values():
		e.queue_free()
	_escenas.clear()
	if Hora.actual != _hora_previa:
		principal._aplicar_hora(_hora_previa, false)
	Hora.niebla_a_pie(true)
	trafico.visible = true
	trafico.process_mode = Node.PROCESS_MODE_INHERIT
	_personajes_visibles(true)
	principal.tour_terminado()             # de vuelta a pie, frente al monumento de la plaza
	var espera := 0.0
	while principal._pendiente != null and espera < 20.0:
		await get_tree().process_frame
		espera += get_process_delta_time()
	jugador.camara.make_current()
	_camara.queue_free()
	_carta.queue_free()
	_efectos.queue_free()
	activo = false
	interfaz.hud_visible(true)
	puente.emitir({"tipo": "tour", "activo": false})
	await _laminas.negro(false, 0.8)
	_laminas.queue_free()

func _personajes_visibles(v: bool) -> void:
	if encuentros == null:
		return
	for c in encuentros.get_children():
		if c is Personaje:
			(c as Personaje).visible = v

# ------------------------------------------------------------------------------------------------- recorrido
func _recorrido() -> void:
	var paradas: Array = _datos["paradas"]
	var tomas := []                       # lista plana [[parada, toma]] para poder ir y volver con las flechas
	for i in paradas.size():
		for j in (paradas[i]["tomas"] as Array).size():
			tomas.append([i, j])
	var k := int(OS.get_environment("SUCRE_TOUR_DESDE")) if OS.get_environment("SUCRE_TOUR_DESDE") != "" else 0
	k = clampi(k, 0, tomas.size() - 1)
	var parada_previa := -1
	var primera := true
	while k < tomas.size():
		var i: int = tomas[k][0]
		var parada: Dictionary = paradas[i]
		var toma: Dictionary = parada["tomas"][tomas[k][1]]
		var nueva_parada := i != parada_previa
		parada_previa = i
		var transicion: String = toma.get("transicion", "deslizar")
		if primera:
			transicion = "vuelo"
		elif nueva_parada and transicion == "deslizar" and _lejos(toma):
			transicion = "vuelo"
		if nueva_parada:
			_laminas_de_parada(parada)
		var r := await _hacer_toma(parada, toma, transicion, nueva_parada, i, paradas.size())
		primera = false
		if r == "salir" or _pedido_salir:
			break
		if r == "toma-":
			k = maxi(k - 1, 0)
			parada_previa = -1
			primera = true            # se llega volando
			continue
		k += 1
	if _carta.abierta and not _saliendo:
		await _carta.cerrar()
	_terminar()

func _lejos(toma: Dictionary) -> bool:
	var claves: Array = toma["camara"]
	return _vec(claves[0]["ojos"]).distance_to(_pose["ojos"]) > 120.0

## Una toma: transición, escena, y sus frases con la cámara en movimiento. Devuelve "fin", "toma+", "toma-" o "salir".
func _hacer_toma(parada: Dictionary, toma: Dictionary, transicion: String, nueva: bool, n: int, total: int) -> String:
	var claves := _claves(toma["camara"])
	var pasos: Array = toma["pasos"]
	_carta.voz.precargar(pasos.slice(0, 2))
	var hora: String = parada.get("hora", "dia")
	match transicion:
		"vuelo":
			if nueva:
				_laminas.titulo(n + 1, total, parada["titulo"], parada.get("lema", ""))
			await _volar(claves[0], hora)
		"corte":
			await _laminas.negro(true, 0.45)
			_poner_pose(claves[0])
			if Hora.actual != hora:
				principal._aplicar_hora(hora, false)
			await _esperar_carga(claves[0]["ojos"])
			_laminas.negro(false, 0.7)
		_:
			claves.push_front(_pose.duplicate())
	if _pedido_salir:
		return "salir"
	# escena (se arma antes de que la cámara la busque)
	var escena: String = toma.get("escena", "")
	if escena != "":
		await _montar_escena(escena)
	var seguir: Node3D = _escenas.get("procesion") if toma.has("camara_seguir") and _escenas.has("procesion") else null
	var dur := 0.0
	for p in pasos:
		dur += _estimar(p)
	if seguir != null:
		_mov = {"tipo": "seguir", "claves": _claves(toma["camara_seguir"]), "desde": _pose.duplicate(), "t0": _t,
			"dur": dur, "nodo": seguir}
	else:
		_mov = _ruta(claves, dur)
	if not _carta.abierta:
		_carta.abrir()
	var resultado := "fin"
	var idx := 0
	while idx < pasos.size():
		var p: Dictionary = pasos[idx]
		if idx + 1 < pasos.size():
			_carta.voz.precargar([pasos[idx + 1]])
		_mostrar_paso(p)
		var quien := {"nombre": "El cronista", "retrato": null}
		if p.get("quien", "cronista") != "cronista":
			quien = {"nombre": p.get("nombre", ""), "retrato": _retrato(p.get("retrato", ""))}
		_carta.decir(quien, p["texto"], p)
		var r: String = await _evento
		if _pedido_salir:
			r = "salir"
		if r == "siguiente":
			idx += 1
			continue
		resultado = r
		break
	_laminas.ocultar_lado()
	_carta.voz.callar()
	return resultado

func _mostrar_paso(p: Dictionary) -> void:
	if p.has("fundido"):
		_laminas.fundido(_info_lamina(p["fundido"]))
	if p.has("lamina"):
		_laminas.lado(_info_lamina(p["lamina"]))
	else:
		_laminas.ocultar_lado()
	if p.has("sonido"):
		var s: Dictionary = _datos.get("sonidos", {}).get(p["sonido"], {})
		if not s.is_empty():
			_efectos.tocar(s)
	if _escenas.has("eco_campana") and p.get("voz", "").contains("mariana_zudanez/06"):
		_escenas["eco_campana"].repicar()

func _info_lamina(id: String) -> Dictionary:
	var d: Dictionary = _datos["laminas"].get(id, {})
	d["id"] = id
	return d

func _laminas_de_parada(parada: Dictionary) -> void:
	for t in parada["tomas"]:
		for p in t["pasos"]:
			for clave in ["lamina", "fundido"]:
				if p.has(clave):
					_laminas.precargar(_info_lamina(p[clave]))

## Duración estimada de una frase (con voz: su audio y la pausa; sin voz: escritura y lectura de la carta).
func _estimar(p: Dictionary) -> float:
	var n := float(str(p["texto"]).length())
	if p.has("voz"):
		return float(p.get("dur", n * 0.065)) + PAUSA_FRASE + 0.15
	return n * Carta.MS_LETRA * 1.25 + Carta.LECTURA_BASE + n * Carta.LECTURA_LETRA

var _retratos := {}
func _retrato(archivo: String) -> Texture2D:
	if archivo == "":
		return null
	if not _retratos.has(archivo):
		_retratos[archivo] = load("res://personajes/retratos/" + archivo)
	return _retratos[archivo]

# ------------------------------------------------------------------------------------------------- escenas
func _precargar_procesion() -> void:
	var d: Dictionary = _datos.get("procesion", {})
	if d.is_empty():
		return
	var p := TourProcesion.new()
	p.name = "Procesion"
	p.visible = false
	add_child(p)
	_escenas["procesion_cargando"] = p
	await p.armar(d, _datos.get("figurantes", {}))
	if not is_instance_valid(p):
		return
	_escenas.erase("procesion_cargando")
	_escenas["procesion_lista"] = p

func _montar_escena(nombre: String) -> void:
	match nombre:
		"procesion":
			var espera := 0.0
			while not _escenas.has("procesion_lista") and _escenas.has("procesion_cargando") and espera < 12.0:
				await get_tree().process_frame
				espera += get_process_delta_time()
			if _escenas.has("procesion_lista"):
				var p: TourProcesion = _escenas["procesion_lista"]
				_escenas.erase("procesion_lista")
				_escenas["procesion"] = p
				p.visible = true
				p.empezar()
		"eco_campana":
			var e := TourEco.new()
			e.name = "EcoCampana"
			add_child(e)
			_escenas["eco_campana"] = e

# ------------------------------------------------------------------------------------------------- cámara
func _vec(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))

func _claves(lista: Array) -> Array:
	var r := []
	for c in lista:
		r.append({"ojos": _vec(c["ojos"]), "mira": _vec(c["mira"]), "fov": float(c.get("fov", 52.0))})
	return r

func _poner_pose(c: Dictionary) -> void:
	_pose = c.duplicate()
	_mov = {}

## Una ruta por las claves a velocidad pareja (el tiempo de cada tramo, según su largo), con arranque y frenado suaves.
func _ruta(claves: Array, dur: float) -> Dictionary:
	var largos := [0.0]
	for i in range(1, claves.size()):
		var a: Dictionary = claves[i - 1]
		var b: Dictionary = claves[i]
		var l: float = a["ojos"].distance_to(b["ojos"]) + 0.35 * a["mira"].distance_to(b["mira"]) + 0.2
		largos.append(largos[-1] + l)
	var total: float = largos[-1]
	dur = maxf(dur, MIN_RUTA)              # ni brusca si la toma es corta
	return {"tipo": "ruta", "claves": claves, "acum": largos, "total": maxf(total, 0.001), "t0": _t, "dur": maxf(dur, 1.0)}

static func _cr(p0, p1, p2, p3, t: float):
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)

static func _suave(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)      # smootherstep

## Perfil de velocidad: arranca y frena en 'rampa' segundos y en el medio va pareja (en tomas largas la curva suave
## dejaría la cámara casi quieta al principio y al final).
static func _perfil(t: float, dur: float) -> float:
	var r := minf(4.0, dur / 3.0)
	t = clampf(t, 0.0, dur)
	var v := 1.0 / (dur - r)
	if t < r:
		return 0.5 * v * t * t / r
	if t > dur - r:
		return 1.0 - 0.5 * v * (dur - t) * (dur - t) / r
	return v * (t - r * 0.5)

func _en_ruta(m: Dictionary, u: float) -> Dictionary:
	var c: Array = m["claves"]
	if c.size() == 1:
		return c[0]
	var s: float = (_perfil(u * float(m.get("dur", 1.0)), float(m.get("dur", 1.0))) if m.has("dur") else _suave(u)) * m["total"]
	var acum: Array = m["acum"]
	var i := 1
	while i < acum.size() - 1 and acum[i] < s:
		i += 1
	var tramo: float = maxf(acum[i] - acum[i - 1], 0.0001)
	var f := clampf((s - acum[i - 1]) / tramo, 0.0, 1.0)
	var a: Dictionary = c[maxi(i - 2, 0)]
	var b: Dictionary = c[i - 1]
	var cc: Dictionary = c[i]
	var d: Dictionary = c[mini(i + 1, c.size() - 1)]
	return {"ojos": _cr(a["ojos"], b["ojos"], cc["ojos"], d["ojos"], f), "mira": _cr(a["mira"], b["mira"], cc["mira"], d["mira"], f),
		"fov": lerpf(b["fov"], cc["fov"], f * f * (3.0 - 2.0 * f))}

## Vuelo a otra parada: espera que cargue el destino, sube, planea y baja (curva de Bézier), mirando hacia adelante.
func _volar(destino: Dictionary, hora: String) -> void:
	var a: Dictionary = _pose.duplicate()
	var b: Dictionary = destino
	foco = b["ojos"]
	var espera := 0.0
	while ciudad.progreso_alrededor(b["ojos"], RADIO_CARGA) < 0.95 and espera < ESPERA_CARGA_MAX and not _pedido_salir:
		await get_tree().process_frame
		espera += get_process_delta_time()
	if Hora.actual != hora:
		await _laminas.negro(true, 0.35)
		principal._aplicar_hora(hora, false)
		_laminas.negro(false, 0.8)
	var pa: Vector3 = a["ojos"]
	var pb: Vector3 = b["ojos"]
	var dist := pa.distance_to(pb)
	var alto := maxf(pa.y, pb.y) + clampf(dist * 0.15, 8.0, 60.0)
	var c1 := pa.lerp(pb, 0.06)          # primero sube casi en vertical: no atraviesa los árboles de la calle
	c1.y = alto
	var c2 := pa.lerp(pb, 0.78)
	c2.y = alto
	var dur := clampf(dist / VEL_VUELO + 2.0, 4.0, 11.0)
	_mov = {"tipo": "vuelo", "p": [pa, c1, c2, pb], "a": a, "b": b, "t0": _t, "dur": dur}
	while _t - float(_mov.get("t0", 0.0)) < dur and not _pedido_salir and _mov.get("tipo", "") == "vuelo":
		await get_tree().process_frame
	_poner_pose(b)

func _en_vuelo(m: Dictionary, u: float) -> Dictionary:
	var e := _suave(u)
	var p: Array = m["p"]
	var q := 1.0 - e
	var ojos: Vector3 = q * q * q * p[0] + 3.0 * q * q * e * p[1] + 3.0 * q * e * e * p[2] + e * e * e * p[3]
	# la mirada: del encuadre de salida, hacia adelante en el aire, al encuadre de llegada
	var a: Dictionary = m["a"]
	var b: Dictionary = m["b"]
	var adelante: Vector3 = ojos + (p[3] - p[0]).normalized() * 60.0 + Vector3.DOWN * 30.0
	var mira: Vector3
	if e < 0.5:
		mira = (a["mira"] as Vector3).lerp(adelante, _suave(e * 2.0))
	else:
		mira = adelante.lerp(b["mira"], _suave((e - 0.5) * 2.0))
	return {"ojos": ojos, "mira": mira, "fov": lerpf(a["fov"], b["fov"], e)}

func _esperar_carga(p: Vector3) -> void:
	foco = p
	var espera := 0.0
	while ciudad.progreso_alrededor(p, RADIO_CARGA) < 0.95 and espera < ESPERA_CARGA_MAX:
		await get_tree().process_frame
		espera += get_process_delta_time()

func _process(dt: float) -> void:
	if not activo or _camara == null:
		return
	_t += dt
	match _mov.get("tipo", ""):
		"ruta":
			_pose = _en_ruta(_mov, (_t - float(_mov["t0"])) / float(_mov["dur"]))
		"vuelo":
			_pose = _en_vuelo(_mov, (_t - float(_mov["t0"])) / float(_mov["dur"]))
		"seguir":
			var n: Node3D = _mov["nodo"]
			if is_instance_valid(n):
				var ruta := {"claves": _mov["claves"]}
				var acum := [0.0]
				for i in range(1, (_mov["claves"] as Array).size()):
					acum.append(float(i))
				ruta["acum"] = acum
				ruta["total"] = maxf(acum[-1], 0.001)
				var local := _en_ruta(ruta, (_t - float(_mov["t0"])) / float(_mov["dur"]))
				var x := n.global_transform
				var objetivo := {"ojos": x * (local["ojos"] as Vector3), "mira": x * (local["mira"] as Vector3), "fov": local["fov"]}
				# al empezar, llega desde la pose anterior en 3 s
				var f := _suave((_t - float(_mov["t0"])) / 3.0)
				var de: Dictionary = _mov["desde"]
				_pose = {"ojos": (de["ojos"] as Vector3).lerp(objetivo["ojos"], f), "mira": (de["mira"] as Vector3).lerp(objetivo["mira"], f),
					"fov": lerpf(de["fov"], objetivo["fov"], f)}
	if _mov.get("tipo", "") != "vuelo":
		foco = _pose["ojos"]
	# pulso de cámara en mano: más notorio cerca del suelo, casi nada en el aire
	var bajo := clampf(1.0 - (float(_pose["ojos"].y) - 62.0) / 40.0, 0.15, 1.0)
	var pulso := Vector3(sin(_t * 0.37) + 0.5 * sin(_t * 0.91 + 1.3), 0.6 * sin(_t * 0.53 + 0.7), cos(_t * 0.29) * 0.7) * 0.05 * bajo
	var ojos: Vector3 = _pose["ojos"] + pulso
	var mira: Vector3 = _pose["mira"] + pulso * 0.4
	if ojos.distance_squared_to(mira) < 0.0001:
		mira = ojos + Vector3.FORWARD
	var arriba := Vector3.UP if absf((mira - ojos).normalized().y) < 0.995 else Vector3.FORWARD
	_camara.look_at_from_position(ojos, mira, arriba)
	# mirar alrededor (vuelve solo al encuadre)
	if not _arrastrando:
		_t_suelto += dt
		if _t_suelto > 0.8:
			_mirar_off = _mirar_off.lerp(Vector2.ZERO, 1.0 - exp(-2.2 * dt))
	_camara.rotate_object_local(Vector3.UP, _mirar_off.x)
	_camara.rotate_object_local(Vector3.RIGHT, _mirar_off.y)
	_camara.rotate_object_local(Vector3.FORWARD, sin(_t * 0.21) * 0.0035 * bajo)
	_camara.fov = float(_pose["fov"])
	_pruebas()

# ------------------------------------------------------------------------------------------------- entrada
func _unhandled_input(ev: InputEvent) -> void:
	if not activo or _saliendo:
		return
	if ev is InputEventKey and ev.pressed and not ev.echo:
		match ev.physical_keycode:
			KEY_ESCAPE:
				_pedir("salir")
			KEY_RIGHT:
				_pedir("toma+")
			KEY_LEFT:
				_pedir("toma-")
			KEY_SPACE, KEY_ENTER, KEY_KP_ENTER, KEY_I:
				if not _carta.abierta:
					return
			_:
				return
		get_viewport().set_input_as_handled()
	elif ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT:
		_arrastrando = ev.pressed
		_t_suelto = 0.0
	elif ev is InputEventScreenTouch:
		_arrastrando = ev.pressed
		_t_suelto = 0.0
	elif (ev is InputEventMouseMotion and _arrastrando) or ev is InputEventScreenDrag:
		var r: Vector2 = ev.relative
		_mirar_off.x = clampf(_mirar_off.x - r.x * 0.004, -1.2, 1.2)
		_mirar_off.y = clampf(_mirar_off.y - r.y * 0.004, -0.5, 0.5)

func _notification(que: int) -> void:
	if que == NOTIFICATION_WM_GO_BACK_REQUEST and activo:
		_pedir("salir")

# ------------------------------------------------------------------------------------------------- pruebas
## SUCRE_TOUR_CAPTURAS=carpeta: guarda una imagen cada SUCRE_TOUR_CADA s (por defecto 3) para revisar las tomas.
var _t_captura := 0.0
var _n_captura := 0
func _pruebas() -> void:
	var dir := OS.get_environment("SUCRE_TOUR_CAPTURAS")
	if dir == "" or _t < _t_captura:
		return
	var cada := float(OS.get_environment("SUCRE_TOUR_CADA")) if OS.get_environment("SUCRE_TOUR_CADA") != "" else 3.0
	_t_captura = _t + cada
	_n_captura += 1
	var n := _n_captura
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_jpg("%s/%04d.jpg" % [dir, n], 0.8)
