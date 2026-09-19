# Las pruebas, y cómo correrlas sin perder la tarde

Son más de cuatrocientas y casi todas llevan un emulador de verdad detrás, así
que **la suite no es lenta porque calcule mucho: es lenta porque espera**. De
sus cincuenta minutos en serie, sólo unos cinco son esperas fijas escritas en
las pruebas; el resto es el emulador cargando cintas, dibujando láminas y
jugando.

Esperar es justo lo que se puede hacer de varios en varios.

## Las dos órdenes

```
pytest -n 4 --dist loadgroup -m "not serial"     # el grueso, en paralelo
pytest -m serial -m "not mirror"                 # las que miden tiempo
pytest -m mirror                                 # el espejo, a mano
```

Las dos primeras son la puerta: unos doce minutos y otros catorce. **El espejo
no está en la puerta**: juega tres aventuras enteras --MegaCorp, Los pájaros de
Bangkok y El Quijote II-- en dos máquinas a la vez, tarda un cuarto de hora
largo, y su trabajo es **buscar** y no vigilar. Se lanza cuando se ha tocado
el intérprete, que es cuando puede encontrar algo --y encuentra: el ajuste de
líneas, el `GET` de un objeto que no existe y la regla de cómo se parten las
tiradas de espacios salieron de ahí--.

Cuatro y no seis, aunque la máquina tenga ocho núcleos: con seis emuladores a
la vez el grueso baja a nueve minutos pero empiezan a fallar pruebas **distintas
en cada vuelta**, que es la peor clase de fallo. Lo que se les queda corto es el
plazo de espera, no el intérprete. Con cuatro son once minutos y salen siempre
igual, y once minutos ciertos valen más que nueve dudosos.

### Los plazos, que es lo que de verdad fallaba

Lo primero que hicieron cuatro trabajadores fue tirar cuatro pruebas por
vuelta, **distintas cada vez**, que es la peor clase de fallo: parece el
intérprete y es el reloj. Antes de alargar plazos a ojo se midió cuánto corre
de verdad una máquina emulada aquí, preguntándole su propio contador de ciclos:

| emuladores a la vez | velocidad |
|---|---|
| uno | 0,96 veces un Spectrum de verdad |
| dos | 0,71 |
| cuatro | 0,58 |

O sea que con cuatro **todo tarda 1,7 veces más**, no cuatro. Un trabajo de
quince segundos pide veintiséis, y el plazo de veinticinco que tenía esperar a
que el PCW acabara de dibujar era una moneda al aire.

Así que **todo plazo de espera se estira con la compañía que tenga la
máquina**: `emulator.longer()` lo hace, y por ahí pasan el arranque, el
`wait_for` de `emulator.py` --y con él `start_code`-- y el `wait_screen` de los
doce módulos que miran la pantalla. Reproducir el fallo a propósito --los
cuatro módulos peores, cuatro máquinas distintas a la vez-- cuesta tres minutos
y medio en vez de doce, y es lo que hay que hacer antes de tocar un plazo.

Dos esperas siguen siendo del reloj nuestro porque no hay nada que mirar:
arrancar una ROM y pedirle el disco a un PCW. Las dos crecen igual.

Y una cosa que no se arregla con plazos: **cargar de cinta pasa en el tiempo de
la máquina**, así que la del Amstrad se va con las que miden tiempo.

La primera es la de todos los días. La segunda son las que **miden tiempo**
--cuánto tarda una tecla en repetirse, cuánto aguanta una orden la máquina-- y
que una máquina ocupada hace fallar; sus propios comentarios ya lo decían antes
de que existiera esto.

## Lo que había que arreglar para poder

Dos cosas se compartían, y las dos están resueltas en `tests/conftest.py` y en
`tests/emulator.py`:

- **El puerto del emulador.** Un ZEsarUX contesta en el 10000, y dos sesiones en
  un puerto hablan con la misma máquina. Cada trabajador toma su puerto del
  nombre que le da xdist --`gw0`, `gw1`...--, así que el 10000, el 10001 y
  siguientes.
- **Lo que escribe el ensamblador.** Dos pruebas que construyen
  `z80/spectrum/game.sna` se pisan a mitad de la construcción. Las que escriben
  los mismos ficheros van en un grupo, y `--dist loadgroup` mantiene cada grupo
  dentro de un trabajador. El mapa está en `conftest.py` y va **por lo que cada
  prueba construye**, no por lo que prueba: por eso `test_markers_z80` y
  `test_tape_z80` están juntas.

Un detalle que costó encontrar: la marca del grupo hay que ponerla **antes** que
la de xdist, con `@pytest.hookimpl(tryfirst=True)`. Puesta después, xdist ya ha
repartido y los ocho casos de un módulo acaban en dos trabajadores distintos,
construyendo los dos sobre el mismo fichero. Se ve en el reparto:

```
pytest tests/test_parser_z80.py -n 2 --dist loadgroup -v | grep -o "gw[0-9]" | sort | uniq -c
```

Ocho en uno solo está bien; seis y siete repartidos es que el grupo no se está
aplicando.

## La regla: un fallo en paralelo no se cree hasta repetirlo a solas

Con los plazos estirados quedan una o dos pruebas por vuelta que fallan por la
compañía y no por el código, y no siempre las mismas. Así que:

```
pytest tests/la_que_fallo.py -q        # a solas, un minuto
```

Si pasa, era la compañía. Si falla, es de verdad y hay algo que arreglar. Un
minuto de comprobación vale más que subir un plazo a ojo, y mucho más que
creerse un fallo que no existe --o, peor, no creerse uno que sí--.

## Si una vuelta se corta a medias

Un emulador huérfano se queda con el puerto, y la vuelta siguiente falla en
todo lo que toque ese puerto con «something is already listening on port
10000». No es un fallo del intérprete ni de las pruebas: es basura de la
anterior. Se mira y se limpia así:

```
powershell -c "Get-Process zesarux -ErrorAction SilentlyContinue | Select Id,StartTime"
powershell -c "Get-Process zesarux -ErrorAction SilentlyContinue | Stop-Process -Force"
```

Conviene hacerlo siempre después de cortar una suite a mano.

## Mientras se trabaja

Lo caro no es la suite: es lanzarla entera después de cada cambio. El orden
que funciona es

1. la prueba dirigida de lo que se acaba de tocar --un fichero, medio minuto--;
2. las de su área, en paralelo, cuando el cambio toca algo común;
3. **la suite entera una sola vez, antes de comitear**.

Y qué toca qué, que es lo que evita adivinar:

| lo que se toca | lo que hay que correr |
|---|---|
| `common/parser.asm`, `common/config.asm` | `test_parser_z80`, `test_statements_z80`, `test_markers_z80`, `test_interpreter` |
| `common/opcodes.asm`, `common/conditions.asm` | `test_conditions_z80`, `test_opcodes_z80`, `test_markers_z80`, `test_game_z80` |
| `common/loop.asm` | `test_markers_z80`, `test_game_*` de las cinco máquinas |
| `common/keys.asm`, un `keyboard.asm` | `test_keyboard_*`, `test_statements_z80` |
| `common/textout.asm`, una `screen.asm` | `test_text_*`, `test_textmode_*`, `test_wrapping_z80` |
| dibujo (`draw`, `fill`, `shapes`, `picture`) | `test_graphics_*`, `test_all_pictures*` |
| cinta, disco, `media.py` | `test_tape_*`, `test_media_*`, `test_save_*` |
| `regac/` a secas, sin tocar `z80/` | las de Python, que son segundos |
