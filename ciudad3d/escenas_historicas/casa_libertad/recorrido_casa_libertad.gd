extends Node3D
## Escena rápida de recorrido en primera persona para probar el interior y fachada de Casa de la Libertad
## directamente al iniciar (Godot 4.7 Compatibility / Web / Escritorio), sin necesidad de cargar toda la ciudad.

const CASA_ESCENA := preload("res://escenas_historicas/casa_libertad/casa_libertad.tscn")
const HORAS_CICLO := ["dia", "atardecer", "noche", "amanecer"]

var museo: CasaLibertadMuseo
var jugador: Jugador
var sol: DirectionalLight3D
var entorno: Environment
var _cielo_mat: ShaderMaterial
var _idx_hora := 0
var _btn_hora: Button
var _cl_overlay: CanvasLayer
var _captura := ""
var _captura_t := 0.0
var _portal_salida: Area3D
var _puede_salir := false

func _ready() -> void:
	Hora.registrar_globales()
	_crear_entorno_e_iluminacion()

	museo = CASA_ESCENA.instantiate() as CasaLibertadMuseo
	add_child(museo)

	_crear_acera_exterior()

	jugador = Jugador.new()
	jugador.name = "Jugador"
	add_child(jugador)
	jugador.visible = true
	jugador.activo = true
	jugador.colocar(Vector3(0.0, 0.04, 5.5), 0.0)   # 5.5 m frente al portón mirando al norte (-Z)
	jugador.camara.make_current()

	_crear_overlay_controles()
	_configurar_portal_regreso_si_aplica()
	add_child(PortalAsamblea1825.new())   # [H] en el Salón: viaje al juego de la Asamblea de 1825 (portal_1825.gd)

	var h_env := OS.get_environment("SUCRE_HORA")
	if h_env != "" and Hora.ATMOSFERAS.has(h_env):
		_idx_hora = HORAS_CICLO.find(h_env)
		if _idx_hora < 0:
			_idx_hora = 0
	_aplicar_hora(HORAS_CICLO[_idx_hora])

	if OS.get_environment("SUCRE_TOMA") != "":
		var t := OS.get_environment("SUCRE_TOMA").split(",")
		if t.size() >= 5:
			jugador.colocar(Vector3(float(t[0]), float(t[1]) - Jugador.ALTURA_OJOS, float(t[2])), deg_to_rad(-float(t[3])))
			jugador.pitch = deg_to_rad(float(t[4]))
			jugador.mirar(0.0, 0.0)
	_captura = OS.get_environment("SUCRE_CAPTURA")
	if OS.get_environment("SUCRE_VERIFICAR") != "":
		call_deferred("_ejecutar_autoverificacion")

