class_name TourEfectos
extends Node
## Sonidos del tour (campanas): como las voces (Voz), pero en otro reproductor para no cortar la narración.
## Web: <audio> propio (Ogg Opus o MP3); APK y escritorio: MP3 del paquete en un AudioStreamPlayer.

const VOLUMEN := 0.55

var en_web := OS.has_feature("web")
var _js: JavaScriptObject
var _jugador: AudioStreamPlayer

const JS := """
window.sucreEfecto = window.sucreEfecto || (() => {
  const prueba = document.createElement('audio');
  const fmt = prueba.canPlayType('audio/ogg; codecs="opus"') ? 'opus' : 'mp3';
  const base = location.origin + '/ciudad3d/datos/';
  let actual = null;
  return {
    tocar(ruta, v, vol) {
      if (actual) actual.pause();
      actual = new Audio(base + ruta + '.' + fmt + '.bin' + (v ? '?v=' + v : ''));
      actual.volume = vol;
      actual.play().catch(() => {});
    },
    callar() { if (actual) { actual.pause(); actual = null; } },
  };
})();
"""

func _ready() -> void:
	if en_web:
		JavaScriptBridge.eval(JS, true)
		_js = JavaScriptBridge.get_interface("sucreEfecto")
	else:
		_jugador = AudioStreamPlayer.new()
		_jugador.volume_db = linear_to_db(VOLUMEN)
		add_child(_jugador)

## s = {voz (ruta sin formato), av}
func tocar(s: Dictionary) -> void:
	var ruta: String = s.get("voz", "")
	if ruta == "":
		return
	if en_web:
		_js.tocar(ruta, str(s.get("av", "")), VOLUMEN)
		return
	var b := FileAccess.get_file_as_bytes("res://datos/" + ruta + ".mp3.bin")
	if b.is_empty():
		return
	var st := AudioStreamMP3.new()
	st.data = b
	_jugador.stream = st
	_jugador.play()

func callar() -> void:
	if en_web:
		_js.callar()
	elif _jugador.playing:
		_jugador.stop()
