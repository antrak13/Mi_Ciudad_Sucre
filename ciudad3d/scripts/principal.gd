extends Node3D
## Sucre 3D (web en la PC y app en el celular): une ciudad, hora del día, cámaras, tráfico, posproceso e interfaz.
## Flujo: pantalla de carga (la ciudad gira detrás) → a pie en la calle con nombre más cercana a la plaza.
## En la web, incrustada en la portada (?embebido): carga a escondidas, avisa "lista" y espera la orden de entrar
## (puente.gd). La vista aérea está desactivada (decisión del usuario); la cámara aérea solo gira durante la carga.

enum Modo { INICIO, PIE }

const CENTRO := Vector3(-205.0, 58.0, 150.0)       # Plaza 25 de Mayo / San Francisco
const MONUMENTO := Vector2(-176.7, 233.0)          # llegada desde la portada: de cara al monumento (rumbo norte)
const CLAVE_POSICION := "posicion"

var modo := Modo.INICIO
var ciudad: Ciudad
var jugador: Jugador
var aerea: CamaraAerea
var ui: Interfaz
var calles := Calles.new()
var noche: Noche
var post: Post
var oclusion: Oclusion
var calidad: Calidad
var trafico: Trafico
var pasto: Pasto
var puente: Puente
var revision: Revision
var embebido := false
var _t_calle := 0.0
var _t_inicio := 0.0
var _t_guardar := 0.0
var _lista := false
var _pendiente = null          # {x, z, yaw, desde} mientras se espera que cargue el suelo donde aparecer
var _captura := ""
var _captura_t := 0.0
var _t_log := 0.0
var _retorno_museo := false
var tour: Tour
var _tour_pendiente := false

## Cierre ordenado: las cachés estáticas de materiales se sueltan mientras el servidor de render sigue vivo.
func _exit_tree() -> void:
	Estilo.liberar()