func _ejecutar_autoverificacion() -> void:
	for _i in range(6):
		await get_tree().physics_frame
		await get_tree().process_frame
	var glb_root := museo.glb_raiz
	var bodies: Array[StaticBody3D] = []
	var vis_count := 0
	var pila: Array[Node] = [glb_root]
	while not pila.is_empty():
		var n: Node = pila.pop_back()
		for h in n.get_children():
			pila.append(h)
		if n is StaticBody3D:
			var sb := n as StaticBody3D
			bodies.append(sb)
			if (sb.scale - Vector3.ONE).length() > 0.001:
				push_error("[VERIFY] Escala != 1 en %s: %s" % [sb.name, str(sb.scale)])
				get_tree().quit(1)
				return
		elif n is MeshInstance3D and (n as MeshInstance3D).visibility_range_end > 0.0:
			vis_count += 1

	print("[VERIFY] StaticBody3D (-colonly): ", bodies.size(), " -> ", bodies.map(func(b): return "%s(layer=%d,scale=%s)" % [b.name, b.collision_layer, str(b.scale)]))
	print("[VERIFY] OmniLight3D activas: ", museo.luces_creadas.size(), " -> ", museo.luces_creadas.map(func(l): return "%s(shadow=%s)" % [l.name, str(l.shadow_enabled)]))
	print("[VERIFY] Mallas con VisibilityRange > 0: ", vis_count)
	print("[VERIFY] POIs registrados en Interaccion: ", museo.areas_poi.size())
	var ali := CasaLibertadMuseo.transform_en_plaza_25()
	print("[VERIFY] Plaza 25 alignment origin=", ali.origin, " rot_y=", CasaLibertadMuseo.ROTACION_Y_PLAZA_25)

	var puntos_prueba := [
		["Patio/Estatua", Vector3(3.05, 0.20, -13.90), "POI_ESTATUA", false],
		["Salon", Vector3(0.0, 0.42, -45.8), "POI_ACTA_INDEPENDENCIA", false],
		["Puerta Claustro->Guerrilleros", Vector3(8.30, 0.42, -26.8), "", false],
		["Guerrilleros/Belgrano", Vector3(9.80, 0.42, -33.4), "POI_BANDERA_BELGRANO", false],
		["Guerrilleros/Juana", Vector3(8.50, 0.42, -45.8), "POI_SALA_MUSEO", false],
		["Paso Puerta Verde->Salon", Vector3(4.00, 0.42, -45.0), "", false],
		["Puerta Claustro->Senado", Vector3(-9.60, 0.42, -20.8), "", false],
		["Senado/Aguila", Vector3(-12.80, 0.42, -20.8), "POI_PASILLO_AGUILA", false],
		["Galeria Presidentes/Bolivar", Vector3(-14.10, 0.42, -29.2), "POI_SALA_BOLIVAR", true],
	]
	for p in puntos_prueba:
		jugador.colocar(p[1], 0.0)
		for _i in range(6):
			await get_tree().physics_frame
		var act := Interaccion.actual()
		print("[VERIFY] %s pos=%s en_suelo=%s POI=%s" % [p[0], str(jugador.global_position), str(jugador.is_on_floor()), act])
		if not jugador.is_on_floor():
			push_error("[VERIFY] Sin suelo en %s" % p[0])
			get_tree().quit(1)
			return
		if p[2] != "" and not String(p[2]).to_lower() in act.to_lower() and act == "":
			push_error("[VERIFY] POI vacio en %s" % p[0])
			get_tree().quit(1)
			return

	# Verificar tránsito libre sin topes en umbrales (Patio->Guerrilleros, Guerrilleros->Salon, Patio->Oeste)
	var tramos := [
		["Cruce Claustro->Guerrilleros", Vector3(8.30, 0.42, -26.6), Vector3(0.0, 0.0, -3.5)],
		["Cruce Puerta Verde", Vector3(6.40, 0.42, -45.0), Vector3(-3.0, 0.0, 0.0)],
		["Cruce Claustro->Senado", Vector3(-9.40, 0.42, -20.8), Vector3(-3.0, 0.0, 0.0)],
	]
	for tr in tramos:
		jugador.colocar(tr[1], 0.0)
		await get_tree().physics_frame
		var vel_v: Vector3 = tr[2]
		for _step in range(36):
			jugador.velocity = Vector3(vel_v.x, -4.0, vel_v.z)
			jugador.move_and_slide()
		var disp: float = (jugador.global_position - (tr[1] as Vector3)).length()
		print("[VERIFY] %s desplazamiento=%.2f m pos_final=%s" % [tr[0], disp, str(jugador.global_position)])
		if disp < 1.8:
			push_error("[VERIFY] Paso bloqueado en %s (solo %.2f m)" % [tr[0], disp])
			get_tree().quit(1)
			return

	if bodies.size() < 3 or museo.luces_creadas.size() != 5 or vis_count < 45 or museo.areas_poi.size() < 12:
		push_error("[VERIFY] Falla en verificacion integral")
		get_tree().quit(1)
		return
	jugador.colocar(Vector3(-14.10, 0.42, -29.2), 0.0)
	for _i in range(6):
		await get_tree().physics_frame
	Interaccion.usar()
	await get_tree().process_frame
	print("[VERIFY] Ficha abierta=", museo.get("_panel_abierto"), " titulo=", museo.get("_ficha_titulo").text)
	if not bool(museo.get("_panel_abierto")) or not ("Senado" in museo.get("_ficha_titulo").text or "Presidentes" in museo.get("_ficha_titulo").text):
		push_error("[VERIFY] Interaccion.usar() no abrio la ficha actualizada")
		get_tree().quit(1)
		return
	print("[VERIFY] OK_FASE_4_GODOT")
	if _captura == "":
		get_tree().quit(0)

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventKey and ev.pressed and not ev.echo:
		if ev.physical_keycode == KEY_N:
			_alternar_hora()
		elif _puede_salir and ev.physical_keycode in [KEY_B, KEY_ESCAPE]:
			_regresar_a_plaza()

