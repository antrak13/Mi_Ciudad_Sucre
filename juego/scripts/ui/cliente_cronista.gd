class_name ClienteCronista
extends Node
## Le pregunta al cronista por HTTP: POST /api/cronista de la web (web/src/app/api/cronista/route.ts).
## - En la web (juego incrustado en /asamblea) usa el mismo origen de la página.
## - En el escritorio usa http://localhost:3000 (servidor de la web encendido) o la variable CRONISTA_URL.
## Devuelve {respuesta, fuentes, modo} o {error}.

var _http: HTTPRequest


func _ready() -> void:
	_http = HTTPRequest.new()
	_http.timeout = 35.0
	add_child(_http)


func url() -> String:
	var propia := OS.get_environment("CRONISTA_URL")
	if not propia.is_empty():
		return propia
	if OS.has_feature("web"):
		return str(JavaScriptBridge.eval("window.location.origin", true)) + "/api/cronista"
	return "http://localhost:3000/api/cronista"


func preguntar(texto: String, idioma := "es") -> Dictionary:
	if _http.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return {"error": "El cronista todavía está respondiendo la pregunta anterior."}
	var cuerpo := JSON.stringify({"pregunta": texto, "idioma": idioma})
	var error := _http.request(url(), PackedStringArray(["Content-Type: application/json"]), HTTPClient.METHOD_POST, cuerpo)
	if error != OK:
		return {"error": "No pude enviar la pregunta (error %d)." % error}
	var r: Array = await _http.request_completed
	if r[0] != HTTPRequest.RESULT_SUCCESS or r[1] != 200:
		return {"error": "El cronista no está disponible. ¿Está encendido el servidor de la web (cd web && npx next dev)?"}
	var datos: Variant = JSON.parse_string((r[3] as PackedByteArray).get_string_from_utf8())
	return datos if datos is Dictionary else {"error": "El cronista respondió algo que no entiendo."}