func _ready() -> void:
	Hora.registrar_globales()               # antes de crear ningún material
	Hora.montar(self)
	ciudad = Ciudad.new()
	ciudad.name = "Ciudad"
	add_child(ciudad)
	noche = Noche.new()
	noche.name = "Noche"
	add_child(noche)
	aerea = CamaraAerea.new()
	aerea.name = "CamaraAerea"
	add_child(aerea)
	jugador = Jugador.new()
	jugador.name = "Jugador"
	jugador.ciudad = ciudad
	add_child(jugador)
	trafico = Trafico.new()
	trafico.name = "Trafico"
	trafico.ciudad = ciudad
	trafico.jugador = jugador
	add_child(trafico)
	pasto = Pasto.new()
	pasto.name = "Pasto"
	pasto.ciudad = ciudad
	add_child(pasto)
	post = Post.new()
	post.name = "Post"
	add_child(post)
	oclusion = Oclusion.new()
	oclusion.name = "Oclusion"
	oclusion.fijar_radio(8.0)
	add_child(oclusion)
	ui = Interfaz.new()
	ui.name = "Interfaz"
	add_child(ui)
	ui.visible = not Datos.en_web          # en la web la interfaz es la de la página (React), encima del lienzo
	revision = Revision.new()
	revision.name = "Revision"
	revision.principal = self
	add_child(revision)
	calidad = Calidad.new()
	calidad.name = "Calidad"
	calidad.ciudad = ciudad
	calidad.post = post
	calidad.oclusion = oclusion
	calidad.trafico = trafico
	calidad.pasto = pasto
	add_child(calidad)
	puente = Puente.new()
	puente.name = "Puente"
	puente.principal = self
	add_child(puente)
	embebido = puente.parametro("embebido") != null
	var encuentros := Encuentros.new()       # personajes y encuentros (scripts/personajes/)
	encuentros.name = "Encuentros"
	encuentros.jugador = jugador
	encuentros.ciudad = ciudad
	encuentros.interfaz = ui
	encuentros.puente = puente
	encuentros.trafico = trafico
	add_child(encuentros)
	tour = Tour.new()                         # tour guiado (scripts/tour/, guion en tour/guion.json)
	tour.name = "Tour"
	tour.principal = self
	tour.ciudad = ciudad
	tour.jugador = jugador
	tour.interfaz = ui
	tour.puente = puente
	tour.trafico = trafico
	tour.encuentros = encuentros
	add_child(tour)
	ui.iniciar_tour.connect(iniciar_tour)
	calles.cargar(await Datos.texto("calles.json"))
	noche.cargar(await Datos.json("faroles.json"))
	ui.entrar_pie.connect(func():
		if _retorno_museo:
			_retorno_museo = false
			var b_p := CasaLibertadMuseo.POSICION_PLAZA_25
			var n_p := Vector3(sin(CasaLibertadMuseo.ROTACION_Y_PLAZA_25), 0.0, cos(CasaLibertadMuseo.ROTACION_Y_PLAZA_25))
			var llegada := b_p + n_p * 3.0
			_pedir_pie(llegada.x, llegada.z, CasaLibertadMuseo.ROTACION_Y_PLAZA_25 + PI)
		else:
			_pedir_pie(CENTRO.x, CENTRO.z, NAN))
	ui.mirar.connect(func(dx, dy): jugador.mirar(dx, dy))
	ui.mover.connect(func(v, c): jugador.entrada_tactil(v, c))
	ui.minimapa_ir.connect(_minimapa_ir)
	ui.cambiar_hora.connect(cambiar_hora)
	# hora: ?hora=… o la última elegida; SUCRE_HORA=… (pruebas en el escritorio)
	var h = puente.parametro("hora")
	if h == null:
		h = OS.get_environment("SUCRE_HORA") if OS.get_environment("SUCRE_HORA") != "" else Guardado.leer("hora", "dia")
	_aplicar_hora(h if Hora.ATMOSFERAS.has(h) else "dia", false)
	# inicio: la ciudad gira lentamente detrás de la pantalla de carga
	aerea.activa = true
	aerea.autogiro = not embebido
	aerea.objetivo = CENTRO
	aerea.make_current()
	ciudad.fijar_foco(CENTRO)
	if embebido:
		ui.ocultar_inicio()
		ui.hud_visible(false)
		_pedir_pie(MONUMENTO.x, MONUMENTO.y, 0.0)
	_captura = OS.get_environment("SUCRE_CAPTURA")
	if OS.get_environment("SUCRE_ESCENA") == "casa_libertad" or "--casa-libertad" in OS.get_cmdline_user_args():
		get_tree().change_scene_to_file.call_deferred("res://escenas_historicas/casa_libertad/recorrido_casa_libertad.tscn")
		return
	var portal_museo := PortalCasaLibertad.new()
	portal_museo.name = "PortalCasaLibertad"
	portal_museo.principal = self
	add_child(portal_museo)
	if get_tree().has_meta("retorno_plaza_casa_libertad"):
		get_tree().remove_meta("retorno_plaza_casa_libertad")
		_retorno_museo = true
	if OS.get_environment("SUCRE_MINIMAPA") != "":
		# herramienta: genera la imagen del minimapa y sale (scripts/generador_minimapa.gd)
		set_process(false)
		ui.visible = false
		post.visible = false
		var g := GeneradorMinimapa.new()
		g.ciudad = ciudad
		g.ocultar = [jugador, trafico, pasto]
		add_child(g)

# ------------------------------------------------------------------------------------------------- hora del día
## Día → atardecer → noche y noche → amanecer → día (pedido del usuario, 2026-11-23): cada paso con un fundido corto.
func cambiar_hora() -> void:
	var pasos := ["amanecer", "dia"] if Hora.actual in ["noche", "amanecer"] else ["atardecer", "noche"]
	for k in pasos.size():
		var n: String = pasos[k]
		get_tree().create_timer(k * 2.2).timeout.connect(func(): ui.fundir(func(): _aplicar_hora(n, k == pasos.size() - 1)))

