"""El campus en Django, mientras convive con FastAPI.

Es un paquete aparte de `app/` a propósito: durante la migración FastAPI
sigue intacto y atiende todo lo que no se haya pasado, y cada router de
`app/rutas/` va a tener acá su gemelo para revisarlos lado a lado.

Qué hay
-------
settings.py     Django sin base de datos ni módulos de `contrib`
urls.py         las rutas migradas; en la fase 0 no hay ninguna
vistas.py       la respuesta para una ruta que no existe
adaptadores.py  lo que hace falta para que una vista de Django conteste
                exactamente lo mismo que su ruta de FastAPI

Qué **no** hay, y por qué
-------------------------
Ni middlewares ni manejadores de error propios. Las peticiones que van a
Django pasan por la **misma** pila que las de FastAPI —el freno, la
auditoría, el guardado, el CORS y el formato de los errores—, armada en
`despachador.py` con la configuración del propio FastAPI. Reimplementarlos
acá sería tener dos copias que tarde o temprano dejan de decir lo mismo.
"""