func _process(dt: float) -> void:
	if _captura != "":
		_captura_t += dt
		var espera := float(OS.get_environment("SUCRE_ESPERA")) if OS.get_environment("SUCRE_ESPERA") != "" else 2.5
		if _captura_t >= espera:
			var ruta := _captura
			_captura = ""
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(ruta)
			var o := jugador.camara.global_position
			var ri := func(k): return RenderingServer.get_rendering_info(k)
			print("[CasaLibertad] Captura %s guardada · ojos=%.2f,%.2f,%.2f · fps=%d · llamadas=%d · tris=%.0f" % [
				ruta, o.x, o.y, o.z, Engine.get_frames_per_second(),
				ri.call(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				float(ri.call(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME))])
			get_tree().quit()

func _crear_entorno_e_iluminacion() -> void:
	entorno = Environment.new()
	entorno.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	_cielo_mat = ShaderMaterial.new()
	_cielo_mat.shader = load("res://shaders/cielo.gdshader")
	sky.sky_material = _cielo_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	entorno.sky = sky
	entorno.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	entorno.ambient_light_color = Color(0.86, 0.80, 0.72)
	entorno.ambient_light_energy = 0.55
	entorno.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	entorno.tonemap_mode = Environment.TONE_MAPPER_FILMIC

	var we := WorldEnvironment.new()
	we.name = "EntornoMuseo"
	we.environment = entorno
	add_child(we)

	sol = DirectionalLight3D.new()
	sol.name = "SolMuseo"
	sol.shadow_enabled = not OS.has_feature("mobile")
	sol.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sol.directional_shadow_max_distance = 72.0
	sol.shadow_bias = 0.05
	sol.shadow_normal_bias = 1.2
	sol.shadow_blur = 1.5
	add_child(sol)

func _alternar_hora() -> void:
	_idx_hora = (_idx_hora + 1) % HORAS_CICLO.size()
	_aplicar_hora(HORAS_CICLO[_idx_hora])

func _aplicar_hora(nombre_hora: String) -> void:
	var a: Dictionary = Hora.ATMOSFERAS[nombre_hora]
	var dir: Vector3 = (a["sol"][2] as Vector3).normalized()
	_cielo_mat.set_shader_parameter("mapa", load("res://cielo/%s.jpg" % a["cielo"]))
	var astro: Vector2 = a["astro"]
	_cielo_mat.set_shader_parameter("desfase", astro.x - (atan2(dir.x, dir.z) / TAU + 0.5))
	_cielo_mat.set_shader_parameter("horizonte", Color(a["horizonte"]))

	sol.light_color = Color(a["sol"][0])
	sol.light_energy = 1.25 if nombre_hora == "dia" else (0.95 if nombre_hora in ["atardecer", "amanecer"] else 0.28)
	sol.look_at_from_position(Vector3.ZERO, -dir, Vector3.UP)

	var es_noche: bool = a["luces"]
	entorno.ambient_light_color = Color(0.24, 0.28, 0.44) if es_noche else (Color(0.92, 0.70, 0.54) if nombre_hora == "atardecer" else Color(0.86, 0.80, 0.72))
	entorno.ambient_light_energy = 0.30 if es_noche else 0.58
	if museo != null:
		museo.fijar_modo_noche(es_noche)
	if _btn_hora != null:
		_btn_hora.text = "Hora: %s [N]" % nombre_hora.capitalize()

## Acera y calzada de aproximación al frente del edificio para poder admirar la portada completa.
func _crear_acera_exterior() -> void:
	var cuerpo := StaticBody3D.new()
	cuerpo.name = "SueloExteriorAproximacion"
	cuerpo.collision_layer = 1
	cuerpo.collision_mask = 0

	var col := CollisionShape3D.new()
	var box_sh := BoxShape3D.new()
	box_sh.size = Vector3(28.0, 0.4, 10.0)
	col.shape = box_sh
	col.position = Vector3(0.0, -0.205, 5.2)
	cuerpo.add_child(col)

	var topes := [
		Vector3(-13.5, 1.5, 5.2),
		Vector3(13.5, 1.5, 5.2),
		Vector3(0.0, 1.5, 10.2),
	]
	for k in topes.size():
		var c_muro := CollisionShape3D.new()
		var sh_m := BoxShape3D.new()
		sh_m.size = Vector3(0.5, 3.0, 10.5) if k < 2 else Vector3(28.0, 3.0, 0.5)
		c_muro.shape = sh_m
		c_muro.position = topes[k]
		cuerpo.add_child(c_muro)

	var vis := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(28.0, 6.2)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.24, 0.25, 0.27)  # calzada asfalto/adoquin gris oscuro
	mat.roughness = 0.92
	pm.material = mat
	vis.mesh = pm
	vis.position = Vector3(0.0, -0.025, 7.6)
	vis.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	cuerpo.add_child(vis)

	# Bordillo de granito gris separando acera (Z<=4.5) y calzada oscura
	var bord := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(26.0, 0.14, 0.22)
	var mat_b := StandardMaterial3D.new()
	mat_b.albedo_color = Color(0.34, 0.34, 0.35)
	mat_b.roughness = 0.88
	bm.material = mat_b
	bord.mesh = bm
	bord.position = Vector3(0.0, -0.04, 4.50)
	bord.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	cuerpo.add_child(bord)

	add_child(cuerpo)

