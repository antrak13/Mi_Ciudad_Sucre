# Universal Animation Library Standard

Edición gratuita de Quaternius para Godot, distribuida bajo CC0. [Godot Asset Store](https://store.godotengine.org/asset/quaternius/universal-animation-library/)

Godot importa `ual_estandar.glb` como `AnimationLibrary` con 46 entradas, incluida la pose `A_TPose`. `mapa_humanoide.tres` asigna los 53 huesos de origen al perfil humanoide de Godot. Las pistas apuntan a `%GeneralSkeleton`.

Para usarla en un personaje, importa su esqueleto con su propio `BoneMap` y el perfil `SkeletonProfileHumanoid`. Carga la biblioteca en su `AnimationPlayer` con el nodo de esqueleto importado como `GeneralSkeleton`. [Retargeting en Godot](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)

`Walk`, `Walk_Formal` y `Jog_Fwd` son ciclos en el sitio. El desplazamiento puede venir del controlador del personaje. La biblioteca también incluye `Idle`, `Idle_Talking` y `Sitting_Idle`.
