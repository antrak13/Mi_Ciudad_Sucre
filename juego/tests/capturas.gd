extends Node
## Toma capturas del nivel desde puntos de vista fijos para revisar los gráficos.
## Uso: godot --path juego res://tests/capturas.tscn
## Abre una ventana unos segundos y guarda los PNG en build/capturas/.

const NIVEL := preload("res://escenas/niveles/asamblea_1825.tscn")
const VISTAS := [
	{"nombre": "1_patio_hacia_sala", "desde": Vector3(1.5, 1.6, 9.0), "hacia": Vector3(0.0, 2.6, -12.0)},
	{"nombre": "2_claustro_oeste", "desde": Vector3(-9.0, 1.6, 9.0), "hacia": Vector3(-8.6, 1.8, -8.0)},
	{"nombre": "3_galeria_este", "desde": Vector3(-4.0, 1.6, 6.0), "hacia": Vector3(8.5, 2.0, -2.0)},
	{"nombre": "4_sala_mayor", "desde": Vector3(0.0, 1.6, -13.0), "hacia": Vector3(0.0, 2.4, -36.0)},
	{"nombre": "5_presidencia", "desde": Vector3(3.2, 1.6, -27.0), "hacia": Vector3(0.0, 1.6, -34.0)},
	{"nombre": "6_desde_el_coro", "desde": Vector3(4.5, 1.6, -33.5), "hacia": Vector3(-1.0, 3.2, -14.0)},
	# Personajes de la Escena 1, de frente y a la altura de los ojos
	{"nombre": "7_mendizabal", "desde": Vector3(-2.2, 1.6, 6.3), "hacia": Vector3(-3.0, 1.2, 4.0)},
	{"nombre": "8_diputado_peru", "desde": Vector3(-5.0, 1.6, -3.7), "hacia": Vector3(-5.8, 1.2, -6.0)},
	{"nombre": "9_diputado_rioplata", "desde": Vector3(8.4, 3.1, -0.7), "hacia": Vector3(9.2, 2.7, -3.0)},
	{"nombre": "10_olaneta", "desde": Vector3(-3.4, 1.6, -25.7), "hacia": Vector3(-4.2, 1.2, -28.0)},
	{"nombre": "11_serrano", "desde": Vector3(0.8, 1.6, -30.9), "hacia": Vector3(0.0, 1.2, -33.2)},
]


func _ready() -> void:
	var nivel := NIVEL.instantiate()
	add_child(nivel)
	var interfaz := nivel.get_node("Interfaz") as CanvasLayer
	var camara := Camera3D.new()
	camara.fov = 72.0
	add_child(camara)
	await get_tree().process_frame
	interfaz.visible = false
	(nivel.get_node("Jugador") as Node3D).visible = false  # su brazo flotaría frente a la cámara
	camara.make_current()

	var carpeta := ProjectSettings.globalize_path("res://").path_join("../build/capturas")
	DirAccess.make_dir_recursive_absolute(carpeta)
	for vista: Dictionary in VISTAS:
		camara.global_position = vista["desde"]
		camara.look_at(vista["hacia"])
		for i in 30:
			await get_tree().process_frame
		var imagen := get_viewport().get_texture().get_image()
		var ruta := carpeta.path_join("%s.png" % vista["nombre"])
		imagen.save_png(ruta)
		print("Captura: ", ruta)
	get_tree().quit()