func _crear_overlay_controles() -> void:
	_cl_overlay = CanvasLayer.new()
	_cl_overlay.layer = 14
	add_child(_cl_overlay)
	var cl := _cl_overlay

	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.984, 0.976, 0.957, 0.92)
	sb.set_corner_radius_all(10)
	sb.border_width_top = 3
	sb.border_color = Color("#a9432d")
	sb.content_margin_left = 14
	sb.content_margin_right = 14
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8

	var pc := PanelContainer.new()
	pc.add_theme_stylebox_override("panel", sb)
	pc.position = Vector2(16, 14)

	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 4)
	var t := Label.new()
	t.text = "Casa de la Libertad · 1809"
	t.add_theme_font_size_override("font_size", 20)
	t.add_theme_color_override("font_color", Color("#a9432d"))
	var ay := Label.new()
	ay.text = "WASD: caminar · Arrastrar ratón / Q / Flechas: mirar · Shift: correr · E: ficha histórica"
	ay.add_theme_font_size_override("font_size", 14)
	ay.add_theme_color_override("font_color", Color("#2b1d16"))
	vb.add_child(t)
	vb.add_child(ay)
	pc.add_child(vb)
	cl.add_child(pc)

	_btn_hora = Button.new()
	_btn_hora.text = "Hora: Dia [N]"
	_btn_hora.add_theme_font_size_override("font_size", 16)
	_btn_hora.add_theme_stylebox_override("normal", sb)
	_btn_hora.add_theme_stylebox_override("hover", sb)
	_btn_hora.add_theme_stylebox_override("focus", sb)
	_btn_hora.add_theme_color_override("font_color", Color("#2b1d16"))
	_btn_hora.pressed.connect(_alternar_hora)
	_btn_hora.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT, Control.PRESET_MODE_MINSIZE, 16)
	cl.add_child(_btn_hora)

func _configurar_portal_regreso_si_aplica() -> void:
	if not get_tree().has_meta("desde_plaza_casa_libertad"):
		return
	var btn_plaza := Button.new()
	btn_plaza.text = "Volver a Plaza 25 de Mayo [B]"
	btn_plaza.add_theme_font_size_override("font_size", 15)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color("#a9432d")
	sb.set_corner_radius_all(8)
	sb.content_margin_left = 14
	sb.content_margin_right = 14
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	for st in ["normal", "hover", "focus", "pressed"]:
		btn_plaza.add_theme_stylebox_override(st, sb)
	btn_plaza.add_theme_color_override("font_color", Color.WHITE)
	btn_plaza.pressed.connect(_regresar_a_plaza)
	btn_plaza.position = Vector2(16, 94)
	_cl_overlay.add_child(btn_plaza)
	_puede_salir = true

	_portal_salida = Area3D.new()
	_portal_salida.collision_layer = 0
	_portal_salida.collision_mask = 8
	var cs := CollisionShape3D.new()
	var bx := BoxShape3D.new()
	bx.size = Vector3(10.0, 3.0, 2.0)
	cs.shape = bx
	_portal_salida.add_child(cs)
	_portal_salida.position = Vector3(0.0, 1.5, 8.8)
	_portal_salida.body_entered.connect(func(_b): _regresar_a_plaza())
	add_child(_portal_salida)

func _regresar_a_plaza() -> void:
	get_tree().remove_meta("desde_plaza_casa_libertad")
	get_tree().set_meta("retorno_plaza_casa_libertad", true)
	get_tree().change_scene_to_file("res://escenas/principal.tscn")
