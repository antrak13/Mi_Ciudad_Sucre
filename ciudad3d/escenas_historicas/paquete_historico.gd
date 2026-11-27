class_name PaqueteHistorico
extends Node
## Recursos pesados de las escenas históricas cargados aparte de la ciudad (solo en la web).
##
## En la web, sucre.pck lleva lo necesario para ver la plaza; el modelo y las texturas de la Casa de la Libertad
## (~12 MB) van en /ciudad3d/historica.pck. Este nodo lo descarga en segundo plano cuando la ciudad ya está a la
## vista y lo monta con ProjectSettings.load_resource_pack: al pedir el museo ya está en memoria. Si el visitante
## llega antes, la entrada espera a que termine y muestra el avance.
## En escritorio y en el APK los recursos ya vienen dentro del paquete principal: no se descarga nada.

signal avance(fraccion: float)
signal listo

const URL := "/ciudad3d/historica.pck"
const DESTINO := "user://historica.pck"
const PRUEBA := "res://escenas_historicas/casa_libertad/casa_libertad.glb"
## espera tras arrancar para no competir con la descarga de la zona inicial de la ciudad
const ESPERA_S := 8.0

static var _montado := false
var _http: HTTPRequest
var _descargando := false


static func disponible() -> bool:
	return _montado or ResourceLoader.exists(PRUEBA)


func _ready() -> void:
	if disponible():
		return
	get_tree().create_timer(ESPERA_S).timeout.connect(descargar)


## Empieza la descarga (si no empezó). Emite 'listo' al montarse el paquete.
func descargar() -> void:
	if disponible():
		listo.emit()
		return
	if _descargando:
		return
	_descargando = true
	var origen := ""
	if OS.has_feature("web"):
		origen = str(JavaScriptBridge.eval("location.origin", true))
	_http = HTTPRequest.new()
	_http.body_size_limit = 64 * 1024 * 1024
	_http.use_threads = false
	add_child(_http)
	_http.request_completed.connect(_al_terminar)
	set_process(true)
	if _http.request(origen + URL) != OK:
		_descargando = false
		push_warning("PaqueteHistorico: no se pudo pedir " + URL)


func _process(_d: float) -> void:
	if _http and _descargando:
		var total := _http.get_body_size()
		if total > 0:
			avance.emit(float(_http.get_downloaded_bytes()) / float(total))


func _al_terminar(resultado: int, codigo: int, _h: PackedStringArray, cuerpo: PackedByteArray) -> void:
	_descargando = false
	set_process(false)
	if resultado != HTTPRequest.RESULT_SUCCESS or codigo != 200:
		push_warning("PaqueteHistorico: descarga fallida (%d, HTTP %d)" % [resultado, codigo])
		return
	# se escribe y se cierra antes de montar (con download_file el archivo seguía abierto y el montaje fallaba)
	var f := FileAccess.open(DESTINO, FileAccess.WRITE)
	if f == null:
		push_warning("PaqueteHistorico: no se pudo escribir %s (%d)" % [DESTINO, FileAccess.get_open_error()])
		return
	f.store_buffer(cuerpo)
	f.close()
	if not ProjectSettings.load_resource_pack(DESTINO, true):
		push_warning("PaqueteHistorico: no se pudo montar " + DESTINO)
		return
	_montado = true
	print("PaqueteHistorico: escenas históricas montadas, museo disponible=", ResourceLoader.exists(PRUEBA))
	listo.emit()
