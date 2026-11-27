class_name TourEco
extends Node3D
## El repique de San Francisco la noche del 25 de mayo de 1809: ondas que salen del campanario y un trazo de luz dorada
## que viaja por encima de los tejados hasta la plaza mayor, adonde la campana llamó al vecindario.
## Todo es una cinta y unos anillos con un sombreador sin luz (suma de color): no pesa nada.

const TORRE := Vector3(-105.0, 84.0, -17.0)
const PLAZA := Vector3(-183.0, 66.0, 209.0)
const SEGMENTOS := 64
const ANCHO := 1.6

const SOMBREADOR := """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, fog_disabled;
uniform float avance = 0.0;      // hasta dónde llegó el trazo (0–1 del largo)
uniform float brillo = 1.0;
uniform vec3 color : source_color = vec3(1.0, 0.78, 0.36);
void fragment() {
	float u = UV.x;
	float borde = 1.0 - abs(UV.y * 2.0 - 1.0);
	float cuerpo = smoothstep(avance, avance - 0.08, u);           // lo ya recorrido
	float frente = exp(-pow((u - avance) * 28.0, 2.0)) * 2.2;       // la cabeza brillante
	float a = (cuerpo * 0.45 + frente) * pow(borde, 1.6) * brillo;
	ALBEDO = color * a;
	ALPHA = clamp(a, 0.0, 1.0);
}
"""

const ANILLO := """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, fog_disabled;
uniform float vida = 0.0;
void fragment() {
	float r = abs(UV.y * 2.0 - 1.0);
	float a = (1.0 - r) * (1.0 - vida) * 0.9;
	ALBEDO = vec3(1.0, 0.82, 0.45) * a;
	ALPHA = a;
}
"""

var _cinta: MeshInstance3D
var _mat: ShaderMaterial
var _anillos := []
var _t := 0.0
var _t_repique := -100.0

func _ready() -> void:
	_mat = ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = SOMBREADOR
	_mat.shader = sh
	_cinta = MeshInstance3D.new()
	_cinta.mesh = _malla_cinta()
	_cinta.material_override = _mat
	_cinta.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_cinta)
	var sh_a := Shader.new()
	sh_a.code = ANILLO
	for i in 4:
		var m := MeshInstance3D.new()
		var t := TorusMesh.new()
		t.inner_radius = 0.92
		t.outer_radius = 1.0
		t.rings = 48
		t.ring_segments = 4
		m.mesh = t
		var mat := ShaderMaterial.new()
		mat.shader = sh_a
		m.material_override = mat
		m.position = TORRE
		m.visible = false
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(m)
		_anillos.append(m)
	repicar()

func _curva(u: float) -> Vector3:
	var p := TORRE.lerp(PLAZA, u)
	p.y += sin(u * PI) * 46.0
	return p

## Cinta que mira hacia arriba a lo largo del arco (se ve desde la cámara del tour, que va por encima y al costado).
func _malla_cinta() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in SEGMENTOS:
		var u0 := float(i) / SEGMENTOS
		var u1 := float(i + 1) / SEGMENTOS
		var a := _curva(u0)
		var b := _curva(u1)
		var dir := (b - a).normalized()
		var lado := dir.cross(Vector3.UP).normalized() * ANCHO * 0.5
		var arriba := Vector3.UP * ANCHO * 0.5
		for par in [[lado, -lado], [arriba, -arriba]]:       # dos cintas en cruz: se ven de cualquier lado
			var l0: Vector3 = par[0]
			var l1: Vector3 = par[1]
			st.set_uv(Vector2(u0, 0)); st.add_vertex(a + l0)
			st.set_uv(Vector2(u0, 1)); st.add_vertex(a + l1)
			st.set_uv(Vector2(u1, 0)); st.add_vertex(b + l0)
			st.set_uv(Vector2(u1, 0)); st.add_vertex(b + l0)
			st.set_uv(Vector2(u0, 1)); st.add_vertex(a + l1)
			st.set_uv(Vector2(u1, 1)); st.add_vertex(b + l1)
	return st.commit()

## Otra tanda de ondas y otro trazo hacia la plaza.
func repicar() -> void:
	_t_repique = _t

func _process(dt: float) -> void:
	_t += dt
	var desde := _t - _t_repique
	_mat.set_shader_parameter("avance", clampf(desde / 7.0, 0.0, 1.08))
	_mat.set_shader_parameter("brillo", clampf(1.4 - maxf(desde - 9.0, 0.0) * 0.12, 0.35, 1.4))
	for i in _anillos.size():
		var m: MeshInstance3D = _anillos[i]
		var vida := fmod(desde + i * 0.9, 3.6) / 3.6
		m.visible = desde > i * 0.9 and desde < 22.0
		m.scale = Vector3.ONE * (2.0 + vida * 42.0)
		(m.material_override as ShaderMaterial).set_shader_parameter("vida", vida)
