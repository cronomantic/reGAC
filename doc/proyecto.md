# El fichero de proyecto

Una aventura no dice nada de bancos, ni de pantallas de carga, ni de a qué
tamaño se dibujan sus láminas. Eso son decisiones sobre **a dónde va**, no
sobre lo que es, y estaban repartidas por una docena de líneas de comando.
Ahora van juntas en un fichero, y un solo comando construye todo lo que ese
fichero nombre:

    python -m regac make megacorp.toml

Es el mismo principio que separa el fuente `.gac` de la máquina destino, y que
ya estaba escrito en [`formato-fuente.md`](formato-fuente.md): *lo que es de la
aventura va en el fuente; lo que es de la máquina va en el fichero de
proyecto*.

## Cómo es

TOML, que lee la biblioteca estándar de Python desde la 3.11 y no obliga a
instalar nada:

    name   = "megacorp"          # cómo se llaman los medios que salen
    source = "megacorp.json"     # la aventura: .json hoy, .gac también
    output = "salida"            # dónde se dejan, una carpeta por máquina

    [targets.spectrum48]

    [targets.spectrum128]
    screen = "carga.scr"

    [targets.plus3]
    screen = "carga.scr"

    [targets.cpc]
    screen = "carga.cpc"

    [targets.pcw]
    screen = "carga.pcw"
    scale  = [2, 1]

Las rutas se cuentan desde el propio fichero de proyecto. Las máquinas se
llaman `spectrum48`, `spectrum128`, `plus3`, `cpc`, `msx` y `pcw`.

## Las perillas

| clave | qué dice | por defecto |
|---|---|---|
| `banks` | tamaño de banco: `none`, `8k` o `16k` | lo que esa máquina suele usar |
| `screen` | el volcado de pantalla que se ve mientras carga | ninguna |
| `scale` | a cuántos píxeles de la máquina sale un punto de la lámina | 1, y 2 en el PCW |
| `music-buffer` | bytes reservados para la melodía que suena | 0 |

Un nombre que no esté en esa lista es un error y se dice, en vez de construir
otra cosa en silencio; lo mismo con una máquina que no existe, o con una escala
que esa máquina no sabe dibujar.

**La escala va a las dos puntas.** No es una etiqueta: el intérprete se
ensambla con ella (`PICTURE_SCALE`) y el renderizador de referencia recibe el
mismo número, así que la prueba que compara uno contra otro sigue valiendo. Hoy
sólo el PCW tiene de dónde elegir —uno o dos puntos de ancho—, porque es la
única máquina cuya pantalla es más ancha que la lámina; las demás dibujan a
tamaño natural y decirles otra cosa es un error.

**La pantalla de carga se comprueba**: si no mide lo que mide la pantalla de esa
máquina, protesta y no escribe nada. Qué es cada una está en
[`binario.md`](binario.md).

## Lo que *no* va aquí

Nada que decida la máquina por sí misma. En qué páginas de un Spectrum caen los
bancos, dónde carga el intérprete, cuánto ocupa un volcado de pantalla, qué
fichero de cada árbol hay que ensamblar: eso son hechos de la máquina y viven
en la tabla de `regac/project.py` o en el fuente de la propia máquina. El
fichero de proyecto elige entre lo que la máquina ofrece; no la reinventa.

## Qué hace por cada máquina

1. **La base de datos** que esa máquina lee, con los bancos que se le pidan, y
   el `.inc` que el ensamblador necesita para repartirla.
2. **La pantalla de carga**, si la hay: comprobada, y puesta donde haga falta
   —junto al fuente cuando el medio lo escribe el ensamblador, o entregada a
   `release` cuando lo escribe él—.
3. **El intérprete**, ensamblado con lo que el proyecto haya dicho.
4. **El medio**, en `salida/<máquina>/`. Cada máquina en su carpeta, que es
   necesario: todas llaman igual a sus ficheros.

Con `-t` se construye una sola:

    python -m regac make megacorp.toml -t pcw

## Lo que sale

    cpc          -> cpc\megacorp.dsk, cpc\megacorp.cdt
    pcw          -> pcw\megacorp.dsk
    plus3        -> plus3\megacorp.dsk
    spectrum128  -> spectrum128\megacorp.tap
    spectrum48   -> spectrum48\megacorp.tap
