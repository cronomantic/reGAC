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
pytest -m "serial and not mirror"                # las que miden tiempo
pytest -m mirror                                 # el espejo, a mano
```

Las dos primeras son la puerta: unos doce minutos y otros once. **Las dos
condiciones de la segunda van en una sola expresión**, y no en dos `-m`:
pytest se queda con el último y tira el primero, de modo que
`-m serial -m "not mirror"` corre **la suite entera** en serie. Estuvo así un
tiempo sin que fallara nada por ello: sólo tardaba cuarenta y nueve minutos en
vez de once, repitiendo en serie lo que la primera orden acababa de hacer en
paralelo. La puerta pasa de una hora larga a poco más de veinte minutos.

**El espejo no está en la puerta**: juega tres aventuras enteras --MegaCorp,
Los pájaros de Bangkok y El Quijote II-- en dos máquinas a la vez, tarda un
cuarto de hora largo, y su trabajo es **buscar** y no vigilar. Se lanza cuando
se ha tocado el intérprete, que es cuando puede encontrar algo --y encuentra:
el ajuste de líneas, el `GET` de un objeto que no existe y la regla de cómo se
parten las tiradas de espacios salieron de ahí--.

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

**Y una prueba que no cabía en ningún grupo.** `test_project` corre
`regac make` para todas las máquinas, y `regac make` construye **donde está
`regac`**, en `z80/`: los mismos `game.bin` que cada grupo guarda para sí. El
mapa lo dejaba sin grupo, y así pasó cientos de vueltas hasta que un día cayó
al lado de `cpc-game`: `test_low_cpc` leyó un intérprete de **cero bytes**,
el que sjasmplus estaba escribiendo en ese momento para `test_project`. A
solas pasaba.

Un grupo no sirve para una prueba que pisa los de todos, así que va con las
de serie, donde no corre nada a su lado. No mide tiempo, pero la segunda
orden es la única en que corre sola, y le cuesta quince segundos.

**La comprobación, para la próxima que se añada**: una prueba que ensambla en
`z80/` o corre `regac make` va en el grupo de lo que construye, o en serie si
construye lo de varios. Las que construyen en su carpeta temporal —como la
del PC, que ensambla con NASM en `tmp_path`— no necesitan nada.

## La regla: un fallo en paralelo no se cree hasta repetirlo a solas

Con los plazos estirados quedan una o dos pruebas por vuelta que fallan por la
compañía y no por el código, y no siempre las mismas. Así que:

```
pytest tests/la_que_fallo.py -q        # a solas, un minuto
```

Si pasa, era la compañía. Si falla, es de verdad y hay algo que arreglar. Un
minuto de comprobación vale más que subir un plazo a ojo, y mucho más que
creerse un fallo que no existe --o, peor, no creerse uno que sí--.

**Y al revés también cuenta.** Ocho pruebas de partida tecleaban en cuanto
asomaban los doce primeros caracteres de la descripción, que no es lo mismo
que esperar a que el turno acabe: el resto de la descripción sigue saliendo, y
una tecla pulsada mientras tanto no va a ninguna parte, porque el intérprete
mira el teclado sólo mientras pregunta --que es lo que hace el original y lo
que ve una persona--. Se perdía la primera letra de la orden, y que se
perdiera o no dependía de lo deprisa que sondeara la prueba: **en paralelo no
pasaba nunca y a solas pasaba siempre**, de modo que parecía culpa del
intérprete de una máquina concreta.

Y **ver el prompt tampoco es que te estén preguntando**: imprimirlo y ponerse
a mirar el teclado no son el mismo instante, y una tecla pulsada entre los dos
no la oye nadie. Eso salía como `>>>EBECA` --la erre de `REBECA` perdida-- en
la máquina más lenta, dos veces en sendas vueltas. Así que `emulator.asked`
pide ver la misma pantalla **dos veces seguidas** con el prompt al final: una
vuelta entera del sondeo, que es de sobra para que la máquina pase de lo uno a
lo otro, y no cuesta nada cuando el prompt ya llevaba ahí un rato.

### El fondo de todo esto: los plazos crecían y las esperas no

Persiguiendo las de arriba una por una salió el patrón. La batería lleva
tiempo haciendo crecer sus **plazos** con `emulator.longer` --que es la
identidad con un trabajador y multiplica por 2,2 con cuatro, que es
aproximadamente lo que se frenan las máquinas: 0,58 de una máquina para sí--
pero no sus **esperas**. Y las esperas son las que duelen:

> un plazo que se queda corto sólo hace la prueba más lenta; **una espera que
> se queda corta significa que a la máquina se le teclea, se le escribe o se
> le lee antes de estar lista**, y de eso salen una pantalla en blanco, una
> primera letra perdida o una lámina con un byte torcido.

Eran **71 esperas en 40 ficheros**, todas de la forma «deja que la máquina
arranque». Ahora crecen con la compañía. A solas no cambia nada; con cuatro,
la puerta paga algo más de tiempo a cambio de no perseguir fantasmas.

**Menos tres, y el porqué merece quedarse escrito.** Escalarlas todas rompió
en firme --las dos vueltas, no una-- exactamente las tres que arrancan con una
**cinta metida y corriendo**: dos de `test_save_z80` y una de
`test_save_next`. Ninguna de las que sólo graban. Una espera que crece no le
da más tiempo a la máquina si lo que hay al otro lado es una cinta: **la cinta
no espera**, y el bloque ya ha pasado cuando por fin se mira. La regla, dicha
entera:

> una espera crece con la compañía cuando lo que espera es que **la máquina**
> esté lista; no crece cuando lo que corre al otro lado va por su cuenta.

**Y luego resultó que esas tres no tenían que esperar por el reloj en
absoluto.** Se quedaron como estaban, con un `sleep(3.0)` a pelo, y siguieron
cayendo de vez en cuando --en una vuelta, las tres a la vez-- con el mismo
«nothing ever came off the tape». Lo que esperaban era que la ROM acabara de
arrancar, y eso **sí** se puede mirar: el 48 termina en su bucle de órdenes,
entre `$1200` y `$16FF`, y el Next acaba en el mismo sitio. Medido, arrancar
lleva entre **2,35 y 2,71 segundos** contra un salto de tres, y los tres se
gastaban tanto si habían hecho falta dos como cuatro.

Aquí cada décima cuenta doble, porque es cinta pasando: ocho vueltas de cada
manera dieron **siete de ocho durmiendo y ocho de ocho mirando**, y la prueba
entera bajó de setenta segundos a veintidós. Es `Session.wait_in`, y la
moraleja es la de siempre dicha del revés: si una espera no se puede escalar,
lo que hay que preguntarse no es cuánto dormir sino **qué mirar**.

**Y una instantánea puede no entrar.** `test_wrapping_z80` salía con la
pantalla **en blanco** en tres vueltas enteras de cada cuatro, un texto
distinto cada vez, y pasaba a solas y con media carga. Cuando un `smartload`
no coge, lo que queda es una máquina a la que nunca se le preguntó nada, y
todo lo que la prueba comprueba después se lee como si el intérprete hubiera
colocado mal el texto --que es la peor manera de que se lea--. Ahora la
instantánea **se vuelve a meter** si la aventura no llegó a preguntar, igual
que un build que no arranca; y si aun así no arranca, lo que se dice es **dónde
estaba el procesador**, que es el único número que separa las dos mitades: por
debajo de `$4000` es la ROM, y significa que la carga nunca entró; por encima
es el intérprete corriendo y entonces lo que está mal es cómo se lee la
pantalla.

De paso, la espera de dos segundos de `ends()` no estaba escalada. Ésa se
queda esperando por el reloj y no mirando, porque una aventura que se para
sola puede no preguntar nunca --que es justo lo que esa función comprueba--,
pero ahora crece con la compañía como todas las demás.

**Y la música sí sonaba.** `test_game_music_z80` fallaba la mitad de las veces
incluso a solas, diciendo que el reproductor no estaba leyendo su melodía, y
eso pone en duda una función entera. No era verdad: mirando el puntero del
reproductor durante diez segundos en vez de una sola vez, en cinco vueltas de
cinco **acaba dentro del buffer y recorre la melodía** --seis o siete valores
distintos--, y la única que empezó en cero se puso buena **un cuarto de
segundo después**. La bandera es nuestra y la pone el intérprete al pedir la
melodía; el puntero lo mueve el reproductor en su primer paso por la
interrupción. No son el mismo instante. Las tres pruebas que lo miraban de
una ojeada --Spectrum, Amstrad y Next-- ahora lo esperan.

La del Quijote en un 464 tenía la misma de otra forma: pulsaba espacio cuatro
veces nada más arrancar, para pasar la portada, y si la portada aún estaba
saliendo se perdían las cuatro --y entonces el juego se quedaba esperando una
tecla que ya no iba a llegar, hasta agotar los dos minutos de plazo--. Ahora
espera a la última palabra del título antes de pulsar.

### El teclado del PCW: una tecla que se aguanta un tiempo que no es el suyo

Nueve pruebas, y **entre una y tres fallaban cada vuelta, cambiando de prueba
cada vez**. A solas pasaban; en fila no. Y la excusa fácil era mentira: el
binario y el `.rgac` eran idénticos byte a byte a los de la vuelta verde
anterior, así que no era el build.

Eran tres cosas, todas la misma en el fondo —**adivinar en vez de esperar**—:

1. **Se sabe que arrancó, no que está mirando.** `ready_flag` se pone una vez,
   y las teclas se mandaban a continuación. El bucle escribe `raw_row` en cada
   vuelta, así que ahora se le mete un valor nuestro y se espera a que lo
   quite: eso sí es el bucle contestando. Es `wait_for_change`, el revés de
   `wait_for`.
2. **Una tecla aguantada 0,06 s de los nuestros no son 0,06 s de la máquina.**
   Este emulador no lleva el tiempo del PCW, de modo que con el anfitrión
   ocupado el mismo `sleep` compra menos ciclos, y una tecla que dura menos de
   una pasada del teclado **no la ve nadie**. Ahora se cuenta en ciclos suyos,
   con `get-tstates-partial`, cuatro tramas por tecla.
3. **Saltar no es haber llegado.** `session.jump(read_a_line)` y teclear
   0,3 s después tiraba las primeras teclas cuando el salto no había caído.
   Todo lo que hay por encima de `read_a_line` en el fuente son esas entradas
   y lo que llaman, y por debajo está el bucle del teclado, así que un
   contador de programa pasado de esa dirección es el salto ya dado.

Y una cuarta, de las de leerse dos veces: el reintento de tres vueltas que
`test_a_whole_line_is_read_and_shown` ya tenía **no servía para nada**, porque
el `assert` de «la línea no terminó nunca» estaba dentro del `try` y salía
disparado del bucle en la primera. Un reintento que sólo cubre el caso bueno
no es un reintento.

**Quedó una sin arreglar, y volvió una vuelta después**: la que mide cada
cuántas tramas se repite una tecla aguantada. Decía «only 0 frames were
counted», que es un número que no se parece a un error de medida sino a que no
había nada que medir, y así era. Al ver una tecla nueva el contador se pone a
`KEY_DELAY` —treinta y cinco tramas, y es de `common/keys.asm`, igual en todas
las máquinas— y baja una por trama; la prueba pulsaba,
dormía un vigésimo de segundo y empezaba a mirar, y si la pulsación aún no
había llegado el contador valía cero y la medición se cortaba antes de
empezar. Ahora espera a **verlo contando** —por encima de veinte, que deja de
sobra las diez tramas que quiere— y sólo entonces pone el contador de ciclos a
cero. El contador pasa por ahí una sola vez, porque al llegar abajo se queda
en `KEY_EVERY` y ya no vuelve a subir, así que no hay forma de confundirse de
vuelta.

**Y la vuelta siguiente lo dijo otra vez, en el Amstrad.** Esa prueba está
escrita tres veces —Amstrad, MSX y PCW— con el mismo patrón, y arreglar una
sola es no arreglar ninguna. La lección es más general que el fallo:

> cuando una prueba de máquina falla por cómo espera, **lo primero es buscar
> el mismo trozo en las otras máquinas**, porque estos ficheros se escribieron
> copiando el de al lado y el defecto viaja con la copia.

Un `grep` por la línea que falla —aquí `key_repeat`— sale más barato que dos
vueltas de diez minutos.

### Medir con la regla que no se mueve

La prueba del canal de ruido del AY cayó **dos veces en dos puertas
distintas**, y las dos por el mismo motivo de fondo: estaba construida sobre
una medida inestable. Cuatro vueltas del mismo build en la misma máquina:

| | tramos distintos | cambios de valor |
|---|---|---|
| tono | 18 - 21 | 7243 - 9236 |
| ruido | 38 - 45 | **7373 - 12337** |
| ambos | 31 - 44 | 11351 - 14088 |

**Los tramos son firmes y los cambios de valor no.** La cuenta de cambios de
un siseo se mueve dos tercios y se solapa con la del tono, así que cualquier
afirmación apoyada en ella falla el día que al siseo le toca medir alto —que
es lo que pasó, con 9934—.

Lo que hice mal las dos veces fue lo mismo: **retocar el umbral en vez de
medir la dispersión**. La primera vez bajé una exigencia y subí otra; la
segunda, ya con los cuatro pares de números delante, se vio que una de las dos
reglas no servía para nada y que la otra valía para los dos casos.

> antes de mover un umbral, mídelo cuatro veces. Si lo que se mueve es la
> medida y no el código, el umbral no es el problema.

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