func _aplicar_hora(h: String, guardar := true) -> void:
	Hora.aplicar(h)
	noche.fijar(Hora.luces())
	post.fijar_hora(Hora.post())
	ui.poner_hora(Hora.luces())
	puente.emitir({"tipo": "hora", "hora": h})
	if guardar:
		Guardado.escribir("hora", h)

# ------------------------------------------------------------------------------------------------- a pie
func _pedir_pie(x: float, z: float, yaw: float) -> void:
	# se espera a que el suelo del lugar tenga colisión para poder apoyar los pies
	_pendiente = {"x": x, "z": z, "yaw": yaw, "desde": Time.get_ticks_msec()}
	ciudad.fijar_foco(Vector3(x, 0.0, z))

## Entrada desde la portada (puente): aparece en la plaza, de cara al monumento.
func entrar_desde_portada() -> void:
	ui.hud_visible(true)
	if modo == Modo.PIE:
		_ir(MONUMENTO.x, MONUMENTO.y, 0.0)

## Vuelve exactamente a una vista (posición guardada, revisiones): ojos en (x, y, z), rumbo (0 = norte, horario) e inclinación.
func tomar(x: float, y: float, z: float, rumbo: float, inclinacion: float) -> void:
	if modo != Modo.PIE:
		_pedir_pie(x, z, -rumbo)
		return
	jugador.colocar(Vector3(x, y - Jugador.ALTURA_OJOS, z), -rumbo)
	jugador.pitch = inclinacion
	jugador.mirar(0.0, 0.0)

# ------------------------------------------------------------------------------------------------- tour guiado
## Empieza el tour guiado (scripts/tour/): desde la portada, el botón del HUD o la página web.
func iniciar_tour() -> void:
	if modo != Modo.PIE:
		_tour_pendiente = true          # aún carga: empieza en cuanto se pueda estar a pie
		return
	tour.iniciar()

## Al terminar el tour: de vuelta a pie, frente al monumento de la plaza.
func tour_terminado() -> void:
	_ir(MONUMENTO.x, MONUMENTO.y, 0.0)

func _minimapa_ir(x: float, z: float) -> void:
	if modo == Modo.PIE:
		_ir(x, z, jugador.yaw)

## Salto (minimapa, revisiones, taller): el caminante aparece sobre lo primero que haya debajo, en la calle más cercana.
func _ir(x: float, z: float, yaw: float) -> void:
	_pedir_pie(x, z, yaw)

func _intentar_aparecer() -> void:
	var p: Dictionary = _pendiente
	var espera: float = (Time.get_ticks_msec() - int(p["desde"])) / 1000.0
	var estado := get_world_3d().direct_space_state
	var candidatos := calles.puntos_cercanos(p["x"], p["z"], 60)
	candidatos.push_front(Vector2(p["x"], p["z"]))
	var elegido = null
	var pendientes := 0
	for c in candidatos:
		if not ciudad.suelo_listo(c.x, c.y):
			pendientes += 1
			continue
		var q := PhysicsRayQueryParameters3D.create(Vector3(c.x, 420.0, c.y), Vector3(c.x, -100.0, c.y), 3)
		var h := estado.intersect_ray(q)
		if h.is_empty() or (h["collider"] as CollisionObject3D).collision_layer != 1:
			continue
		var pos: Vector3 = h["position"]
		elegido = pos
		break
	if elegido == null:
		if (pendientes > 0 and espera < 20.0) or espera < 30.0:
			return
		_pendiente = null
		return
	var yaw: float = p["yaw"]
	if is_nan(yaw):
		yaw = _rumbo_mas_libre(elegido, estado)
	_pendiente = null
	modo = Modo.PIE
	oclusion.fijar_radio(2.5)
	aerea.activa = false
	jugador.visible = true
	jugador.colocar(elegido + Vector3(0, 0.05, 0), yaw)
	jugador.activo = true
	if OS.get_environment("SUCRE_YAW") != "":      # solo pruebas: rumbo e inclinación dados
		jugador.yaw = float(OS.get_environment("SUCRE_YAW"))
		jugador.pitch = float(OS.get_environment("SUCRE_PITCH"))
		jugador.mirar(0.0, 0.0)
	jugador.camara.make_current()
	ui.ocultar_inicio()
	if OS.get_environment("SUCRE_TOMA") != "":      # solo pruebas: "x,y,z,rumbo,inclinación" (ojos, grados)
		var t := OS.get_environment("SUCRE_TOMA").split(",")
		tomar(float(t[0]), float(t[1]), float(t[2]), deg_to_rad(float(t[3])), deg_to_rad(float(t[4])))
	Hora.niebla_a_pie(true)
	ui.modo(true)
	ui.minimapa.peaton = true
	calidad.fin_carga()
	if not embebido:
		ciudad.presupuesto_ms = Ciudad.PRESUPUESTO_MS     # incrustada sigue cargando rápido hasta que se entra
	trafico.arrancar()
	puente.avisar_lista()
	if _tour_pendiente or (OS.get_environment("SUCRE_TOUR") != "" and not tour.activo):
		_tour_pendiente = false
		tour.iniciar.call_deferred()

func _rumbo_mas_libre(p: Vector3, estado: PhysicsDirectSpaceState3D) -> float:
	var mejor := -1.0
	var mejor_ang := 0.0
	for k in 16:
		var a := float(k) / 16.0 * TAU
		var d := Vector3(-sin(a), 0.0, -cos(a))
		var q := PhysicsRayQueryParameters3D.create(p + Vector3(0, 1.6, 0), p + Vector3(0, 1.6, 0) + d * 200.0, 2)
		var h := estado.intersect_ray(q)
		var dist := 200.0 if h.is_empty() else (h["position"] as Vector3).distance_to(p)
		if dist > mejor:
			mejor = dist
			mejor_ang = a
	return mejor_ang

# ------------------------------------------------------------------------------------------------- cuadro a cuadro
func _process(dt: float) -> void:
	match modo:
		Modo.INICIO:
			_t_inicio += dt
			var f := ciudad.progreso_alrededor(CENTRO, 280.0)
			ui.progreso(f, "Armando la ciudad… %d%%" % int(f * 100.0))
			puente.progreso(f)
			if not _lista and ciudad.listo and (f >= 0.97 or _t_inicio > 25.0):
				_lista = true
				if OS.get_environment("SUCRE_X") != "":
					_pedir_pie(float(OS.get_environment("SUCRE_X")), float(OS.get_environment("SUCRE_Z")), NAN)
				elif not embebido:
					ui.entrar_pie.emit()
		Modo.PIE:
			if tour.activo:
				ciudad.fijar_foco(tour.foco)
				if _pendiente != null:
					_intentar_aparecer()
				return
			ciudad.fijar_foco(jugador.global_position)
			var m := ui.minimapa
			m.centro = Vector2(jugador.global_position.x, jugador.global_position.z)
			m.rumbo_ = jugador.yaw
			m.refrescar()
			_actualizar_calle(dt, m.centro, 14.0)
			_t_guardar += dt
			if _t_guardar > 2.0 and not embebido:
				_t_guardar = 0.0
				var g := jugador.global_position
				Guardado.escribir(CLAVE_POSICION, [g.x, g.z, jugador.yaw])
	if _pendiente != null:
		_intentar_aparecer()
	_pruebas(dt)

func _actualizar_calle(dt: float, p: Vector2, maximo: float) -> void:
	_t_calle += dt
	if _t_calle < 0.25:
		return
	_t_calle = 0.0
	ui.poner_calle(calles.calle(p.x, p.y, maximo))

## Solo pruebas: SUCRE_TOMAS=archivo.json ([{"nombre", "ojos": [x, y, z], "mira": [x, y, z], "fov"}]) fotografía cada vista
## en SUCRE_TOMAS_DIR (una sola ejecución para muchas vistas: así se diseñan las cámaras del tour) y sale.
var _tomas_hechas := false
func _fotografiar_tomas() -> void:
	_tomas_hechas = true
	var lista = JSON.parse_string(FileAccess.get_file_as_string(OS.get_environment("SUCRE_TOMAS")))
	var dir := OS.get_environment("SUCRE_TOMAS_DIR")
	trafico.visible = false
	trafico.process_mode = Node.PROCESS_MODE_DISABLED
	jugador.activo = false
	var cam := Camera3D.new()
	cam.near = 0.1
	cam.far = 6000.0
	add_child(cam)
	cam.make_current()
	for t in lista:
		var o: Array = t["ojos"]
		var m: Array = t["mira"]
		var ojos := Vector3(o[0], o[1], o[2])
		cam.fov = float(t.get("fov", 60.0))
		cam.look_at_from_position(ojos, Vector3(m[0], m[1], m[2]))
		ciudad.fijar_foco(ojos)
		var espera := 0.0
		while (ciudad.progreso_alrededor(ojos, 160.0) < 0.98 and espera < 25.0) or espera < 1.5:
			await get_tree().process_frame
			ciudad.fijar_foco(ojos)
			espera += get_process_delta_time()
		for i in 8:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_jpg(dir + "/" + str(t["nombre"]) + ".jpg", 0.85)
		print("toma ", t["nombre"])
	get_tree().quit()

## Banderas de prueba (solo escritorio): SUCRE_CAPTURA=ruta.png (y SUCRE_ESPERA=s), SUCRE_ANDAR=1, SUCRE_X/SUCRE_Z.
func _pruebas(dt: float) -> void:
	if modo == Modo.PIE and not _tomas_hechas and OS.get_environment("SUCRE_TOMAS") != "":
		_fotografiar_tomas()
	if modo == Modo.PIE and OS.get_environment("SUCRE_ANDAR") != "":
		jugador.entrada = Vector2(0, 1)
		_t_log += dt
		if _t_log > 1.0:
			_t_log = 0.0
			var p := jugador.global_position
			print("andar: (%.1f, %.1f, %.1f) en suelo=%s teselas=%d fps=%d" % [p.x, p.y, p.z, jugador.is_on_floor(), ciudad.cargadas_en_total, Engine.get_frames_per_second()])
	if _captura != "" and modo == Modo.PIE:
		_captura_t += dt
		if OS.get_environment("SUCRE_TOMA") != "":   # la toma se mantiene (el ratón sobre la ventana gira la cámara)
			var t := OS.get_environment("SUCRE_TOMA").split(",")
			tomar(float(t[0]), float(t[1]), float(t[2]), deg_to_rad(float(t[3])), deg_to_rad(float(t[4])))
		var espera := float(OS.get_environment("SUCRE_ESPERA")) if OS.get_environment("SUCRE_ESPERA") != "" else 12.0
		if _captura_t > espera:
			_captura = ""
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(OS.get_environment("SUCRE_CAPTURA"))
			var o := jugador.camara.global_position
			print("captura guardada (%d teselas, %d fps) ojos=%.2f,%.2f,%.2f rumbo=%.1f incl=%.1f" % [ciudad.cargadas_en_total,
				Engine.get_frames_per_second(), o.x, o.y, o.z, rad_to_deg(-jugador.yaw), rad_to_deg(jugador.pitch)])
			var ri := func(k): return RenderingServer.get_rendering_info(k)
			print("cuadro: %d llamadas, %d objetos, %.2f M triángulos; vídeo %d MB (texturas %d, búferes %d); memoria %d MB" % [
				ri.call(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME), ri.call(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
				ri.call(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME) / 1e6, ri.call(RenderingServer.RENDERING_INFO_VIDEO_MEM_USED) >> 20,
				ri.call(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED) >> 20, ri.call(RenderingServer.RENDERING_INFO_BUFFER_MEM_USED) >> 20,
				OS.get_static_memory_usage() >> 20])
			get_tree().quit()
