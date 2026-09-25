# Pendiente

Estado a 15 de septiembre de 2026, para retomarlo sin tener que reconstruir el
contexto.

## Los gráficos, cerrados

Las 196 láminas de las ocho aventuras salen idénticas a la referencia, y las
cuatro que fallaban se han comparado además contra la pantalla que deja el GAC
original, byte a byte, que es la única prueba que vale de verdad.

La más lenta son 4,5 segundos de Spectrum real, dentro del tope de cuatro o
cinco. Se llegó por tres sitios: el salto de byte entero en la búsqueda de
extremos, recordar la última lámina encontrada, y llevar el puntero y la cuenta
de órdenes en registros en lugar de en memoria. Está contado en `graficos.md`.

Dos cosas que conviene no olvidar. El emulador de esta máquina corre a 2,03
MHz, no a 3,5, así que los segundos de reloj engañan: hay que medir con el
contador de ciclos del Z80, como hace `tests/test_all_pictures.py`. Y esa
prueba tarda doce minutos, así que sólo corre con `REGAC_SLOW=1`.

## Del intérprete

Los cuatro opcodes que faltaban ya están. `HOLD` espera las cincuentavas de
segundo que le digan o hasta que se toque una tecla, lo que antes pase; lo que
estuviera pulsado al empezar no cuenta, o el mismo enter que cerró la orden
acabaría con la espera. `QUIT` pregunta antes, con el mensaje 244, y sólo se va
si la respuesta es sí; vale S, SI, Y o YES, comparados en los códigos de la
aventura y no en letras.

`SAVE` y `LOAD` usan la cinta a través de la ROM, un bloque de datos sin
cabecera delante. Lo que viaja es sólo la partida, de `vm_state` a
`vm_state_end`: la aventura no cambia nunca, así que no hace falta guardarla.

El original no lo hacía así, y aquí decía que sí: está leído en su código
(ver «Lo que hace el `LOAD` del original», más abajo). Pide un nombre y
graba un fichero CODE normal, con cabecera, de 768 bytes desde `$A1FD`, que es
su estado de partida. Lo de guardar de `$5DC0` al final de la base de datos,
que también se decía aquí, es el **editor** grabando la aventura entera, no el
`SAVE` del juego. Nuestro formato es distinto a propósito —y en un disco pedir
un nombre no tendría sentido—, así que eso se queda como está.

~~De esos dos, en el Spectrum, no hay prueba automática: el emulador no sabe
grabar lo que sale por la cinta.~~ **Sí sabe**, y ya la hay. Lo que no puede
grabar es la cinta que suena; la otra, la de verdad, entra y sale con `--tape`
y `--outtape`, y el emulador engancha las dos rutinas de la ROM. Así que
[`test_save_z80.py`](../tests/test_save_z80.py) mira las dos direcciones
contra el fichero: lo que `SAVE` saca se lee de la cinta donde se escribió
—bloque, marca y suma—, lo que `LOAD` lee viene de una cinta escrita aquí, y
la vuelta entera, que es grabar en una cinta y volver a cargar de esa misma
cinta. Cada mitad por su lado sólo se pone de acuerdo con lo que la prueba
cree que es un bloque; las dos juntas se ponen de acuerdo entre ellas.

Una cosa que costó y conviene saber: **cargar una instantánea saca la cinta de
la máquina**. Con la instantánea puesta como siempre, la ROM se quedaba
esperando una cinta que ya no estaba. El banco de pruebas se escribe en memoria
y se arranca, y la cinta se queda donde estaba.

Partir la línea en varias órdenes ya está, y de dónde salen los separadores
costó dos vueltas. La primera fue mirar la base de datos: los ocho signos de
puntuación están ahí —fijos e iguales en las ocho aventuras, hasta el punto de
que el decompilador de referencia los usa como firma para reconocer un GAC— y
**ninguna lista de palabras**. De ahí se concluyó que las palabras `then` y
`and` que traía todo lo decompilado se las inventaba `deGAC`, y se quitaron.

La conclusión estaba mal, y el fallo fue de método: que no estén en la base de
datos no quiere decir que no estén en el intérprete. Medido en la máquina, en
MegaCorp, que es española y no tiene declarado nada:

| lo tecleado | lo que hace el original |
|---|---|
| `XYZY SUR` | se va al sur, sin quejarse |
| `XYZZY Y SUR` | se va al sur, sin quejarse |
| `XYZZY THEN SUR` | **«Repita la orden.»** y se va al sur |
| `XYZZY AND SUR` | **«Repita la orden.»** y se va al sur |

O sea que **THEN y AND son del intérprete** del original, están en las ocho
aventuras aunque ninguna las guarde, y la Y castellana no separa nada.

Y ahí hubo una decisión, que es de Sergio: **no repetir el a capón**. Tenemos
intérprete propio, así que las palabras que parten una orden las dice la
aventura y no el intérprete. El nuestro **no sabe ninguna**; el que las pone
es `deGAC`, que escribe `THEN` y `AND` en la base de datos de toda aventura
que lee. Con eso se tienen las dos cosas: un original recompilado parte las
órdenes donde siempre, y una aventura escrita de ahora en adelante dice las
suyas —`sep "y" "luego"`— sin cargar con dos palabras inglesas que no quiere.

Se comparan como palabra entera, así que `ANDAR` no es `AND` con cola, y se
guardan sin marcas y en mayúsculas, que es como llegan de estos teclados. Hay
prueba de cada cosa en [`test_statements_z80.py`](../tests/test_statements_z80.py)
y en [`test_interpreter.py`](../tests/test_interpreter.py), incluida una que
mira que las aventuras decompiladas las traigan: una que las perdiera dejaría
de partir órdenes y no se enteraría nadie.

**Las que ya estuvieran decompiladas hay que volver a pasarlas por `deGAC`**,
porque el campo se escribía vacío. Hecho: las ocho de `snapshots/` traen
`["THEN", "AND"]`.

Para que eso sirva de algo hubo que enseñar al teclado a dar los signos, que
en el Spectrum piden símbolo y otra tecla a la vez. De paso se arregló que
mayúsculas con cero, que es el borrado, no funcionaba: el rastreo devolvía la
tecla de mayúsculas y se quedaba ahí.

## Las máquinas

En Python están modeladas Spectrum, Sam Coupé, Next, MSX1, MSX2, Amstrad y
PCW. En Z80 están el Spectrum y el Amstrad CPC, los dos enteros, el Spectrum de
128K con la base de datos repartida en bancos, **el PCW entero** —arranca solo
de un disco que se hace con `release`, dibuja láminas idénticas a las de la
referencia, imprime, lee el teclado y guarda la partida en un fichero de
verdad—, **el MSX1 entero**, que carga de cinta, y **el Spectrum Next**, que se
entrega en un `.nex` que escribe el propio ensamblador.

Y todos se entregan en el medio que les toca, con su cargador: cinta para el
Spectrum de 48 y el de 128, disco y cinta para el Amstrad, disco para el +3,
disco que arranca solo para el PCW y cinta para el MSX. El +3 los lleva además
con la base de datos repartida en bancos, con un cargador en código máquina que
se los pide a +3DOS. Cómo está hecho cada uno está en `binario.md`.

### Los bancos, que ya se usan

El formato los llevaba desde el principio y no los leía nadie. Ahora sí: el
intérprete pide una sección, y si vive en un banco la máquina lo trae a su
ventana. Cómo está hecho y qué cuidado hay que tener con los punteros que
alguien se guarda está en `binario.md`; lo que importa aquí es que el 48K y el
Amstrad no pagan nada por ello, porque una máquina sin bancos se queda con un
`db_page` que sólo retorna.

Hay una prueba que lo demuestra de verdad, no sólo que arranca: una aventura
engordada hasta que el texto y las láminas no caben en el mismo banco, jugada
en un 128, con la lámina de la pantalla comparada byte a byte contra el
renderizador de referencia. Para llegar a ella hubo que tapar antes un agujero
que llevaba tiempo ahí sin que nadie lo viera: **el juego no dibujaba**.
`describe_location` imprimía el texto del cuarto y nadie llamaba nunca a
`draw_picture`; el intérprete de láminas estaba entero y probado, pero suelto.
En el Spectrum ni siquiera se ensamblaba dentro del juego.

### El Amstrad, con su cinta y su disco

Dibuja, escribe, lee el teclado y ya graba y carga, así que juega de principio
a fin. Y se entrega como se entregaba entonces: un disco que arranca con
`RUN"JUEGO` y una cinta que arranca con `RUN"`, las dos con su cargador en
BASIC delante. Cómo está hecho está en `binario.md`.

La cinta va por el firmware, igual que en el Spectrum va por la ROM: un bloque
de datos sin cabecera delante, escrito con CAS WRITE ($BC9E) y leído con CAS
READ ($BCA1). Lo que viaja es sólo la partida, de `vm_state` a `vm_state_end`,
como allí.

No hizo falta paginar nada, que era lo que parecía el problema. Las entradas
del salto del firmware no son un salto: son un reinicio, `CF` más la
dirección, o sea `RST 1`, que trae la ROM baja mientras dura la rutina aunque
nosotros corramos con las dos fuera. Lo que sí hay que hacer al volver es
recoger la máquina, porque el firmware la deja a su gusto: interrupciones
apagadas otra vez, nuestro modo y las cuatro plumas de la lámina que está en
pantalla. Y funciona con las interrupciones apagadas de principio a fin, que
es como corre el intérprete; está medido, no supuesto.

Es cinta y no disco a propósito. Las trece entradas de casete que abren un
fichero con nombre son justo las que AMSDOS se queda para sí —en un 6128 las
trece están parcheadas a un `RST 3` al ROM de disco, se ve leyendo el salto en
$BC77— y todas piden dos kilobytes de memoria nuestra para trabajar. No hay
sitio: la base de datos llega a $ADAD y las variables del firmware empiezan en
$B100. CAS WRITE y CAS READ son las dos que el disco no toca, no piden
memoria, y son el par exacto de las del Spectrum.

Y de ésta sí hay prueba, que en el Spectrum no la había. El emulador sabe
reproducir una cinta pero no grabarla, así que cada sentido se mira por su
lado. Escribir se comprueba viendo que el firmware acepta el bloque, dice que
lo escribió y devuelve la máquina como estaba. Leer se comprueba contra una
cinta de verdad: el primer bloque de datos de la cinta de Megacorp, leído con
nuestra rutina y comparado byte a byte con los mismos bytes sacados de la
imagen `.cdt`, y los 256 salen iguales. Lo único que no se puede probar solo
es la ida y vuelta entera, grabar lo nuestro y volver a leerlo, porque el
emulador no graba.

De camino salió un fallo de los de mirar y no medir. `MODE_1` valía
%10001100, que es modo 0: los dos bits de abajo del registro son el modo y el
modo 1 es %01, así que lo que hay que sacar es %10001101. No lo cazaba ninguna
prueba porque todas leen la memoria de pantalla, y el modo no cambia lo que
hay escrito en ella, sólo cómo se ve; en la pantalla de verdad el juego salía
con los píxeles al doble de ancho. Se comprobó en la máquina, poniendo los dos
valores y mirando lo que sale, y lo confirma el arranque del propio firmware,
que lo primero que hace en $0000 es programar $89: modo 1 con la ROM baja
dentro.

El teclado sí tiene prueba, y lo de que el emulador perdiera teclas era cosa de
cómo se las mandábamos. Darle una cadena entera pierde letras; mandarle la
pulsación y la suelta por separado, que es lo que hace `type_keys`, no pierde
ninguna: de cinco teclas llegan cinco. Los números de tecla del emulador son
casi siempre el ASCII de lo que lleva impreso, salvo unos pocos, y el punto es
uno de ellos.

### Amstrad PCW, target nuevo

Merece la pena porque es Z80 y porque no se parece a ninguna de las otras, así
que obliga a que la separación entre intérprete y máquina sea real.

**Monocromo, y ya resuelto.** 720 por 256 píxeles y ni un color. Todo el
modelo de tinta, papel, brillo y parpadeo se queda sin sitio donde ir, y la
única manera de mostrar tonos es la trama: superficies tramadas por lo clara
que sea la tinta, contornos sólidos, y el brillo sin efecto ninguno. Era la
máquina que ponía a prueba de verdad que el intérprete de láminas no supiera
nada de color, y lo ha pasado: el dispositivo del PCW traduce los colores en
curso a niveles de luz y el intérprete no se entera.

**Memoria de sobra**, 256K o más en bloques de 16K, que encaja con el reparto
por bancos que ya tiene el formato binario. El reparto elegido deja una ranura
entera para la ventana de la base de datos, y las dos mitades de la pantalla se
turnan en otra.

**No hay AY.** Sólo un zumbador, así que toda la previsión de música que
condiciona el reparto de bancos no aplica aquí. La sección de música del
formato seguirá estando, vacía, y este destino no necesitará ni buffer
residente ni ranura propia.

**La pantalla, hecha.** No es un mapa de bits fijo: hay una *roller RAM* de 256
entradas, una por línea de barrido, y la máquina dibuja la línea que cada
entrada diga. Los puertos, comprobados en el emulador uno a uno:

| puerto | qué hace |
|---|---|
| $F0-$F3 | qué banco de 16K se ve en cada una de las cuatro ranuras |
| $F4 | el candado; a cero se pueden remapear |
| $F5 | dónde está la roller RAM: banco = valor>>5, desplazamiento = (valor&31)×512 |
| $F6 | por qué línea de la tabla empieza a pintar |
| $F7 | bit 6 enciende la pantalla, bit 7 la invierte |

Cada entrada son dos bytes: tres bits de banco, diez de bloque de dieciséis
bytes y tres de línea dentro del bloque. Y lo que hace que todo encaje: **una
línea son 720 bytes y no 90**, porque el vídeo lee de ocho en ocho — los ocho
píxeles de la columna `c` están en `base + 8c`. De ahí que la dirección de un
punto salga tan barata como en el Spectrum:

    dirección = base + fila*720 + 8*(x>>3) + (y&7)

La lámina va doblada en horizontal, 512 píxeles de los 720, centrada, y se
dobla **al poner el punto**, que es la regla que costó aprender en el Amstrad.
El cómo y el porqué de todo esto -- el reparto de memoria, la máscara de un
bit, los niveles de gris, el relleno de un byte por fila -- está en
[`graficos.md`](graficos.md); a cuántos píxeles sale un punto lo dice el
fichero de proyecto, y va a las dos puntas —el intérprete se ensambla con ese
número y la referencia lo recibe— así que la comparación entre los dos sigue
valiendo. Ver [`proyecto.md`](proyecto.md).

**Una advertencia sobre el banco de pruebas**: el emulador no vuelca la
pantalla del PCW. Sale negra siempre, incluso arrancando su propio CP/M y
habiendo escrito a mano en la memoria que la tabla señala. Por eso la
comprobación no es por imagen sino leyendo la memoria de pantalla y
comparándola contra el renderizador de referencia. Y para correr una prueba no
hace falta ni disco: un PCW sin disquete se queda en el cargador que le da el
teclado, con los cuatro bancos mapeados del 0 al 3, que es justo el estado en
que lo dejaría su propio sector de arranque, así que se escribe el bloque en
memoria y se apunta el procesador al principio.

**El teclado, medido.** No hay puerto que preguntar: el controlador del propio
teclado deja el estado de cada tecla en los dieciséis últimos bytes de los
primeros 64K de RAM — con nuestro mapa, de $FFF0 a $FFFF — y los escribe mire
alguien o no. **Un bit a uno significa tecla pulsada**, al revés que en el
Spectrum y el Amstrad. Las dos cosas salieron de tener una tecla apretada y
buscar qué byte de los 256K se movía.

Y la sorpresa: medida tecla a tecla, **la matriz es la del Amstrad CPC**. Todas
las letras, todos los dígitos, el espacio, la coma, el punto, el enter y la
mayúscula caen exactamente en el bit que tienen en el CPC. Los seis signos de
la fila tres no se pueden pulsar desde el teclado del anfitrión, así que se dan
por buenos los del CPC.

Un detalle que costó un susto: la tabla que lee el vídeo estaba puesta donde el
controlador escribe las teclas, y no lo notaba nadie porque esa tabla no se
vuelve a leer nunca. Ahora hay un `ASSERT` en el fuente que lo dice.

**Y ya juega.** El intérprete está montado, el `release -m pcw` hace el disco
—sector de arranque, pantalla de carga, intérprete, bancos y la partida vacía
esperando—, y la prueba lo enciende con ese disco dentro y teclea. Cómo está
hecho está en [`binario.md`](binario.md).

**Lo que queda de esta máquina**: nada urgente. El zumbador, si alguna vez hay
sonido.

**Arranca solo, y no hace falta CP/M.** Los juegos de PCW son autoarrancables
y el mecanismo es simple: la máquina **no tiene ROM**; al encender se trae un
cargador del controlador del teclado, lee el sector de la pista 0, cara 0,
registro 1 en $F000, suma sus 512 bytes y, si dan $FF, salta a $F010 con los
cuatro bancos mapeados del 0 al 3. Los dieciséis primeros bytes del sector son
la especificación del disco, que es justo la que ya escribe `dsk.py`, y por eso
el código empieza donde empieza.

De ahí en adelante no hay a quién pedirle nada: el sector maneja el PD765 él
mismo, que está en los puertos 0 y 1, con el motor en el $F8. Leer un sector
son nueve bytes de orden, los datos, y siete de respuesta.

Ya está hecho y probado: [`boot.asm`](../z80/pcw/boot.asm) arranca en un PCW
emulado, lee lo que va detrás del sector y lo ejecuta. La prueba lo comprueba
por memoria, no por pantalla, porque el emulador no devuelve la del PCW.

**Y las partidas**, que son lo que era el plan y salió tal cual: disco con
formato CP/M, el intérprete y sus bancos en un fichero, y la partida en un
fichero creado ya en la construcción, del tamaño justo. El intérprete escribe
sus sectores directamente, sin tocar directorio ni reserva de bloques, y aun
así la partida es un fichero de verdad que se puede copiar con las
herramientas de CP/M. El sistema de ficheros existe para la persona; el
intérprete sólo toca sectores que ya le dijeron cuáles son.

### Spectrum Next, en layer 2 y con la máquina llena

Juega de principio a fin: dibuja, imprime, lee el teclado —que es el del
Spectrum, así que es el mismo fichero—, entiende lo que se le teclea y graba y
carga partidas. Se entrega en un `.nex` que escribe `sjasmplus`, con su
pantalla de carga dentro, y se arranca como cualquier juego de Next.

**Layer 2**: un byte por píxel, dieciséis colores que son los del Spectrum
porque la paleta es nuestra, y ni un solo conflicto de atributos. Y es memoria
normal que lee el vídeo, así que no hay copia de pantalla ni nada que enviar al
acabar una lámina: se dibuja donde se ve, y `gfx_show` no hace nada.

De ahí salen las dos cosas propias de esta máquina.

**La ventana.** En 64K no caben la base de datos, el intérprete y los 48K de
layer 2, así que layer 2 se ve de dieciséis en dieciséis en $C000 —la mitad de
arriba de la lámina, la de abajo, o el texto— y qué trozo toca sale de la fila,
así que nada por encima de la suma de direcciones se entera. Dentro de un trozo
una línea son 256 bytes, con lo que un píxel es la fila en H y la columna en L:
más barato que la pantalla del propio Spectrum. El reparto entero está en
[`game.asm`](../z80/next/game.asm) y no sobra nada.

**La máscara.** Con color por píxel la lámina ya no dice dónde para un relleno
—en el Spectrum un píxel encendido es a la vez marca negra y pared—, así que al
lado se lleva una máscara de un bit por píxel con exactamente lo que tendría la
pantalla de un Spectrum. Va fila a fila, treinta y dos bytes por fila, y por eso
el relleno que la recorre es el de aquella máquina sin tocar una línea.

**Los colores pidieron un gancho.** El dispositivo de esta máquina resuelve una
tinta de nueve —blanco o negro, el que se lea— contra el papel del momento, y
una lámina de Megacorp cambia el papel después y espera la tinta que ya tenía.
Así que el intérprete de láminas ofrece ahora `GFX_COLOURS` donde guarda un
color, vacío en las máquinas que los asientan una vez por figura.

**Comprobado contra la referencia**: cada primitiva por separado y las 31
láminas de Megacorp enteras, píxel a píxel, leyendo layer 2 por la propia
ventana de la máquina. La más lenta son 0,52 segundos a 28 MHz.

**Las partidas** van por la ROM del 48K, como en el Spectrum, con dos vueltas
de tuerca: la ROM no está en la máquina —los primeros 16K son la ventana de la
base de datos, así que se trae y se devuelve— y el procesador no va a la
velocidad en la que la ROM cuenta, así que baja a 3,5 MHz mientras dura y
vuelve a 28. Los dos sentidos se miran por separado, como en el Amstrad y el
MSX.

De eso salió un detalle que conviene no olvidar: **la ROM quiere la máquina
para la que se escribió**. Un Next que ha arrancado su sistema la tiene —que es
como se arranca un `.nex`—, pero un TBBlue recién encendido en el emulador no:
nada ha puesto las variables que las rutinas de cinta leen, y la última de
ellas manda la máquina al BASIC en lugar de devolverla. La prueba usa
`--tbblue-fast-boot-mode`, que es como el emulador da una máquina ya arrancada.

**La pared de `$A000` no era el final de la máquina.** `ASSERT last <= MASK`
mide lo que hay entre el final del intérprete y la máscara de los rellenos, y
llegó a quedar en tres bytes. Pero `gfx_clear` borra la máscara y para ahí, y
la pila baja desde `$BF00`: entre el final de una y el pie de la otra hay casi
cuatro kilobytes que nadie tocaba. Viajan en el fichero de todos modos, porque
`SAVENEX BANK 2` se lleva entero `$8000`-`$BFFF`, así que lo que se ponga ahí
sale gratis.

Lo que vive allí tiene que ser código al que le dé igual dónde está, y se coge
del final de la lista de `include` para que nada de lo anterior cambie de
orden. Empieza en `$B200` y no en `$B000`, y **la razón ya no existe**: ahí
iban la tabla del modo dos y su rutina, que eran de la música y se fueron con
ella. La dirección se deja donde está porque moverla no gana nada —el primer
kilobyte que libera está por debajo de la pared, donde ya sobra sitio—. Ahí
vive `picture.asm`, y bajo la pared quedan quinientos bytes largos. Si hace
falta más, se bajan más módulos.

**Lo que queda de esta máquina**: nada urgente. ~~Guardar en fichero por el API
de NextZXOS, si alguna vez se quiere en vez de la cinta.~~ Hecho: ver «El Next
guarda en la tarjeta», más abajo. El sonido ya está,
por su AY compatible —ruidos y clic de tecla—, **sin interrupción ninguna**:
la de modo 2 era del reproductor de música y se fue con él.

### MSX1, con la máquina entera y una cinta

Juega de principio a fin: dibuja láminas idénticas a las de la referencia,
imprime, lee el teclado sin BIOS que lo rastree, y se carga de una cinta con
`BLOAD"CAS:",R` y nada más.

**Se toma la máquina entera**, RAM en las cuatro páginas, porque un intérprete
y una base de datos no caben en los 32K que ve el BASIC. `out ($A8), $AA` y la
BIOS desaparece; está medido, y es reversible, que es lo que hace posible lo de
la cinta. El mapa queda plano y sin bancos: la base de datos en $0000, el
intérprete en $8000, la copia de la pantalla en $C000 y la pila en $EF00, por
encima de todo lo que viaja.

De ahí salió el susto de esta máquina: **la pila estaba dentro de la copia de
la base de datos que viajaba**, así que la dirección de retorno acabó metida en
la base de datos y dos bytes de una lámina se convirtieron en `07 80`. Se veía
como una raya verde saliéndose del marco.

**La pantalla es el modo 2**, con la VRAM detrás de los puertos $98 y $99 y
nada de acceso directo, así que se dibuja en una copia en RAM y se vuelca por
láminas. El color va por grupo de ocho píxeles de una sola línea, que es mucho
más suave que la celda del Spectrum. El teclado es el 8255 del Amstrad con
otra matriz, once filas, y **un bit a cero significa pulsada**.

**La cinta va en dos tiempos**, y el porqué está en
[`binario.md`](binario.md): lo único que sabe leer una cinta es la BIOS, que
está justo encima de donde va la base de datos, así que el BASIC carga el
intérprete y el intérprete lee el resto, trozo a trozo, devolviendo la BIOS
para cada uno y tomando la máquina otra vez para copiarlo debajo. La prueba lo
hace como su dueño: mete la cinta, teclea la orden y espera a que la aventura
pregunte.

**Y dos cosas que costaron horas cada una.** La orden no se puede teclear:
de las teclas que manda el emulador no llegan ni las comillas, ni los dos
puntos, ni la coma, ni como teclas ni como cadena. Lo que sí llega es dejarla
en el buffer del teclado del MSX, en $FBF0, y mover los dos punteros de $F3F8,
que es lo que el BASIC lee de verdad. Y el `SAVEBIN` del intérprete seguía
guardando desde `start` cuando delante ya había otra entrada, la de la cinta,
así que el fichero salía corrido doce bytes y la máquina saltaba a mitad de una
instrucción; desde fuera parecía que la cinta no cargaba.

**Y la pantalla de carga, puesta**, sin `BLOAD"CAS:",S` ni segunda orden que
teclear: va en la cinta detrás del intérprete y la mete el intérprete mismo,
directa al chip de vídeo según la lee, porque el chip lleva su propia
dirección y la sube solo. Se ve mientras entra la base de datos, que son dos
tercios de la cinta. Se le da el volcado de la memoria de vídeo, 14336 bytes,
o el `.SC2` de cualquier programa de dibujo de MSX, que es lo mismo con siete
bytes de cabecera delante.

**Y las partidas**, por la misma cinta y por la misma BIOS. Lo que viaja es
sólo la partida, de `vm_state` a `vm_state_end`, como en todas. Los dos
sentidos se miran por separado, igual que en el Amstrad, porque el emulador
reproduce cintas pero no las graba: grabar se comprueba viendo que la BIOS
acepta el bloque y dice que lo escribió —y tarda trece segundos de reloj, que
es lo que tarda de verdad, porque escribir no lo acelera nadie—, y leer se
comprueba contra una cinta con un bloque de bytes conocidos, comparados uno a
uno con lo que llega.

Las dos pruebas miran además lo que es de esta máquina: que el mapa vuelve a
ser el nuestro y que las interrupciones siguen apagadas. Y lo miran de la
manera más dura posible, porque el build que las corre toma la máquina entera
y **no lleva base de datos ninguna**: si esa disciplina se saltara, el salto a
$0038 iría a memoria vacía y no llegaría a terminar nada. Que termine es la
mitad de lo que se comprueba.

Lo que no está automatizado, y se ha mirado a mano en la máquina, es la
cadena entera desde el verbo: cargada la aventura de la cinta, se teclea
`SAVE` y el intérprete llama a la rutina, la ROM escribe durante medio minuto
—que es lo que tarda de verdad una partida a 1200 baudios— y al acabar el
juego sigue donde estaba, con su pantalla intacta. Automatizarlo no añadiría
nada: el emulador tampoco podría decir qué se grabó.

Una diferencia con el Amstrad que conviene saber: aquí no hay que devolverle
nada a la pantalla. Las rutinas de cinta de la BIOS dejan el chip de vídeo
exactamente como estaba, encendido y con sus registros; está mirado en la
máquina, con una pantalla puesta y un bloque escrito encima.

**Lo que queda de esta máquina**: nada. Hubo una lámina, una sola, que pasaba
del tope, y ya no —sigue leyendo—.
Están medidas las 196 de las ocho aventuras, con un contador de ciclos parado
en seco por un punto de ruptura, y **todas salen idénticas a la referencia**;
la más lenta de cada aventura va de 2,9 a 4,2 segundos, salvo en una: la 28
de Bangkok2, que cuesta **6,11 s**. Esa misma lámina en un Spectrum cuesta
**4,67 s**, así que la diferencia entre máquinas es de 1,31, no la vez y media
que decía antes este párrafo; y lo que la hace cara no es el MSX, es ella: en
el Spectrum también es la peor con diferencia (la 21 son 1,48 s y la 26, 0,30).

~~Dónde se van esos seis segundos no se sabe todavía.~~ **Ya se sabe, y la
lámina baja de 6,11 s a 4,45: dentro del presupuesto, de modo que no queda
ninguna de las 196 fuera de él en ninguna máquina.**

Los dos modos de mirarlo que había **se contradecían y estaban los dos mal**.
Muestreando el contador de programa 400 veces salía `colour_span` 19%,
`span_extent` 18% y `mark_span` 14,5%; poniendo un `RET` encima de cada rutina
salía que quitar `gfx_fill` ahorraba 0,86 s. Ninguna de las dos se acercaba.

### El perfil de verdad, que el emulador sabía dar

ZEsarUX tiene `cpu-transaction-log`: apunta a un fichero **cada instrucción
ejecutada**, con su dirección y el reloj. Con `opcode no`, `registers no`,
`address yes` y `tstates yes` la lámina 28 sale por 30 MB y catorce segundos
nuestros. El reloj es el de la trama y da la vuelta, así que la diferencia
entre dos líneas es lo que costó la instrucción, sumándole la trama cuando sale
negativa. Repartido por la etiqueta global anterior a cada dirección:

| rutina | % |
|---|---:|
| `run_picture`, el bucle que lee órdenes | 38,2 |
| `set_border` | 22,8 |
| `picture_find` | 14,3 |
| todo lo que dibuja de verdad | ~25 |

Hay dos acciones de punto de ruptura, `start-transaction-log` y
`stop-transaction-log`, si alguna vez se quiere acotar más fino.

### Y lo que el perfil descubrió: la lámina casi no dibuja

Siguiendo sus `CALL`, la 28 ejecuta **48.626 órdenes**: 43.821 `BORDER`, 4.726
`CALL`, y sólo 53 `LINE`, 15 `FILL` y 3 `RECT`. Es **un parpadeo de borde**
entre el rojo y el negro, hecho con sub-láminas anidadas que se llaman unas a
otras cuatro niveles. Por eso ningún ajuste del relleno la iba a tocar: el
relleno no es lo que hace.

Tres cambios, medidos uno a uno:

| | | |
|---|---:|---|
| de partida | 6,29 s | |
| **no reescribir un borde que no cambia** | 5,45 s | de las 43.821, sólo 17.528 piden un color que el borde no esté mostrando ya |
| **`BORDER` con destino propio en el reparto** | 5,07 s | se comparaba el código dos veces, en `.next` y otra vez en `.one_byte` |
| **guardar las dos últimas láminas y no una** | 4,45 s | |

**Lo de las dos láminas merece contarse**, porque la caché de una entrada que
había no estaba mal pensada: falla exactamente al volver de un nivel. Con A
llamando a B y B llamando a C, la única ranura tiene a C cuando A vuelve a
pedir B. Simulado en Python sobre las 4.726 llamadas de verdad antes de
escribir una línea de Z80: **una ranura falla 657 veces, dos fallan 81**, tres
27 y cuatro 7. Y promocionar la segunda cuando acierta no cambia nada —siguen
siendo 81—, así que no se hace y el código se queda corto.

Lo que compara la guarda del borde es **el valor sin enmascarar**: cuántos bits
significan algo es cosa de cada máquina, y el Amstrad pasa el número entero a
`hardware_ink`. Y la caché se pone a `$FF` al empezar cada lámina, porque
`gfx_clear` y el `mode_init` de cada máquina pueden haber movido el borde;
comprobado que fuera de esos dos sitios nadie lo toca, y que ninguno de los dos
ocurre dentro de una lámina.

**Cuesta 64 bytes** de intérprete, y está en `common/picture.asm`, de modo que
lo ganan las cinco máquinas —el PCW sólo la parte del reparto, que allí
`GFX_BORDER` está vacía—.

**Lo comprobado**: las 196 láminas de las ocho aventuras dibujadas en las tres
máquinas que las dibujan, **todas idénticas a la referencia en las tres**, más
las 66 pruebas de gráficos y la batería entera. La más lenta de cada aventura:

| aventura | Spectrum | MSX | Amstrad |
|---|---:|---:|---:|
| Bangkok1 | 3,6 | 3,4 | 2,3 |
| **Bangkok2** | **3,8** | **4,5** | **4,1** |
| megacorp1 | 3,4 | 3,7 | 2,3 |
| megacorp2 | 3,6 | 3,5 | 2,9 |
| quijote1 | 2,9 | 2,9 | 16,8 |
| quijote2 | 3,6 | 3,6 | 25,3 |
| vajillas1 | 4,6 | 4,2 | 7,8 |
| vajillas2 | 4,0 | 3,7 | 6,9 |

**El Spectrum y el MSX quedan enteros dentro del presupuesto.** En el Amstrad
siguen fuera el Quijote y las Vajillas, y siguen fuera por lo que ya se sabía
—cuarenta y tantos rellenos por lámina—, que esto no toca: sus números son los
mismos hasta la décima que antes del cambio, lo cual es de paso la prueba de
que lo que bajó a Bangkok2 fue el borde y no otra cosa.

La prueba lenta `tests/test_all_pictures_msx.py` guarda el tope de 5 segundos
para las 196 y lleva esa única lámina apuntada con nombre y con su número en
`KNOWN_SLOW`, de modo que si crece se entera, y si crece otra distinta,
también.

### Los dos Amstrad, que son dos máquinas

Un 464 tiene cinta y sesenta y cuatro kilobytes; un 6128 tiene disco y otros
sesenta y cuatro. Eso no es una perilla de un destino, son dos destinos:
`cpc464` y `cpc6128`, y el `cpc` de antes —que hacía disco y cinta y daba lo
mismo qué máquina fuera— ya no está.

**El 6128 pagina como el +3.** Las únicas dieciséis kilobytes que el gate
array sabe cambiar son las de `$4000`, con las cuatro configuraciones `&C4` a
`&C7`, así que la ventana va ahí y todo lo demás se coloca alrededor:

    $0300-$3FFF  lo residente de la base de datos, casi dieciséis kilobytes
    $4000-$7FFF  la ventana, uno de cuatro bancos
    $8000-$BEFF  el intérprete, con la pila encima
    $C000-$FFFF  la pantalla

Y de ahí sale lo que cierra el medio: **ese build no puede llamar al firmware
ni una vez**, porque una entrada del jumpblock es un `RST` y un `RST` trae la
ROM baja, que taparía lo residente mientras dura. Así que la cinta queda
descartada por el mapa y las partidas van al disco por sectores, como en el
PCW: ver «Las partidas del 6128, en su disco», justo aquí debajo.

El cargador es BASIC y pagina él: `OUT &7F00,&C4` y un `LOAD` por banco. De
paso, algo que costó una tarde: **los dos puntos que separan dos sentencias no
son el carácter `:` sino un `01`**. Con `3A` el `LIST` los enseña igual y BASIC
dice «Syntax error».

**Lo que gana**: las dos partes del Quijote, que no caben en un Amstrad de
sesenta y cuatro, caben en un 6128 con un banco y de sobra. Y el intérprete,
que en un 464 acaba a un palmo del firmware, ahí acaba en `$A011` con casi
ocho kilobytes libres.

### Las partidas del 6128, en su disco

Hecho como estaba decidido: igual que en el PCW. `release` pone en el disco un
fichero `.SAV` vacío y del tamaño justo —cuatro sectores, que una partida son
unos mil cien bytes—, sin cabecera de AMSDOS porque nadie lo carga, y escribe
dónde empieza en el propio intérprete antes de meterlo en el disco. El
intérprete escribe y lee esos sectores él mismo, hablando con el PD765, sin
tocar el directorio; lo que queda sigue siendo un fichero que AMSDOS copia.

Lo que cambia respecto al PCW son tres cosas y media:

- **Dónde se le dice.** El 6128 no arranca de un sector propio donde dejar el
  dato, así que va en **tres bytes fijos del intérprete, en `$8002`**: pista,
  registro y cuántos sectores. El intérprete empieza con un salto por encima
  de ellos, `release` los rellena con lo que dice el directorio del disco que
  acaba de montar, y se niega a escribir en un binario que no empiece por ese
  salto. Un `ASSERT` vigila que no se muevan.
- **Los puertos son de dieciséis bits** —estado en `$FB7E`, datos en `$FB7F`,
  motor en `$FA7E`— y los sectores de un disco de datos se numeran de `$C1` a
  `$C9`.
- **Las interrupciones se quitan mientras dura.** En mitad de un sector el
  controlador entrega un byte cada treinta y dos millonésimas y no espera, así
  que cualquier cosa que interrumpiera perdería alguno. El bucle de los datos
  gasta unas veinte. Hoy no interrumpe nada —el intérprete corre con ellas
  quitadas— y esto dice por qué no pueden volver.
- Y la media: **escucha la respuesta del controlador**, cosa que el del PCW no
  hace. Un disco protegido o un sector que no se lee vuelven con el acarreo
  quitado en vez de dar la partida por guardada; y cargar deja la partida como
  estaba si no llegó entera.

Las pruebas (`test_save_cpc.py`) comprueban las dos mitades: que el intérprete
lleva escrito lo que dice el directorio, y que un bloque guardado vuelve
entero en un 6128 emulado. Dos cosas que costaron:

- **El emulador guarda en memoria y no en la imagen**, salvo con
  `--dsk-persistent-writes`. Con esa opción la prueba lee el disco desde fuera
  al acabar y ve el bloque **dentro de `JUEGO.SAV`**, que es lo que dice que va a
  los sectores de ese fichero y no a otros en los que el constructor y el
  intérprete simplemente coincidan. Y la prueba borra también el área de trabajo
  entre guardar y cargar: sin eso, una lectura que no hiciera nada devolvía lo
  que seguía allí y pasaba igual.
- **Con el disco protegido la máquina se colgaba**, y la prueba pasaba porque la
  bandera de «guardado» empieza a cero. El emulador, con `--dsk-write-protection`,
  abandona la orden de escritura antes de oír sus nueve bytes y se pone a
  contestar, y el código se quedaba esperando a que volviera a escuchar. Ahora
  `send`, si el controlador quiere hablar en mitad de una orden, lo apunta y
  deja de insistir, y el sector va a leer la respuesta, que dice por qué. Un
  controlador de verdad oye la orden entera antes de negarse, así que en la
  máquina real ese camino no se pisa, pero el código sirve para las dos. La
  prueba exige ahora que la máquina termine.

**Y de punta a punta, tecleando.** La última prueba arranca La guerra de las
vajillas desde su disco del 6128 tal como lo hace `release` —es la única de las
ocho cuya primera sala tiene salida—, teclea `SAVE`, `NORTE` y `LOAD`, y mira la
sala en memoria: 1, 4 y otra vez 1. Al acabar lee el disco desde fuera y
`JUEGO.SAV` empieza por la sala 1. Dos tropiezos de la prueba, no del
intérprete, que valen para cualquier prueba que teclee:

- **Una orden tecleada mientras se dibuja se pierde**, porque el teclado no se
  mira mientras tanto. La sala cambia en cuanto se obedece la orden, pero hay
  que esperar a que vuelva a preguntar.
- **Y a que pregunte de nuevo**: la línea en la que se tecleó la orden empieza
  por la misma pregunta. Lo que vale es la última línea con la pregunta sola.

### Lo que hace el `LOAD` del original

Salió de la prueba de arriba: después de `LOAD` la sala se describía dos
veces seguidas, y pegadas (`…ARENAS.ESTAS EN EL PLANETA…`), una porque
`op_load` daba la sala por nueva y otra por el `LOOK` que la aventura pone
detrás (`LOAD LOOK WAIT`). Ninguna de las dos referencias implementaba `LOAD` entonces
—grackle dice «Not implemented (yet)» y `runGAC.py` tenía un `TODO`, que ya no
tiene: ver «`SAVE` y `LOAD` en `runGAC.py`»—, así que se miró en el original de
Spectrum, leído y viéndolo funcionar.

**Leído.** Los opcodes del juego están en `$788F` (`SAVE`) y `$78B3` (`LOAD`).
Los dos piden un nombre —«Introduce nombre del fichero...»— y usan la ROM
para un fichero CODE con cabecera, de 768 bytes desde `$A1FD`. `LOAD`, antes
de cargar, se guarda dos punteros del intérprete que van dentro de ese bloque
(`$A4E8` y `$A4F4`) y los repone después: es lo que le deja **volver a la
condición** y seguir con lo que venga detrás. Luego imprime unos códigos de
control que dejan la zona del dibujo en blanco y el cursor en la ventana de
texto, un salto de línea, y vuelve. En ningún sitio marca la sala como nueva.

**Visto.** Se arrancó Vajillas 1, se fue a la sala 4 y se hizo una cinta con
esa partida en su formato; se volvió a arrancar en la sala 1, con esa cinta
puesta, y se teclearon `LOAD` y el nombre. La sala 4 sale **una sola vez**, y
detrás la pregunta. Para que la cinta se leyera hizo falta cargar la
instantánea con `snapshot-load` y no con `smartload`, que se ponía por medio, y
arrancar el emulador con `--noautoload`, porque si no teclea él solo `""` en
cuanto hay cinta.

**Lo que se cambió:** `op_load` ya no marca la sala como nueva, en ninguna
máquina. Con `LOAD LOOK WAIT` la sala se describe una vez, por el `LOOK`; con
el `LOAD WAIT` de Bangkok, como en el original, no se describe. La prueba de
teclear del 6128 cuenta las descripciones después de `LOAD`: con el código de
antes daba dos, y ahora una.

**Lo que no se cambió**, y es distinto del original: no se borra la pantalla
al cargar, que es cosmético, y no se pide nombre de fichero, porque nuestro
formato de partida es otro a propósito.

### La memoria que AMSDOS no suelta

El disco de antes —el intérprete y la base de datos entera de un tirón desde
`$4000`— tenía un agujero desde siempre y se descubrió al llenarlo: **AMSDOS
se queda dos kilobytes de buffer alrededor de `$A700` y no los suelta** cuando
BASIC pide la memoria con `MEMORY`. Un fichero cargado por encima vuelve con
un boquete de dos kilobytes.

Llevaba años ahí sin morder porque lo que caía en el boquete era base de datos
que no se leía pronto. El día que le tocó a los gráficos, una lámina salió
como un garabato de líneas. Se midió comparando la memoria después de cargar
contra el fichero: 2418 bytes distintos, el primero en `$A700` clavado.

Ninguno de los dos Amstrad de ahora pasa por ahí —el 464 carga de cinta y el
6128 deja el intérprete en `$8000` y la base de datos entra por la ventana—,
así que la función que escribía aquel disco ya no está. Queda escrito por si
alguien quiere volver a esa forma.

### Lo que le queda libre al Amstrad, que es poco

Su mapa es fijo: el intérprete desde `$4000`, la base de datos detrás alineada
a 256, y el firmware empezando en `$B100`, que es donde salta el `ASSERT` de su
[`game.asm`](../z80/cpc/game.asm). Medido con las ocho aventuras:

| aventura | base de datos | acaba en | le sobran |
|---|---:|---:|---:|
| vajillas2 | 17387 | `$A3EB` | 3349 |
| vajillas1 | 17538 | `$A482` | 3198 |
| Bangkok1 | 18328 | `$A798` | 2408 |
| megacorp1 | 19204 | `$AB04` | 1532 |
| Bangkok2 | 19208 | `$AB08` | 1528 |
| megacorp2 | 20574 | `$B05E` | **162** |
| quijote2 | 20984 | — | **le faltan 248** |
| quijote1 | 21115 | — | **le faltan 379** |

~~**Las dos partes del Quijote no caben en un Amstrad.**~~ **Ya caben**, dando
la vuelta al mapa: ver «El Quijote en un 464», más abajo.

Y hay un **escalón** que conviene saber, porque muerde sin avisar: como la base
de datos va alineada a 256, lo que importa no es cuánto crece el intérprete
sino cuándo cruza una página. Antes de los marcadores acababa en `$5F21` y
ahora acaba en `$5FDA` —185 bytes más— y **ninguna aventura ha perdido un solo
byte**, porque la base de datos sigue cayendo en `$6000`. Pero quedan **38
bytes** hasta el escalón, y el día que se crucen, las ocho pierden 256 de golpe
y megacorp2 se sale. Eso es justo lo que pasó a mitad de esta tanda: con una
tabla de separadores metida a capón el intérprete pasó de `$6000`, la base de
datos se fue a `$6100` y `regac make` dejó de construir esta máquina.

### El Quijote en un 464, con el mapa del revés

Un 464 no tiene bancos y su base de datos va de una pieza, así que las dos
partes del Quijote —21115 y 20984 bytes— no cabían de ninguna manera: el
intérprete ocupa desde `$4000` y el firmware corta en `$B100`. Ahora caben
porque **el intérprete y la base de datos se cambian el sitio**.

Los dieciséis kilobytes de debajo de `$4000` son RAM como cualquier otra en
cuanto las dos ROM están fuera, y ahí ya vivía la música. Ahí va ahora el
intérprete, y la base de datos se queda con todo lo de arriba:

| desde | qué |
|---|---|
| `$0400` | el intérprete, unos 8280 bytes |
| `$4000` | la base de datos entera, **27392 bytes** de sitio |
| `$AB00` | la isla: las dos llamadas de la cinta y una copia de la partida |
| `$B100` | lo del firmware |

**Tres cosas costaron entenderse**, y las tres son de la ROM baja:

1. **La cinta se graba por el firmware, y el firmware devuelve la ROM baja
   mientras dura.** Así que ni la llamada ni los bytes que se le dan pueden
   estar debajo de `$4000`: serían ROM. De ahí la isla, que es lo único de un
   build bajo que vive arriba. La partida se copia allí para grabarla y se
   copia de vuelta al cargarla. La isla no nombra ninguna dirección suya, así
   que se ensambla abajo y se ejecuta arriba sin más.
2. **BASIC no puede llamar a `$0400`**, porque en ese momento `$0400` es ROM.
   Lo que llama es un arranque de siete bytes que el movedor deja en la isla:
   quita las dos ROM por el chip y salta abajo. El intérprete lo pisa después
   con la isla de verdad, que ya no lo necesita.
3. **Al volver de la cinta, el firmware repone la paginación que él cree**, y
   lo que cree es que la ROM baja está puesta: el intérprete nunca se lo dijo,
   mueve el chip por su cuenta. Un `ret` a una dirección de abajo con esa idea
   en vigor cae en ROM y la máquina se va al monte, que es justo lo que hizo
   hasta que la isla aprendió a reponer la nuestra antes de devolver el
   control.

**Cómo viaja.** No se puede cargar donde corre, porque la línea de BASIC que
carga está ella misma en `$0170`: el fichero entra en `$4000` con un movedor delante, el
movedor lo baja y vuelve, y entonces la base de datos se carga encima de donde
estuvo. El cargador son cinco líneas: `MEMORY &3FFF`, cargar el intérprete,
llamar al movedor, cargar la base de datos y llamar al arranque de la isla.
BASIC guarda sus variables debajo de `$3FFF` y hacia abajo; el intérprete acaba
sobre `$2450`, así que hay siete kilobytes de nadie entre los dos.

**Se elige solo.** `regac make` construye como siempre y, si el ensamblador
dice que no cabe, vuelve a construir con `-DLOW_CODE` y lo dice por pantalla.
Las seis aventuras que caben siguen saliendo exactamente igual.

Las pruebas son [`test_low_cpc.py`](../tests/test_low_cpc.py) —el Quijote
jugando con el mapa del revés, el cargador, y la cinta entera cuando se pide
con `REGAC_SLOW=1`— y una más en
[`test_tape_cpc.py`](../tests/test_tape_cpc.py), que graba un bloque desde un
build bajo y mira que la copia llegó a la isla y que la máquina volvió entera.

### Lo que cuesta dibujar en el Amstrad, que es mucho

Medido con el contador de ciclos parado en seco, igual que el MSX, y sale lo
peor que hemos encontrado en este proyecto:

| lámina | Spectrum | Amstrad |
|---|---:|---:|
| megacorp2 #29 | 3,53 s | **27,54 s** |
| megacorp2 #4 | 2,58 s | **21,31 s** |
| quijote1 #8 | 2,54 s | **45,03 s** |
| quijote1 #2 | 1,60 s | 4,89 s |
| quijote1 #3 | 1,34 s | 4,93 s |

No es del Quijote: **MegaCorp II se publicó en Amstrad** y sus láminas tardan
veinte y veintisiete segundos con nuestro intérprete. El tope que este
proyecto se puso es de cuatro o cinco.

Y lo primero que había que descartar: **las láminas salen bien**. Comparadas
punto a punto contra el renderizador de referencia con la paleta del Amstrad,
**cero diferencias**. No están mal dibujadas, están lentas.

Dónde se va el tiempo se ve contando lo que pide cada una:

| lámina | órdenes | rellenos |
|---|---:|---:|
| quijote1 #8 | 181 | 41 |
| quijote1 #2 | 43 | 12 |
| quijote1 #3 | 9 | 0 |

Cuarenta y cinco segundos entre cuarenta y un rellenos es **1,1 s por
relleno**; en el Spectrum los mismos salen a unos 60 ms. La razón está en el
fuente de cada uno: **el del Spectrum trabaja por bytes** —ocho píxeles de una
vez, con máscara— y **el del Amstrad va punto a punto**, porque en modo 1 un
píxel son dos bits y tanto `blocked` como `put_pen` preguntan y escriben de
uno en uno. Un `put_pen` son una dirección, una máscara, un byte de pluma y
una mezcla, por píxel.

**Y eso está hecho**, en cuatro pasos, midiendo cada uno:

| | quijote1 #8 | megacorp2 #29 |
|---|---:|---:|
| como estaba | 45,03 s | 27,54 s |
| tendiendo el trazo por bytes | 23,32 | 14,88 |
| sacando la pluma con rotaciones | 21,31 | 13,94 |
| andando la dirección en vez de calcularla | 13,32 | 9,23 |
| saltando bytes enteros de la pluma de la semilla | 5,67 | 4,89 |
| y con el rastreo en registros | **4,17** | **4,87** |

De ocho a once veces, y **sin cambiar un píxel**: las tres láminas más
cargadas de cada una de las ocho aventuras, veinticuatro en total, comparadas
punto a punto contra el renderizador de referencia, cero diferencias.

Los cuatro pasos, por si hay que volver:

1. **El trazo se tiende por bytes.** Cuatro píxeles por byte en modo 1, y como
   un byte empieza en un múltiplo de cuatro, cuál de las dos plumas toca a
   cada píxel suyo depende sólo de la y: **todos los bytes enteros de un trazo
   son el mismo byte**, y sólo los dos de los extremos hay que desmenuzarlos.
2. **La pluma de un píxel** sale rotando el byte hasta alinearlo y mirando dos
   bits, en vez de recorrer las cuatro plumas comparando.
3. **El rastreo lleva la dirección** —el byte en HL y los dos bits del píxel en
   C— y la anda: un píxel a la derecha es `rrc c`, y el acarreo que suelta es
   exactamente «y pasamos al byte siguiente». Ni una dirección se vuelve a
   calcular.
4. **Se saltan bytes enteros** mientras los cuatro píxeles son la pluma de la
   semilla, que es de lo que está hecho casi todo un trazo.

### La segunda vuelta del relleno, que es otro doble

Con la prueba de las 196 ya escrita se podía medir de verdad, y además
muestrear el contador de programa mientras dibuja para ver dónde se va el
tiempo. Salió repartido en tres sitios, y los tres se tocaron:

1. **El rastreo con `cpd` y `cpi`.** Comparar, andar y contar en una sola
   instrucción: 33 relojes por cuatro píxeles donde el bucle a mano gastaba
   138. Lo que lo hace limpio es que esas instrucciones llevan ellas mismas HL
   y BC, así que **todas las salidas del bucle se arreglan igual** y lo que
   queda en BC dice exactamente dónde paró: los bytes que no anduvo, sin
   contar aquel en el que se detuvo.
2. **La fila, una vez por fila.** `pixel_address` son cuarenta instrucciones y
   se llamaba cuatro veces por fila —en `blocked`, en `fill_run` y dos en
   `byte_of`—. Ahora la calcula `blocked`, que tenía que hacer las mismas
   cuentas para contestar, y guarda dónde empieza la fila; los demás la
   encuentran hecha. Era un octavo de la lámina.
Otro doble, y de nuevo sin cambiar un píxel: 196 de 196 idénticas.

| lámina | antes | ahora | |
|---|---:|---:|---:|
| quijote1 #15 | 34,46 s | 16,81 | 2,1x |
| quijote2 #15 | 51,7 | 25,28 | 2,0x |
| quijote2 #14 | 23,32 | 11,58 | 2,0x |
| quijote1 #9 | 14,94 | 8,35 | 1,8x |
| vajillas1 #7 | 12,24 | 7,71 | 1,6x |
| vajillas1 #12 | 10,30 | 7,17 | 1,4x |
| vajillas2 #10 | 4,85 | 3,85 | 1,3x |
| quijote1 #8 | 4,21 | 3,02 | 1,4x |
| megacorp2 #29 | 3,81 | 3,02 | 1,3x |

### Y el tercer cambio, que se escribió, se midió y se devolvió

**El tendido de a ocho.** Un `ld (hl),d` y un `inc hl` son trece relojes y el
`djnz` que iba con cada uno era otros trece, así que desenrollando de ocho en
ocho se paga la cuenta una vez. Dos cosas que enseñó:

- **Desenrollar siempre salió peor.** Las láminas del Quijote están hechas de
  trazos cortos, y repartir un trazo de tres bytes cuesta más que tenderlo a
  pelo: quijote1 #9 llegó a empeorar. Con una guarda de «ocho o más» ganaba en
  los dos casos.
- **Y aun así valía un 4 por ciento.** Con él, las peores de las ocho aventuras
  eran 2,5 / 6,3 / 2,3 / 3,2 / 16,1 / 23,8 / 7,9 / 6,8 contra 2,5 / 6,2 / 2,5 /
  3,1 / 16,8 / 25,4 / 7,8 / 7,1 sin él. Nada.

Y costaba cuarenta y cuatro bytes, que el Amstrad no tiene. Así que se devolvió.

**La cuenta de memoria, que es la que manda aquí.** Las dos vueltas de rellenos
juntas costaban 92 bytes, y el build de cinta **con música** —el del movedor que
baja la música a `$0300`— sólo tenía 53 libres. Devuelto el tendido y sacados
otros trece sin perder velocidad (la pluma sale de A, que `cpd` no toca, y
`fill_row` ya no lo lee nadie), la cuenta con MegaCorp II queda así:

| build | libre |
|---|---:|
| cinta sin música, que es lo que el 464 publica | 67 bytes |
| cinta con música | 14 bytes |

Catorce bytes eran nada, y duraron poco: al imprimir el texto palabra a palabra
(ver «El texto, palabra a palabra», más abajo) el búfer de 256 bytes se quedó
en 41, y la cuenta pasó a **288 bytes libres sin música y 235 con ella**.

**Lo que queda, por si hay una tercera vuelta.** Muestreado el contador de
programa al terminar, el reparto era: el rastreo un 38 por ciento, el tendido un
14, y el resto en los extremos de los trazos (`.right_done`, `.several`,
`merge_byte`) y en lo poco que queda de `pixel_address` y `byte_of`. El rastreo
ya está en el hueso: `cpd` son 16 relojes y las dos pruebas de bandera otros 17,
y no se pueden quitar porque hay que mirar el byte y el contador. Donde queda
margen es en el tendido: **con la pila** se escriben dos bytes por `push` en
once relojes, cinco y medio por byte contra los trece de ahora. Obliga a quitar
las interrupciones mientras la pila apunta a la pantalla —y el Amstrad las tiene
puestas cuando lleva música y quitadas cuando no, así que haría falta una
bandera para saber si hay que volver a ponerlas—, y a estas alturas lo que se
gana no cambia de sitio a ninguna aventura.

**Y las dos partes del Quijote siguen siendo otro problema.** 17 y 25 segundos
contra un presupuesto de 4 o 5 no se arregla apretando esto: son sus láminas,
que tienen cuarenta y tantos rellenos cada una. Mirado lo que hacía el original
de CPC —en la sección de más abajo—, la respuesta es que su intérprete era
más lento que el nuestro, y que lo que hizo Dinamic fue dibujar las láminas otra
vez para la máquina.

Y por qué no lo había visto nadie: **el Amstrad era la única máquina sin la
prueba de todas las láminas de todas las aventuras**, que el Spectrum tiene
desde hace tiempo y el MSX desde hace poco.

### La prueba de las 196 láminas, que ya está y ya ha servido

`tests/test_all_pictures_cpc.py`, con `REGAC_SLOW=1`. Dibuja las 196 láminas de
las ocho aventuras en el emulador, cuenta los ciclos de reloj de cada una y
compara punto a punto contra el renderizador de referencia. Lo que exige de
tiempo no son los 4-5 s del presupuesto —sólo tres aventuras los cumplen— sino
**lo que la máquina tarda hoy, aventura por aventura**: un trinquete, para que
el día que algo se vuelva más lento la prueba lo diga. La vuelta entera son 27
minutos.

Lo que mide, con el arreglo que cuenta más abajo, la segunda vuelta de
rellenos y lo del borde de «la lámina 28 del MSX» —que bajó Bangkok2 de 6,1 a
4,1 también aquí, porque el código es el mismo para las cinco máquinas—:

| aventura | la más lenta |
|---|---|
| Bangkok1 | 2,3 s |
| Bangkok2 | 4,1 s |
| megacorp1 | 2,3 s |
| megacorp2 | 2,9 s |
| quijote1 | 16,8 s |
| quijote2 | 25,3 s |
| vajillas1 | 7,8 s |
| vajillas2 | 6,9 s |

Medido ya con el reloj arreglado (ver «El reloj de las pruebas contaba de más»,
más abajo). La vuelta entera son dieciséis minutos, que eran veintisiete.

Y lo que encontró: **tres láminas de las 196 salían mal**, y no de ahora —se
comprobó volviéndolas a dibujar con el relleno viejo y salían igual de mal—.
Las tres eran de color y no de forma, y las tres pedían una tinta de ocho o
más, que en este formato quiere decir *deja el color como está*, porque viene de
una máquina cuyo BASIC lo escribía así. El Spectrum lo mira en cinco sitios, el
MSX en dos y el PCW en dos; **el Amstrad no lo miraba en ninguno**: se quedaba
con los dos bits de abajo, así que una `INK 9` le cambiaba la pluma cuando no
debía. En megacorp1 #10 el bosque entero se dibujaba de un color que no se
distingue del fondo y la lámina salía casi vacía —y de paso era la más cara de
su aventura, 7,2 s, porque el relleno que la seguía se iba por todo el hueco
que el bosque tenía que haber cerrado; arreglada, la aventura entera baja a
3,0 s—.

Arreglado en `z80/cpc/draw.asm`: la tinta se convierte en pluma **una vez por
orden de color**, en el gancho `GFX_COLOURS` que el intérprete de láminas deja
para eso y que en esta máquina estaba vacío, y sólo si es una tinta de verdad.
Sale además más barato que antes, porque los dos sitios que ponen un punto
hacían tres cargas, una llamada y un paseo por una tabla por cada punto, y
ahora hacen una carga.

La lista de las láminas más caras, por número de rellenos, que sigue siendo por
donde hay que seguir apretando:

| aventura | las tres peores |
|---|---|
| vajillas1 | #12 con 163 rellenos, #4 con 83, #7 con 76 |
| vajillas2 | #10 con 142, #16 con 93, #14 con 74 |
| megacorp2 | #29 con 87, #4 con 51, #8 con 40 |
| megacorp1 | #3 con 63, #20 con 43, #6 con 40 |
| quijote2 | #10 con 46, #14 con 45, #5 con 45 |
| quijote1 | #8 con 41, #1 con 41, #16 con 36 |
| Bangkok1 | #33 con 35, #3 con 31, #7 con 25 |
| Bangkok2 | #18 con 21, #19 con 18, #28 con 17 |

### Mirar las versiones de CPC, que es la lección para el PCW

Sergio puede conseguir las mismas aventuras en su versión de Amstrad CPC. Es la
mejor fuente que hay para el PCW, porque es el único sitio donde se ve qué hizo
el original al llevar las láminas a una máquina que no es el Spectrum.

Lo que se encuentra por ahí son imágenes de disco y de cinta, no instantáneas.
Las de disco se leen sin encender nada, con `disk.py`, hasta las protegidas.
Para una cinta sí hace falta la máquina, y eso es lo que hace `grab.py`:
arranca el emulador en la máquina que se le diga, mete el medio, espera a que
cargue y escribe la memoria en un fichero plano donde la dirección de un byte
es su posición.

    python grab.py --machine CPC464 juego.cdt juego.bin
    python grab.py --machine CPC6128 juego.dsk juego.bin

Está comprobado contra una instantánea de Spectrum, que se puede comparar
consigo misma: los 48K vuelven byte a byte salvo el contador de fotogramas y
los dos bytes de pila que usa la propia instantánea para arrancar. Eso sí, con
una cinta pide paciencia y puntería: una de CPC tarda seis o siete minutos de
reloj en cargar, y hay que leerla cuando ha acabado de cargar y antes de que el
juego eche a andar. Antes faltan las láminas, que van al final; después el
juego ya se ha escrito encima de lo suyo.

Las versiones de Amstrad ya están, en `juegos`, acabadas en `_ams.zip`: son
Megacorp, Los pájaros de Bangkok y La guerra de las vajillas, cada una en
disco y en cinta. De las tres tenemos también la de Spectrum, así que la misma
aventura se puede comparar en las dos máquinas, que es justo lo que hace falta.

Al final el emulador no hizo falta para el disco: `disk.py` lee el directorio
de AMSDOS, junta el fichero y lo deja en una imagen de 64K en la dirección que
dice su propia cabecera. `CARVALHO.FAC`, que es Los pájaros de Bangkok, se
carga en $0040 y trae dentro el intérprete entero, con los punteros en $4000.
De ahí sale todo lo que está contado en `graficos.md`, en el apartado de la
versión de CPC.

Vale la pena saber que el emulador que ya usamos hace también el PCW 8256 y el
8512 con disquetera, así que el banco de pruebas del runtime del PCW no hay que
inventarlo: es el mismo que el del Spectrum con otro nombre de máquina.

Leyendo ese decompilador ya se sacan cuatro cosas, antes incluso de tener las
instantáneas:

**La geometría es la misma y el color no.** Recta, elipse, rectángulo, punto,
relleno, trama y llamada existen en las dos máquinas con los mismos argumentos.
Lo que cambia por completo es el color: el Spectrum tiene tinta, papel, brillo,
parpadeo y borde, cada uno con su argumento, y el CPC tiene cuatro tintas
metidas en el propio opcode y nada más. La numeración de los opcodes tampoco
coincide en nada. Es justo la separación que ya hicimos entre el intérprete de
láminas y el dispositivo, confirmada por el original.

**Las coordenadas son los mismos bytes en las dos máquinas**, así que el ajuste
a la pantalla lo hace la máquina y no el dato. Leyendo el intérprete se ve
cómo: un factor de escala de un byte y dos orígenes. En el CPC el factor deja
la lámina a tamaño natural, pero la perilla está puesta, y es la que le hace
falta al PCW.

**El CPC guarda una paleta por lámina**, ocho bytes a la cabeza de cada
registro, antes de las órdenes. Es la respuesta del original a la pregunta que
nuestro `choose_inks` resuelve adivinando: las tintas no se deducían del uso,
se guardaban. En el PCW ese mismo hueco es el que diría qué trama representa a
cada tinta.

**El lenguaje de láminas se amplió por máquina.** El CPC tiene cuatro órdenes
de espejo y volteo que el Spectrum no tiene, y no tiene relleno de fondo.
Añadir órdenes propias de una máquina no rompe nada, es lo que ya se hacía.

Eso era lo que se sacaba del decompilador. Leyendo el intérprete de CPC entero
quedan contestadas las preguntas que quedaban, y están escritas en
`graficos.md`: la trama es un damero de dos plumas, la prueba de bloqueo
compara el byte de pantalla contra un byte de referencia con la pluma de la
semilla repetida, la tabla de la elipse es la misma sin una cifra distinta, y
las coordenadas sí pasan por una escala, con una perilla de un byte y dos
orígenes que es justo lo que el PCW necesita.

De la versión de CPC quedaban tres cabos, y los tres están atados.

**Los ocho bytes de cada lámina** son las cuatro tintas, y los bits que
sobraban —dos, no tres, porque el séptimo no se pone nunca— son porque el color
se tecleaba como una letra. El propio intérprete lo lleva escrito dentro: «Ink
#: Colours (A..Z or SPACE)?». Guarda el carácter tal cual y el firmware se
queda con los cinco bits de abajo, así que la A y la a son 1, la Z y la z son
26 y el espacio es negro. Está contado en `graficos.md`, y `deGAC` guarda ya el
color y no la letra.

**Megacorp** no tenía las tablas en otro sitio, que era lo que parecía. Su
fichero dice que carga en $0428, pero sus últimos catorce bytes son un `LDIR`
que lo baja a $0040 y salta dentro, que es justo donde carga Los pájaros de
Bangkok; el `.BAS` que lo arranca no hace más que cargarlo y llamar ahí.
`disk.py` sigue ese salto por su cuenta y lo dice al escribir la imagen, y
admite `--at` para poner el fichero donde se le diga. Leídas así, las dos
partes traen el mismo vocabulario que las de Spectrum —55 nombres iguales en la
primera, 60 de 64 en la segunda— y las láminas dibujan las mismas escenas, con
más color. Lo que difiere es de versión, no de lectura: en el CPC el verbo es
`INVENTARIO` y en el Spectrum `INVE`.

**La guerra de las vajillas** tampoco necesita la máquina. Su disco no tiene
nada en el directorio: la pista 0 es una pista normal, con su sector de
arranque —el disco se pone en marcha con `|CPM`— y el directorio vacío, y las
demás llevan cinco sectores de mil veinticuatro bytes numerados del 1 al 5, que
AMSDOS no sabe qué son. Pero esas pistas son el dato tal cual, una detrás de
otra, así que no hay nada que descifrar: basta buscar los ocho signos de
puntuación, que en memoria están en $210C, y eso dice dónde empieza todo. Hay
dos aventuras dentro, que son las dos partes, y `disk.py --part 1` o `--part 2`
las saca.

Contrastado contra la cinta cargada en la máquina, que es la vía lenta: con la
cinta a medio cargar, todo lo que llevaba metido —de $0040 a $57D7, veintidós
kilobytes— es byte a byte lo que sale del disco, y la tabla de punteros de
$4000 es la misma. Dejarla acabar del todo no sirve para comparar, porque el
juego arranca y se escribe encima. Y contra la
versión de Spectrum: 55 verbos, 17 objetos, 26 cuartos y 73 mensajes en las
dos, un nombre de más en el CPC (`COCINA`), y en la segunda parte `SPIELBERG`,
que en el Spectrum es nombre y en el CPC verbo. Láminas tiene más el CPC, 14
contra 11 en la primera parte y 21 contra 16 en la segunda, y dibujan las
mismas escenas.

De paso, `deGAC` avisa cuando las tablas de una máquina no parecen punteros. Sin
ese aviso, una imagen de memoria puesta donde la máquina no la pondría se lee
como una aventura con un solo nombre y nadie se entera.

### Lo que tardaba el original en dibujar, que era más que nosotros

La pregunta vino del Quijote: 17 y 25 segundos su peor lámina en nuestro
Amstrad contra un presupuesto de 4 o 5. Antes de apretar más hacía falta saber
contra qué se compara eso, y la única vara honrada es **el intérprete original
de CPC dibujando sus propias láminas**. Así que se midió, con el mismo reloj
que las nuestras: los ciclos del Z80 que cuenta el emulador, a cuatro millones
por segundo.

| Los pájaros de Bangkok, versión de CPC | el original | el nuestro |
|---|---:|---:|
| la peor lámina (la #35 en los dos) | 8,57 s | **2,62 s** |
| la media | 3,25 s | **1,22 s** |
| las 44 juntas | 143,1 s | **53,4 s** |
| láminas de más de 5 s | 7 | 0 |
| láminas de más de 4 s | 12 | 0 |

Son **las mismas 44 láminas**, las de la versión de CPC sacadas de su disco con
`disk.py` y `deGAC -m cpc`, y las 44 salen punto por punto iguales que la
referencia. El nuestro es más rápido en 43 de las 44, con una mediana de 2,6
veces y hasta 3,3. La única en que pierde es la #1, de 75 bytes: 0,24 contra
0,32, porque ahí manda lo que cuesta borrar la ventana antes de empezar, y el
original la borra con el firmware, que lo hace de un tirón.

Tres cosas que salen de aquí:

- **El original no cumplía el presupuesto.** Una lámina de cada cuatro pasaba
  de 4 segundos y la peor rozaba los 9. El tope de 4 o 5 es nuestro, no suyo, y
  en el Amstrad lo cumplimos con holgura en todo lo que el original dibujó.
- **Por qué era más lento.** El relleno del original ya iba por bytes, como el
  nuestro (está contado más arriba); lo que no hace él mismo son las rectas y
  los puntos, que pide al firmware, y el firmware del CPC los hace en
  coordenadas de 640 por 400 pasando por la escala en cada punto. Eso no está
  medido rutina por rutina, pero es lo único que no se parece.
- **La lección del Quijote es la del dibujante, no la del programador.** El
  Quijote nunca salió en CPC, y sus láminas son las del Spectrum, que rellenan
  áreas enormes con cuarenta y tantos rellenos cada una. Lo que hizo Dinamic
  con Bangkok no fue portar las láminas del Spectrum, fue **dibujarlas otra vez
  para la máquina**: 44 en vez de 32, ninguna igual. Con el intérprete
  original, y sólo echando la cuenta a la misma proporción, las del Quijote
  habrían tardado del orden de un minuto; con el nuestro tardan 17 y 25. Si algún día importa, el camino es el de
  entonces: láminas pensadas para el Amstrad, no un relleno más rápido.

**Cómo se midió, por si hay que repetirlo con Megacorp o las Vajillas.** Se
arranca el juego de verdad desde su disco —`run"carvalho`, la comilla tecleada
con mayúsculas y 2 como en la máquina, y luego la opción del cargador— y se
deja llegar a su *prompt*. Ahí el procesador está dentro de la ROM del
firmware, y eso es lo que complica todo: **por debajo de `$4000` la misma
dirección es a la vez la ROM y el código del juego**, así que ningún punto de
parada en esa zona se puede creer, y la tabla de saltos de `$BB00` tampoco sirve
porque el juego espera la tecla dentro de la ROM sin pasar por ella. Lo que sí
funciona es escribir treinta bytes propios en `$A300`, justo detrás del juego,
que hacen lo mismo que el original hace en `$04CD`: pedir al firmware que quite
la ROM baja con su propia llamada (`KL L ROM DISABLE`, `$B909`), buscar la
lámina en la tabla con `$268C`, preparar los gráficos con `$06D8`, y dibujar
con `$0538`, que pone las cuatro tintas y salta al intérprete de órdenes de
`$3F20`. Al terminar levantan una bandera y se quedan dando vueltas. El número
de lámina va dentro de esos bytes, para no escribir registros con la máquina
en marcha. Megacorp de CPC lleva el mismo intérprete —un 98 por ciento de
bytes iguales, y las cuatro rutinas en las mismas direcciones—, así que sirve
tal cual.

### El reloj de las pruebas contaba de más

Midiendo lo de arriba salió algo que no tenía que ver con el original: láminas
muy distintas nuestras daban **el mismo número de ciclos con diferencias de
diez**, y la misma lámina variaba hasta tres décimas de una vuelta a otra.

La causa: la prueba de las 196 ponía un punto de parada en el bucle donde la
compilación se aparca, en la creencia de que así el contador se paraba con la
máquina. **No se para.** Fuera del modo paso a paso del emulador el punto de
parada salta y la máquina sigue; comprobado leyendo el contador con la máquina
ya aparcada, que subía unos 2,4 millones de ciclos por segundo de reloj. Y el
modo paso a paso no es salida: `run` en ese modo **tumba el emulador** —se
corta la conexión y el proceso desaparece—. Aquí se había escrito que «o no
vuelve o va cientos de veces más lento», y eso lo daba otra cosa: ver «El
indicador del modo paso a paso», más abajo. Así que se contaba también lo que pasaba entre que la lámina acababa y la
prueba miraba la bandera, que era cada medio segundo: **hasta tres décimas de
más en cada lámina**.

El arreglo es mirar la bandera cada centésima (`finished_after` en la prueba).
Con eso **la misma lámina da exactamente el mismo número de ciclos vuelta tras
vuelta**, y lo que queda de error es como mucho un cuadro, veinte milisegundos.
megacorp2 #29, que medía 3,02, son en verdad 2,90.

Lo que eso cambia de lo de arriba: nada de lo grande. Las mejoras del relleno
son de segundos en láminas de 15 a 35, muy por encima de tres décimas. Lo que
sí queda en duda son las diferencias pequeñas, como el 4 por ciento del tendido
desenrollado; pero se devolvió por memoria, no por eso. Y la comparación con el
original se hizo con el reloj ya arreglado en los dos lados.

Dos cosas que quedan: **cuidado con pedir los registros muy a menudo**, que
cada diez milisegundos tumba el emulador y en cambio leer un byte de memoria
no; y **las pruebas de todas las láminas del Spectrum y del MSX** miran la
bandera cada décima, así que cuentan hasta una décima de más. No cambia nada
de lo que se dijo con ellas, pero conviene pasarles el mismo arreglo la
próxima vez que se toquen.

**Pasado.** La espera del CPC es ahora `Session.seconds_until`, en
`tests/emulator.py`, y la usan las tres. No es `wait_for` con otro intervalo:
`wait_for` pide los registros en cada vuelta, y pedirlos cada centésima es
justo lo que tumba el emulador; `seconds_until` sólo lee el byte.

## Los cuatro marcadores que son del intérprete

Los marcadores 0 a 3 y los contadores 0, 126 y 127 **no son de la aventura**,
son del intérprete, y de eso no hacíamos nada. No es un detalle: *Los pájaros
de Bangkok* pregunta `SET? 0` quince veces para escribir por dónde se sale, y
ninguna de esas líneas podía ejecutarse nunca.

Lo que hace cada uno está escrito en el manual del decompilador de referencia,
pero lo que está aquí está **medido en la máquina**, sobre las aventuras de
verdad: la tabla de marcadores de MegaCorp está en `$A483` y la de contadores
en `$A403`, y se encontraron buscando el dibujo de bits que su propia tabla de
alta prioridad pone al empezar.

| | qué es | cómo se comprobó |
|---|---|---|
| marcador 0 | una localidad acaba de describirse | en `$A483` vale 1 nada más arrancar, y la aventura sólo hace `RESE 0` |
| marcador 1 | este sitio tiene luz | vale 1 también, y ninguna de las ocho lo pone |
| marcador 2 | el jugador lleva algo que alumbra | `12 SWAP 9 RESE 2` al apagar la linterna en Bangkok2 |
| marcador 3 | no decir la puntuación al acabar | cinco aventuras lo ponen; las dos de *vajillas* no, y tienen los tres mensajes de puntuación |
| contador 0 | la puntuación | |
| contadores 126 y 127 | los turnos, bajo y alto **en ese orden** | 126 sube de uno en uno con cada orden; el de referencia los tiene al revés |

**A oscuras** —los marcadores 1 y 2 a cero— el original no describe: borra la
ventana de la lámina, dice el mensaje 251 y **no pone el marcador 0**, porque
no ha descrito nada. Las tres cosas están medidas apagando la luz a mano en la
memoria de MegaCorp.

**Lo que hay en el suelo** lo nombra el intérprete detrás de la descripción:
el mensaje 253 y luego los nombres con una coma entre ellos, todo en la misma
línea. `Tambien puedo ver:un disco metalico,una pistola`. Y `LIST` escribe
igual —`Llevas un libro,una camisa`—, y cuando no hay nada que nombrar escribe
la palabra que la aventura da para eso.

De ahí salió otra: **`MESS` no termina la línea**. Si la terminara, el 253 y
los nombres no podrían salir juntos. Por eso las aventuras dicen `LF` cuando
quieren un salto, y por eso MegaCorp rellena sus descripciones con treinta y
dos asteriscos. El nuestro saltaba de línea en cada mensaje y en cada
descripción.

Y la peor de todas: **el turno se cuenta después de la tabla de alta
prioridad**, no antes. MegaCorp monta la partida entera dentro de
`IF ( 0 EQU? 126 )`; contando antes, ese `IF` no se cumple jamás, no se ponen
sus banderas ni sus contadores, y la línea siguiente de la misma tabla ve
`0 EQU? 1` y mata al jugador. **Nuestra compilación de MegaCorp I era
injugable**: decía «Tomandome por uno de sus enemigos... No tengo ninguna
oportunidad!» en la primera jugada. Ahora dice «La cabina de la nave.»

Todo esto está en el Z80 y en `runGAC.py`, que iba por su lado en tres de las
siete, y probado en [`test_markers_z80.py`](../tests/test_markers_z80.py): once
pruebas que no leen la pantalla donde no hace falta, porque una condición que
acaba la partida dice lo que el intérprete creía mucho mejor que una pantalla
de letras.

### Dónde se parten las líneas, que es del autor y no nuestro

El texto del original son palabras con un terminador de tres bits cada una, y
las imprime de una en una, así que **un signo de puntuación acaba una palabra
igual que un espacio**. El nuestro sólo partía en el espacio, y eso no es una
sutileza: MegaCorp escribe sus localidades como `La cabina de la nave.
Salidas:Sur.` y detrás una regla de treinta y dos asteriscos, contados para
llenar un renglón exacto. Partiendo sólo por espacios eso es una palabra de
cuarenta y cuatro letras, y salían dos renglones desiguales en vez de los tres
que su autor dibujó.

De ahí salió una segunda, más pequeña y de la misma familia: **un renglón que
se llena solo no se acaba otra vez**. La regla de asteriscos termina justo en
el borde, y el original pone el `>>>` en el renglón siguiente sin dejar uno en
blanco; el nuestro dejaba uno.

Con las dos, la pantalla de MegaCorp sale letra por letra como la suya:

    La cabina de la nave. Salidas:
    Sur.
    ********************************
    >>>

Queda **una diferencia de un carácter**, y queda apuntada porque no la he
sabido explicar: cuando una palabra no cabe y salta de renglón, el original
deja a veces el espacio que la separaba al principio del renglón nuevo —`La
bodega de carga de la nave.` y debajo ` Salidas:Norte.`— y el nuestro lo deja
al final del anterior, donde no se ve. Es una sangría de un espacio en un
punto de corte, y se ha vuelto a ver en las pruebas de `TEXT`, así que es
constante y no una casualidad de una pantalla.

**Cerrada.** Es la regla de «Cómo corta las líneas el original», más abajo,
leída en `$778A`: el espacio va detrás de un punto, que también es separador,
así que es un espacio de una tirada y baja con la palabra. Lo comprueba
`test_a_space_after_a_mark_goes_down_with_the_word`, con el texto de la sala 2
de megacorp1 tal cual: sale ` SALIDAS:NORTE.` como en el original, y se ha
visto fallar, con `SALIDAS:NORTE.` sin el espacio, al quitar la regla de
`word_print` en `z80/common/textout.asm`.

La prueba es [`test_wrapping_z80.py`](../tests/test_wrapping_z80.py), con la
forma de MegaCorp escrita como MegaCorp la escribe.

### El texto, palabra a palabra

Un mensaje se desempaquetaba entero en `text_buffer`, 256 bytes, y sólo
después se imprimía. Nada comprobaba que cupiera, y uno de 380 caracteres
pisaba el código que hay detrás del búfer: la máquina se cae y no llega a
sacar el *prompt*. Ninguna de las aventuras originales puede hacerlo —las ocho
llegan como mucho a 255 caracteres—, pero una fuente nuestra sí.

**Ese 255 es del editor de GAC, y está leído en su código**, en la versión de
CPC, que trae el editor entero dentro de `CARVALHO.FAC`. La rutina que lee una
línea recibe el tope en E, compara la longitud con él y, si ya está lleno,
pita (`LD A,7 / JP $BB5A`) en vez de aceptar la letra. Tiene varias entradas,
una por tope —de 3, 4, 16, 36 y 255—, y la de 255 (`LD E,$FF` en `$198C`) es la
que usa la entrada de un mensaje en `$3129`, y otros ocho sitios del editor.
Aparte hay otra comprobación, que es la que tiene mensaje propio: después de
empaquetar, cuenta los bytes empaquetados del registro y si pasan de 255 —no
caben en su byte de longitud— dice «Too long... Please shorten the message.».
Esa cuenta es de bytes empaquetados, no de caracteres, y no se alcanza nunca
desde el teclado: en las ocho aventuras hay 1.329 textos, ninguno pasa de 255
caracteres, cinco están entre 251 y 255, y el que más ocupa empaquetado son
106 bytes. Las salas, además, guardan su longitud en dos bytes. Lo de las
versiones de Spectrum no está leído, porque sus instantáneas no traen el
editor, pero sus datos dicen lo mismo.

Lo que se pensó primero era que la construcción se negara a un texto que no
cupiera. Lo que se hizo, por idea de Sergio, es mejor: **desempaquetar y
imprimir a la vez, palabra a palabra**, de modo que en memoria no hay nunca más
que una palabra. Así no hay límite ninguno.

Cómo, porque tiene un detalle: una pareja del compresor puede cruzar el límite
entre dos palabras (`o d` puede salir de `o␣` y `␣d`), así que no se puede
parar la expansión al final de una palabra. Se hace al revés: `expand_code`
suelta cada carácter en cuanto sale hacia `text_put`, que lo guarda en la
palabra en curso y, cuando llega lo que la termina —un espacio, un signo o un
cambio de tinta—, pregunta si cabe en la línea, la imprime y sigue. Es la
misma regla que tenía `print_text`, que ahora se apoya en lo mismo carácter a
carácter.

La palabra se guarda en **el ancho de la línea más uno**, y con eso basta para
cualquier palabra: una tan larga no cabe en la línea empiece donde empiece, así
que lo que le pasa —línea nueva, salvo que el cursor esté al principio de una—
se decide igual con su primer trozo que con ella entera, y el resto sólo hay que
imprimirlo. Para eso está `held_going_on`.

Tres cosas se comprobaron antes de tocarlo: que imprimir no pagina ningún banco
—sólo lo hacen el desempaquetador, las láminas y la sala a oscuras—, porque
ahora se imprime a mitad de leer el almacén de texto; que `word_ends_at` sólo
mira el carácter y no el texto que lo rodea; y que ninguna prueba leía el
búfer viejo.

Lo que dio:

- **Las 41 pruebas de texto de todas las máquinas salen igual**, que es lo que
  dice que el corte de línea no ha cambiado.
- **Una prueba nueva** (`test_wrapping_z80`): un texto de más de 600 caracteres
  con una palabra de 45 letras, más larga que la línea. Con el código nuevo sale
  exactamente como debe; con el viejo la pantalla se queda vacía.
- **Memoria**, porque el búfer pasa de 256 bytes al ancho más uno —de 33 en el
  Spectrum a 65 en el PCW— y el código sale unos bytes más corto. En el
  Amstrad de cinta con música, que tenía 14 bytes libres, quedan 235; en el
  Next, delante de la pared de `$A000`, de 58 a 267, contando ya el arreglo de
  aquí abajo.

**Y destapó un fallo que llevaba ahí desde el principio.** Con el búfer fuera,
todo lo que va detrás se corrió 221 bytes, y cuatro pruebas de rellenos del MSX
empezaron a fallar. No era el texto: el relleno del MSX, y el del Spectrum, el
Next y el PCW, que son primos, buscaban en sus tablas de máscaras así:

    ld      de, bit_masks
    add     a, e            ; el índice, al byte bajo
    ld      e, a            ; y el acarreo no pasa a D
    ld      a, (de)

Eso funciona mientras la tabla no quede al final de una página de memoria. Si
queda, el índice da la vuelta y se lee un byte del principio de esa misma
página. Nadie lo había visto porque ninguna tabla había caído en el borde; al
moverse la memoria, una del MSX cayó. Eran catorce búsquedas en los cuatro
rellenos —el del Amstrad no, que ya usaba `table_byte`, que sí arrastra el
acarreo—, y las catorce llevan ahora `jr nc, $+3 / inc d`. Dos bytes cada una,
y unos relojes que no se notan.

Se buscaron con un rastreo de todo `z80/` por la forma `ld de|hl, tabla / add
a, e|l / ld e|l, a` sin nada que recoja el acarreo detrás; las otras búsquedas
que salieron ya lo recogían, con `jr nc` o con `ld a, 0 / adc a, h`.

### La palabra de «nada», que no está en la base de datos

Es el único texto de una aventura que **no vive en su base de datos**: el
intérprete se guarda unas pocas palabras suyas en letras normales, cada una
acabada en `$FF` y un retorno de carro —una queja de memoria llena, la palabra
que escribe cuando no llevas nada, y lo que pregunta el nombre—. Se demostró
cambiándola en la máquina: MegaCorp pasó a contestar `Llevo conmigo:XXXX`.

Y por eso las ocho no dicen lo mismo, que es lo bonito del hallazgo:

| aventura | dice |
|---|---|
| megacorp1, megacorp2 | `nada` |
| vajillas1, vajillas2 | `NADA` |
| Bangkok1, Bangkok2, quijote1, quijote2 | `nothing` |

Cuatro adaptaciones al castellano y **dos no llegaron a traducir la palabra**.
`deGAC` la lee ahora buscando la queja de memoria llena como mojón y tomando
lo que hay veinte bytes más allá, de modo que no depende de una dirección
fija. De las versiones de Amstrad y de Commodore no se sabe dónde está; si no
aparece, se queda en `Nothing` y se dice.

**La del Amstrad ya se sabe**, y no está con las otras: el intérprete la
imprime donde la usa, en línea. En $05A4 de las tres aventuras de Amstrad que
tenemos: `call $0560`, que lista lo que se lleva, `ret nz` si listó algo, y
`call $2240` --que imprime las letras que siguen a la llamada hasta el $FF y
sigue detrás-- con `nothing`. Su `Memory full` también está, pero con código
detrás y no la palabra. Las tres dicen **`nothing`**, en minúscula: ninguna de
las tres la tradujo, y `deGAC` las dejaba en el `Nothing` de oficio. Ahora la
busca también con ese mojón; prueba en `test_interpreter.py` y, sobre el disco
de Bangkok, en `test_disk.py`. La del Commodore sigue sin buscar: el C64 está
aparcado.

### `TEXT` y `PICT`, medidos y hechos en las cinco

Se escriben en `vm_graphics` y no los lee nadie. Ya está medido qué hacen, y
resultó más sencillo de lo que parecía.

**Cómo se midió**, porque ninguna de las ocho deja ejecutarlos a voluntad: se
escriben dos condiciones nuestras encima del principio de la tabla de baja
prioridad de MegaCorp, en la memoria de la máquina, con un cero detrás para
que no se lea a medias lo que quedaba de la suya. `PULSA` hace `TEXT` y `ABRE`
hace `PICT`. Los opcodes son los del original, que son los nuestros, y de paso
quedó comprobado: lo que había allí era `80 08 30 3E 80 EF 16 3B 36 2B 3F`,
que es `IF ( VERB 8 ) MESS 239 WITH LIST WAIT END`, el inventario.

Lo que hacen:

- **`TEXT` no borra nada ni mueve el cursor.** La pantalla se queda exactamente
  como estaba; lo único que cambia es que **la ventana de texto pasa a ser la
  pantalla entera**, y eso se ve en cuanto algo se imprime: el texto arrastra
  la lámina hacia arriba al desplazar, en vez de desplazar sólo el trozo de
  abajo.
- **Con `TEXT` puesto, una localidad nueva no dibuja su lámina.** Se va al sur,
  se describe la bodega, y la lámina de la cabina sigue subiendo.
- **`PICT` tampoco hace nada en el momento**: no redibuja ni borra. La pantalla
  sigue desplazándose entera.
- **La ventana vuelve a su sitio cuando se dibuja una lámina**, que con `PICT`
  puesto es la siguiente localidad que se describa.

O sea que, puesto en nuestros términos, no hace falta ninguna orden de «volver
al modo lámina»: **`TEXT` pone la ventana en cero y dibujar una lámina la
devuelve a la altura de la lámina**. `PICT` no es más que la bandera que
permite volver a dibujarlas, que es justo lo que `vm_graphics` ya es.

**Y está hecho, las dos mitades y las cinco máquinas.** La mitad común —con
`TEXT` no se dibuja lámina— la decide `describe_location` mirando
`vm_graphics`, que antes se escribía y no leía nadie. La otra mitad, la
ventana, es de cada máquina:

| máquina | la ventana | por qué |
|---|---|---|
| Spectrum | **sí** | |
| MSX | **sí** | dos bytes, el primer renglón y cuántos se mueven. Le faltaba lo otro: **era la única de las cinco sin prueba**, que es lo mismo que no saberlo. Ya la tiene, `test_textmode_msx.py`, y comprobado que sirve: capando `text_window_all` falla |
| Amstrad | **sí** | tardó por falta de sitio: el intérprete acababa a 38 bytes de un escalón de página. El escalón se quitó y el texto palabra a palabra devolvió el búfer; la ventana costó 65 bytes |
| Next | **sí** | tardó por una pared en `$A000` que resultó ser la máscara del relleno: ver «La pared del Next». Costó 54 bytes y cabe debajo de la máscara |
| PCW | **sí** | sus dos mitades viven en bancos distintos y sólo una está en el mapa; el renglón que cruza de una a otra pasa por un búfer. Costó 49 bytes |

**En el Amstrad salió más fácil que en el Spectrum.** Allí la ventana dejó
de caber en un tercio de la pantalla y el desplazamiento tuvo que ir fila a
fila. En el Amstrad cada una de las ocho líneas de píxel de un carácter guarda
las veinticinco filas seguidas, así que desplazar sigue siendo un `LDIR` por
línea; lo único que cambia es que el origen, el destino y la cuenta se sacan de
`text_top` en vez de ser constantes. Con MegaCorp II quedan 175 bytes libres en
la cinta con música, 228 sin ella y **65 con el intérprete de ruidos**, que es
ahora el caso más justo. `test_textmode_cpc.py` es la prueba del Spectrum en
un Amstrad; con el `screen.asm` de antes falla la mitad de la ventana y pasa la
de las láminas, que es lo que había.

En el Spectrum el desplazamiento pasó a recorrer los renglones de uno en uno,
porque el truco de un solo `LDIR` sólo vale mientras la ventana cabe en un
tercio de la pantalla. En el MSX bastaron dos bytes, el primer renglón y
cuántos se mueven.

**En el PCW salió más fácil de lo que se había apuntado.** Se temía que la
dirección de un renglón tuviera que llevar su banco consigo, y no hace falta:
el cursor vive siempre en la mitad del texto, así que escribir no cambia, y lo
único que cruza la juntura es el desplazamiento. Cada mitad sube un renglón en
una sola copia —márgenes incluidos, que son oscuros en todos los renglones, y
eso simplificó de paso el desplazamiento de siempre, que iba renglón a
renglón—, y el renglón que sale por arriba del texto pasa por un búfer de 720
bytes en `$E000` para ser el último de la lámina: la máscara está en `$C000` y
una partida se prepara en `$D000`.

**Y destapó un fallo que habría quedado escondido.** Con la lámina a un punto
de ancho, la lámina es la mitad de ancha que el texto, y `gfx_clear` sólo
pintaba de blanco sus propias columnas: lo que `TEXT` hubiera subido a los
lados se quedaba ahí debajo de la lámina siguiente. Ahora la mitad entera se
pone oscura antes. Medido: 4096 píxeles encendidos al lado de la lámina sin el
arreglo, ninguno con él. [`test_textmode_pcw.py`](../tests/test_textmode_pcw.py)
tiene las dos pruebas de las otras máquinas y una tercera para esto, y las dos
que tocan la ventana fallan con el código de antes.

La prueba del PCW enseñó además dos cosas de las pruebas. Una lectura larga
de memoria con la máquina parada hace que la primera tecla mandada justo
después se pierda —probado orden a orden: es la lectura, no la parada ni los
puertos—, y medio segundo de máquina en marcha lo cura. Y la otra no es de
las pruebas: ver «Las teclas que se solapan, que ya no se pierden».

**En el Next la pantalla entera no se ve nunca de una vez**: son tres trozos
de dieciséis kilobytes y sólo uno está en `$C000`. Así que desplazarla toda no
es copiar trozo a trozo, sino recorrer las seis páginas de 8K de la capa 2
con la siguiente vista detrás: cada copia trae las líneas de su página desde
ocho más abajo, y esas ocho son el principio de la página siguiente, que no
se escribe hasta la vuelta de después. La última vuelta lee ocho líneas de
una página que no es de la capa 2, que no hace daño, y son justo el renglón
que se borra. Escribir en el texto no cambia: el cursor vive siempre en los
renglones de abajo, así que devolver la ventana no tiene nada que corregir.
Comprobado aparte que la lámina sube renglones enteros exactos a través de
las tres fronteras de página y que el renglón de abajo sale limpio.
[`test_textmode_next.py`](../tests/test_textmode_next.py) es la prueba del
Spectrum en un Next, y con el `screen.asm` de antes falla la mitad de la
ventana.

Queda debajo de la máscara: 218 bytes libres sin música y **158 con música y
efectos**, que es el caso más justo. Los tres kilobytes de encima de `$B200`
siguen sin usar, para cuando haga falta.

Se ve en la presentación de MegaCorp, que es lo que lo motivó: antes se perdía
desplazada en ocho renglones y ahora sale letra por letra como la del
original. La prueba es [`test_textmode_z80.py`](../tests/test_textmode_z80.py).

**Lo que queda de aquí**, apuntado y medido y no hecho:

- ~~**La pared de los `$A000` del Next.**~~ **Entendida**, y era nuestra: ver
  «La pared del Next».
- ~~**Un mensaje se desempaquetaba en `text_buffer`, que son 256 bytes, y nadie
  comprobaba que cupiera.**~~ **Hecho**, y no como se pensaba aquí: ver «El
  texto, palabra a palabra».
- ~~**El 464 sigue sin sitio.**~~ **Resuelto**, y por donde aquí se decía: el
  código se baja de `$4000` y la base de datos se queda con todo lo de
  arriba. Ver «El Quijote en un 464, con el mapa del revés», y «Lo que costó,
  y de dónde salió el sitio» para lo que faltaba, que era que ese mapa
  admitiera música. Lo que sigue es lo que se hizo antes de eso, y explica
  por qué MegaCorp II cupo sin cambiar el mapa: el relleno rápido costó unos
  300 bytes y se
  pagaron rascando: se quitó el `ALIGN 256` de la base de datos, que nada
  necesitaba, y el intérprete de ruidos dejó de viajar cuando la aventura no
  pide ninguno —ninguna de las ocho de 1986 puede pedirlo, porque `SOUND` y
  `QUIET` son opcodes nuestros—, que son 163 bytes en esa máquina. Con eso
  MegaCorp II vuelve a caber, con 133 de margen. El Quijote no: le faltan 410
  y 279, y para eso hace falta o bancos, que un 464 no tiene, o bajar el
  código debajo de `$4000` y dejarle a la base de datos los veintiocho
  kilobytes de `$4000` a `$B100` —con la pega de que la rutina de cinta
  tendría que vivir arriba, porque el firmware tapa la ROM baja mientras
  dura—.

- **El Amstrad va justo, y hay un escalón.** Está medido, aventura por
  aventura, antes y después de meter los marcadores, con un árbol aparte en el
  commit anterior para poder comparar.

### La pared del Next, que era la máscara

Durante mucho tiempo pareció un misterio de la máquina o del emulador: el
`.nex` llevaba los bytes que pasaban de `$A000` —leídos del fichero, estaban
bien— y en la máquina esa memoria se leía a ceros. No era ninguna de las dos
cosas. **En `$A000` vive la máscara del relleno**, cuatro kilobytes, y
`gfx_clear` la borra entera cada vez que se borra una lámina. El código que
creciera hasta ahí llegaba bien y el primer cuarto lo machacaba.

Comprobado: un build de prueba con una marca en `$A020` y otra en `$B300`,
cargado con el procesador parado. Las dos marcas están en memoria; después de
dibujar la primera sala, la de `$A020` son ceros y la de `$B300` sigue.

Nada lo avisaba porque el build del Next sólo comprobaba no llegar a la pila;
el banco de pruebas de láminas sí comprobaba la máscara, y el juego no. Ahora
`game.asm` tiene el mismo `ASSERT last <= MASK`, así que un intérprete que
crezca de más no se construye en vez de romperse en la primera sala.

**El mapa de verdad** de `$8000` a `$BFFF`, que es lo que nunca se pagina:

| desde | qué |
|---|---|
| `$8000` | el intérprete; le quedan unos doscientos bytes hasta la máscara |
| `$A000` | la máscara del relleno, que se borra con cada lámina |
| `$B000` | la tabla de las interrupciones en modo 2, y en `$B1B1` su rutina: sólo con música, y puestas al empezar |
| `$B200` | **libre**, unos tres kilobytes hasta la pila |
| `$BF00` | la cima de la pila, que baja |

La pila se midió para saber cuánto de eso es de verdad libre: rellenado con un
byte testigo, dibujando todas las láminas de MegaCorp I, MegaCorp II, el
Quijote II y las Vajillas I, baja 34 bytes como mucho, y jugando otros tantos.
Aunque se le dejara un kilobyte entero, quedan más de dos libres.

Así que el Next no está lleno: está lleno **debajo de la máscara**. La ventana
de `TEXT`, que es lo que chocó con la pared, al final cupo debajo —54 bytes—,
así que el hueco de arriba sigue entero.

## Los caracteres latinos, que ya se ven

El diseño estaba desde el principio —un código y un glifo por carácter usado,
sin reservar nada para alfabetos que la aventura no escribe— y faltaba la mitad
que se ve: la fuente que una aventura hereda de 1986 no tiene ni una letra
acentuada, así que la á recibía su código y salía **en blanco**.

Ahora se construyen, y no a mano: una letra acentuada es la letra de la propia
aventura con una marca encima, de modo que se parece a la tipografía en la que
está; lo guardado son las cinco marcas y la cedilla, y Unicode dice qué letra y
qué marca lleva cada carácter. La ¿ y la ¡ son la ? y la ! dadas media vuelta.
El cómo y el porqué están en [`textos.md`](textos.md).

Y la otra mitad, la de entrada: **al vocabulario se le caen las marcas**, porque
ningún teclado de estas máquinas tiene tecla de acento y un vocabulario que
dijera ARAÑA no lo podría escribir nadie. Se guarda ARANA; el fuente sigue
diciendo ARAÑA. Dos palabras que se queden en la misma se cazan al construir.

Comprobado con una aventura escrita en español de verdad, impresa por el Z80 en
un Spectrum y leída de vuelta de la pantalla con su propia fuente, que es la
única manera de saber que los códigos, los glifos, el empaquetado y la
impresión están de acuerdo.

Y para quien escriba una aventura en vez de decompilarla, **una fuente suya**,
en lo que la tenga: un volcado de ocho bytes por carácter, con o sin dirección
de carga delante, con o sin la cabecera de AMSDOS, una fuente de consola PSF, o
**un PNG con las letras en una rejilla**, que es lo que un artista prefiere
dibujar, o **la fuente escrita como fuente**: una cabecera de C o un listado de
Z80, 6502, x86 o 68000, que es como se publican para que las use un programa.
un BDF, la ristra de VDU 23 de un BBC, el BASIC con `SYMBOL` de un Amstrad o
una fuente de consola PSF. Se mira el fichero y se averigua qué es.

Comprobado con una fuente de verdad, bajada de ZX Origins: de su ZIP entran
—dando todos la misma letra— el `.ch8`, el `.fnt` de Atari, el `.64c`, el
`.psf`, los cinco listados de `Source`, el `.bbc`, el `.bas`, el `.bdf`, la
hoja del GameBoy y hasta la imagen de muestra. Y de eso salieron tres fallos
que los ficheros inventados por mí no habrían encontrado nunca: el `&00` con
que escribe el hexadecimal un ensamblador de Z80, el signo de copyright en un
comentario —que hacía que el fichero no pareciera texto— y, el mejor, que
estos listados ponen en un comentario la letra que dibuja cada fila, así que
la línea de la llave abierta tiene una llave abierta y buscar las llaves de un
array de C sin quitar antes los comentarios encontraba ésa.

Cada letra se identifica por su casilla, y `layout` dice de una vez por dónde
empieza la hoja y cuántas casillas tiene. La que hay que dibujar es **Latin-1**:
todas las letras que esto imprime están ahí, en el sitio donde las pone
cualquier editor de fuentes, así que el artista no tiene que oír hablar de los
códigos de reGAC. Y como se sabe cuántas casillas son, una hoja dibujada al
doble o al triple se lee igual, que es lo que hace que sirva: nadie dibuja a
ocho píxeles por letra. `first` y `order` quedan para lo demás —un C64 no
guarda las letras en el orden del ASCII. O letra a letra en el
propio fuente, nombrando el carácter por su número o por sí mismo. Lo que el
autor dibuja se usa tal cual; sólo se compone lo que no trae.

**Y el juego de caracteres pasó a ser fijo**, que es lo que arregla el fallo de
diseño que asomó al medirlo: numerando los códigos por frecuencia, al compresor
le quedaban los que el alfabeto no se llevara, así que una aventura en
castellano con acentos tenía menos parejas que una en inglés y una en catalán
menos todavía. El idioma no debe ser un handicap. Ahora hay treinta sitios
debajo del espacio para las letras que el ASCII no tiene, el ASCII tal cual del
32 al 127, y del 128 para arriba 128 parejas para todo el mundo; el 0 es el
nulo y el 1 está reservado para un cambio de color. El reparto está en
[`textos.md`](textos.md).

Cuesta un 2,1% de la base de datos —de 305 a 565 bytes por aventura— y devuelve
dos tablas: como un código desde el espacio es su propio ASCII, se van del
binario la de 96 bytes que traducía tecla a código y la de los diez dígitos, y
con ellas una búsqueda por cada tecla. De paso la fuente deja de depender de qué
palabras salgan en la aventura: es una hoja de letras en sitios fijos, que es lo
que un artista puede dibujar una vez y reusar.

La compresión sigue siendo la misma y la mejor de las que se midieron —parejas
recursivas, contra el 57% de Huffman y el 84% de las abreviaturas al estilo
PAW—, ahora entre el 50% y el 55%, y gasta las 128 parejas siempre: lo que la
limita es el byte y no el texto.

## La música, que sonaba y se quitó

**Decisión tomada: fuera el reproductor de Arkos y fuera el opcode `MUSIC`.**
Los efectos se quedan, con `SOUND` y `QUIET`, y los hace el motor que ya
teníamos: el altavoz de un bit donde lo hay y el chip de sonido en el Amstrad,
que no tiene altavoz, **leyendo la misma tabla y con los mismos números**.

Lo que se quitó, contado para que se sepa qué había:

| | |
|---|---|
| el reproductor | 2892 líneas de Z80 de terceros, en `z80/arkos/` |
| lo nuestro alrededor | `common/music.asm`, `common/im2.asm`, `common/ticker.asm` y las cuatro `interrupt.asm` |
| pruebas | 16 módulos |
| herramientas | `arkos.py`, el exportador, `music-tool`, `--music-defs` |
| del lenguaje | `MUSIC`, el bloque `/MUSIC` y `music-buffer` |

Lo que se queda: `common/beep.asm`, `common/effects.asm`, `cpc/ay.asm` y sus
tres pruebas. **309 líneas contra 2892.**

**Por qué.** No era fidelidad —el GAC de 1986 no tenía música— sino una
función añadida, y su coste era continuo: dos vías de sonido en lugar de una,
un exportador que **nunca se había corrido con su binario de verdad**,
dieciséis módulos de prueba, páginas y bancos reservados en cuatro máquinas, y
el clic de tecla del Amstrad atascado precisamente porque el reproductor era
dueño del AY. Eso último se arregla solo al quitarlo.

**Lo que no se tocó a propósito:** el formato binario. Su sección `music` ya
estaba vacía —las melodías eran fuente de ensamblador, nunca datos— y dos
bytes de su cabecera quedan siempre a cero. Cambiarlo obligaría a romper la
versión del formato, y eso merece ir solo y no dentro de este cambio.

**Y el hueco del opcode.** `$40` era `MUSIC`. Se deja apuntando a `op_nop` en
vez de renumerar `SOUND` y `QUIET`, porque renumerar rompería en silencio
cualquier `.rgac` construido antes: así, una base de datos vieja lee ahí un
opcode que no hace nada y deja su argumento en la pila, que la condición
siguiente vacía de todos modos.

**Lo que costó quitarlo, apuntado para la próxima.** Los bloques `IFDEF
WITH_MUSIC` se cortaron con índices sobre el texto, y en
`spectrum/test_conditions.asm` el corte se llevó por delante el `DEVICE` del
principio y el `SAVESNA` del final, que estaban en la rama `ELSE` del mismo
condicional. **El fichero seguía ensamblando** —no escribía nada— y las
pruebas corrieron contra la instantánea vieja: ocho fallos que no tenían nada
que ver con el opcode. La comprobación que lo encontró, y que vale la pena
repetir en cualquier poda de condicionales, es contar las directivas del
ensamblador antes y después:

    for f in $(git diff --name-only -- 'z80/*.asm'); do
      for d in DEVICE SAVESNA SAVETAP SAVEBIN ORG ASSERT ENT PAGE SLOT; do
        a=$(git show HEAD:$f | grep -c "^\s*$d")
        b=$(grep -c "^\s*$d" $f)
        [ "$a" != "$b" ] && echo "$f  $d: HEAD=$a ahora=$b"
      done
    done

Y luego mirar una por una las que bajaron: unas son la música y otras no.

## El zumbador, y el clic que hacía el original

El manual no menciona el sonido en ninguna parte, así que había que mirar el
código. En las cuatro instantáneas de GAC que tenemos hay **exactamente una**
llamada al zumbador de la ROM, en el $820B, y lo que la rodea es el editor de
línea: coge la duración de PIP —la variable del sistema que usa el clic de
teclado de la propia ROM, y que GAC pone a 75—, pide un tono de $00FF y pita.
O sea que **GAC hacía clic con cada tecla**, y ahora esto también.

**El motor son 111 bytes**, tabla incluida. Un altavoz de un bit hace una nota
igual en todas partes —darle la vuelta al bit, esperar, y otra vez— y lo que
cambia es qué bit de qué puerto y qué más hay en ese puerto que no se puede
tocar, así que cada máquina dice tres cosas: `BEEP_BIT`, `BEEP_BASE` y
`BEEP_OUT`.

| máquina | dónde está el altavoz | lo que comparte |
|---|---|---|
| Spectrum y Next | bit 4 del $FE | el borde, que por eso se guarda en memoria |
| MSX | bit 7 del puerto C del 8255 | el motor del casete, la salida de cinta y el led de mayúsculas |
| Amstrad | no tiene: el sonido es el AY | — |
| PCW | tiene zumbador, pero no sabemos aún cómo se toca | — |

De esa tabla **sólo queda en uso la primera fila, y sólo en el 48**: donde hay
chip suena el chip, que es `common/ay.asm`. El altavoz del MSX estuvo escrito
y funcionando en `z80/msx/beep.asm`, y se quitó al pasar esa máquina al PSG;
la fila se queda aquí porque el bit y lo que comparte son lo que costaba
averiguar, y el fichero está en el historial si alguna vez hiciera falta.

Como el puerto del Spectrum no se puede leer, el borde que se puso la última
vez se guarda en `gfx_border` y sale otra vez con cada vuelta del altavoz; si
no, un clic dejaría el borde negro.

**Cinco efectos**, que es lo que una aventura de las de entonces llegaba a
querer: algo cogido, algo rechazado, una puerta, una caída y un aviso. Cada uno
son tres bytes —tono de salida, cuántas vueltas dura y cuánto se mueve el tono
en cada una—, y duran entre una vigésima y una décima de segundo. Un tono más
grande es una nota más grave, y el paso se para en los extremos en vez de dar
la vuelta: un blip que se salía por abajo volvía convertido en el gruñido más
grave que hay.

**`SOUND n` elige solo**: si la versión lleva el reproductor con efectos, suena
por el AY; si no, suena por el altavoz. Los números no coinciden entre los dos
—el banco del tracker es del autor y la tabla del zumbador es nuestra—, y eso
es inevitable: son sonidos distintos hechos con cosas distintas.

**Lo que falta aquí**:

- **El PCW, y esto ya está medido.** El emulador **no emula sonido de PCW
  ninguno**, así que ni se puede encontrar el zumbador a base de probar ni se
  podría comprobar nada que escribiéramos para él.

  Cómo se midió, para no repetirlo: ZEsarUX sabe volcar el audio a fichero
  (`--aofile`), y eso da un oráculo de «¿ha sonado algo?» que se validó con un
  Spectrum pitando —85 valores distintos de byte en la grabación— y con nuestra
  propia música de Arkos en el Amstrad —30—. Contra eso, en el PCW: las
  dieciséis órdenes numeradas del puerto $F8, de dos en dos, **silencio**; y un
  bit meneado en cada uno de los 71 puertos de los rangos $00-$0F, $A0-$AF,
  $D0-$EF y $F9-$FF, **silencio también**. La lista de chips de sonido que
  ZEsarUX dice emular tampoco menciona el PCW por ninguna parte. El build que
  hace la prueba es [`test_beeper.asm`](../z80/pcw/test_beeper.asm) y se queda
  ahí por si algún día hay con qué escucharlo.

  **Y lo dice el propio emulador**, que es mejor que deducirlo del silencio:
  su fichero `FEATURES` enumera del PCW los modos de vídeo y el controlador de
  disquete, y en toda la lista de sonido —AY, Turbosound, los DAC, General
  Sound, el del ZX80/81, el altavoz del Jupiter Ace, el i8049 del QL— **el PCW
  no aparece**.

  **Decisión: aparcado.** Tres motivos, de más a menos peso:

  1. **No se puede comprobar.** Lo que escribiéramos no se ejecutaría ni una
     vez.
  2. **No se puede escribir bien desde aquí.** No hay documentación del
     hardware del PCW en el repositorio: lo que hay son manuales de GAC.
  3. **No es un hueco de fidelidad.** GAC salió para Spectrum, Amstrad CPC,
     C64 y BBC —de ahí los formatos de fuente que lee `deGAC`—. **El PCW lo
     añadimos nosotros**, y `SOUND` y `QUIET` son opcodes nuestros; que el PCW
     los lea y no haga nada está documentado y es coherente.

  Y el que cierra: escribirlo a ciegas sería **un segundo trozo de código
  nunca ejecutado**, que es exactamente lo que es el C64 de `deGAC` y
  exactamente por lo que ese se aparca. No se añade el mismo problema en la
  misma frase en que se decide dejar de tenerlo.

  El camino, si alguna vez se quiere, es en este orden: **Joyce, el emulador
  de John Elliott, en `tools/`**, y sólo entonces buscar el puerto. Al revés no
  sirve. Lo que sí se sabe es que la máquina tiene interrupción de
  temporizador, así que el clic de tecla saldría gratis el día que se sepa el
  puerto. El build que hace el barrido se queda en
  [`test_beeper.asm`](../z80/pcw/test_beeper.asm).
- ~~El Amstrad sin música~~, **hecho**: ahí el único altavoz es el AY, así que
  ahora `SOUND` le pide la nota al chip en vez de menear un bit. Es el mismo
  baile del 8255 que ya hacía el teclado, y lee **la misma tabla** que el
  motor de un bit —las notas, las duraciones y los números son de la aventura y
  no de la máquina—: un tono de la tabla es medio periodo del chip, así que
  `SOUND 2` suena a lo mismo aquí.
- ~~El clic de tecla del Amstrad~~, **hecho**, y con él el chip en todas las
  máquinas que lo tienen: ver la entrada de abajo.

## El chip de sonido en las seis máquinas que lo tienen

Quitado el reproductor de Arkos, el AY se quedó sin dueño y **ocioso en tres
máquinas**: el 128, el +3, el MSX y el Next tenían chip y seguían haciendo los
ruidos meneando un bit. Ahora no: donde hay chip suena el chip, y el altavoz
de un bit queda para el Spectrum 48, que es la única sin uno.

**Lo que se hizo.** El motor del Amstrad —que ya existía, ya estaba probado y
ya leía la misma tabla— salió a `common/ay.asm`, y cada máquina dice sólo lo
que la diferencia, igual que `beep.asm` pide `BEEP_BIT`/`BEEP_BASE`/`BEEP_OUT`:

| máquina | cómo se llega al chip |
|---|---|
| 128, +3 y Next | `$FFFD` elige registro, `$BFFD` le da valor |
| MSX | `$A0` elige registro, `$A1` le da valor |
| Amstrad | el baile del 8255 que ya hace el teclado |

Y una cosa más que cada una dice, `AY_MIXER_KEEP`, que es lo único que no se
ve venir: **en el MSX el registro siete no es sólo el mezclador**. Sus dos bits
de arriba dicen hacia dónde miran los puertos del propio chip, que ahí son los
joysticks, y escribir el mezclador sin conservar el bit siete los daría la
vuelta. En el Amstrad pasa lo mismo con el bit seis, que ha de quedar a cero
porque el puerto A es la fila del teclado —ahí ya lo estaba—.

**El clic, que es lo que empezó esto.** En el Amstrad el único altavoz es el
chip, y `ay.asm` sólo viajaba con `NOISES`, que ninguna de las ocho del 86
pide: la máquina no clicaba. Ahora el fichero está partido por la mitad —no
son dos motores, es un `IFDEF`— y lo que viaja siempre es el acceso al chip y
una nota plana; la tabla y el reproductor que camina el tono siguen detrás de
`NOISES`.

**Lo que cuesta, medido sobre las ocho aventuras en un 464 de cinta**, libres
hasta `$B100`:

| | antes | ahora |
|---|---|---|
| megacorp1 | 1385 | 1282 |
| **megacorp2** | **14** | no cabe arriba |
| Bangkok1 / 2 | 2258 / 1378 | 2155 / 1275 |
| vajillas1 / 2 | 3260 / 3411 | 3157 / 3308 |

**103 bytes**, y megacorp2 —que tenía catorce— deja de caber de la manera
normal. No es un problema: `regac` lo construye del revés solo, como ya hacía
con los dos Quijotes, y ahí el intérprete tiene 6949 bytes libres y la base de
datos pasa de 20572 a 27392. **Salir del build alto da más sitio, no menos.**

**Cómo se comprueba.** Con el mismo oráculo que el Amstrad: el `--aofile` de
ZEsarUX y contar cuántos valores distintos de byte tiene la grabación. Y una
cosa que había que aprender: **cuánto se mueve el silencio es de cada
máquina**, tres formas en el Spectrum y el Next y una en el MSX, contra cinco
y tres con un efecto sonando. El dos que valía para el Amstrad estaba mal para
las tres, así que cada prueba mide su propio silencio primero y pide que todo
ruido lo supere. Está en `tests/test_sound_ay.py`, y en
`tests/test_sound_cpc.py` hay además la que importa de verdad aquí: que un
build **sin** `NOISES` —el que reciben las ocho del 86— sigue clicando.

Dos tropiezos que merecen quedarse escritos:

- **`IFNDEF` no ve un `equ`.** `common/ay.asm` daba un `AY_MIXER_KEEP` por
  defecto detrás de un `IFNDEF`, y sjasmplus mira los `DEFINE`, no las
  etiquetas: salió «Duplicate label». Ahora cada máquina lo dice y no hay
  valor por defecto, que además es mejor —no hay forma de olvidarlo—.
- **Un `IFDEF` se lee donde está.** El build de prueba del Amstrad ponía
  `IFDEF WITH_NOISES` sobre datos que están **antes** del `include` que define
  esa palabra, y salió silencio con la tabla pedida. Lo que hay que mirar ahí
  es `NOISES`, que la da la línea de órdenes y se conoce desde el principio.
- Y uno del MSX: la pila del build de prueba estaba en `$7FF0`, que en un
  Spectrum es RAM y ahí es la ROM del BIOS. Arrancaba, ponía su bandera y se
  moría en el primer `call`.

**Y un fallo que llevaba ahí desde que se escribió el motor del Amstrad**, que
salió al leerlo para sacarlo a `common/`: `ay_write` se carga BC, y en B está
**cuántas ondas dura el efecto**. Las tres escrituras que preparan el chip van
después de cargar B, de modo que lo que se descontaba no era la tabla sino lo
que la última de ellas dejara ahí —siempre el mismo número, para los cinco—.
O sea que en el Amstrad la promesa de que **la misma tabla dura lo mismo en
todas partes** no era cierta, y nadie se enteró: sonaba algo, la máquina
volvía, y eso era todo lo que las pruebas pedían.

La prueba que lo caza está en `test_sound_cpc.py` y merece contarse, porque
medir esto no es obvio. Lo que cuesta un efecto son dos cosas: lo que se tarda
en hablarle al chip, igual en cada onda, más dieciséis ciclos por cada vuelta
del bucle de espera, que es lo que cuenta el tono. Dos incógnitas, así que se
despejan con **dos** de los efectos —los dos menos parecidos de forma— y los
otros tres tienen que caer en su sitio. Con el arreglo caen dentro del 3 %;
con el fallo, **lo que cuesta una onda sale negativo**, que no es una cosa que
pueda ser, y los demás se van al 69 %.

Y un detalle de la medida que costó un rato: mirar `done_flag` cada cincuenta
milésimas deja hasta una veinteava de segundo de máquina girando en su bucle
de parada, y eso son doscientos mil ciclos que entran en la cuenta —del mismo tamaño que las
diferencias que se buscaban—. Por eso el build toca cada efecto **dieciséis
veces**: el hueco deja de pesar.

~~**Lo que queda de esto**, y es el paso dos: un cuarto byte que diga canal.~~
**Hecho**, y así quedó:

La tabla pasa de tres bytes a cuatro y el cuarto dice de dónde sale el ruido:
`tone`, `noise` o `both`. En el fuente es una cuarta columna que se puede
dejar en blanco —una línea de tres sigue valéndose y es un tono—, de modo que
ningún fuente escrito antes cambia. De los cinco de serie, la puerta y el
aviso pasaron a `both` y la caída a `noise`.

**En el Spectrum 48 el byte se lee y no se usa**, y eso no es un descuido:
allí no hay ni generador de tono ni de ruido, sólo un bit que se menea, y lo
más parecido a un siseo que puede hacer es el tono barrido que el resto de la
línea ya describe. La aventura corre igual en las ocho máquinas.

**Una decisión que parece un desperdicio y no lo es**: los dos periodos —el
del tono y el del ruido— salen al chip **en cada onda, diga lo que diga el
cuarto byte**, incluso el que no se está escuchando. Cuesta unos ciclos en una
nota simple y compra algo que vale más: lo que cuesta un efecto no depende de
por dónde salga, de modo que la tabla sigue diciendo cuánto dura cada uno y la
prueba que lo comprueba tiene una incógnita y no tres.

**Cómo se comprueba que la palabra llega al chip**, que era lo difícil: se
toca el mismo efecto tres veces cambiando **sólo ese byte en la máquina**, de
modo que nada más puede explicar una diferencia. Contar valores distintos en
la grabación no sirve —nota y siseo salen del mismo volumen de cuatro bits y
los dos dan cuatro o cinco—. Lo que sí sirve es **cuántos tramos de longitud
distinta** tiene: una onda cuadrada es el mismo puñado de longitudes una y
otra vez y un siseo es un reparto. Medido en las tres máquinas: una nota da
entre doce y diecinueve longitudes distintas y un siseo entre treinta y seis y
cuarenta y cuatro, y los dos juntos cambian de valor casi el doble de veces
que cualquiera por separado. Comprobado también al revés, con el motor sordo
al cuarto byte: la prueba lo dice.

**Lo que se decidió no hacer**: usar la envolvente por hardware para que el
ruido no pare el turno. Se puede —se escriben los registros y se vuelve, y el
chip termina solo— pero se llevaría por delante la única promesa escrita en
`effects.asm`, que `SOUND 2` suene a lo mismo en todas partes, porque el paso
del tono desaparecería donde hay chip. Y lo que compra es poco: estos blips
duran entre una vigésima y una décima de segundo. Además volvería `SOUND`
indeterminado en el tiempo, que es lo que la batería peor lleva.

## El color de la letra, que ya se cambia

Pedido hace tiempo y hecho. Se escribe **dentro del texto del mensaje**, que es
donde va: lo que sale en rojo es una palabra de una frase y no una propiedad
del mensaje entero.

    #14
    El dragón es \ink 2 rojo \ink 7 y está dormido.

El comando se come los espacios que lo siguen, como en cualquier otro lenguaje
con comandos dentro del texto, para que no salgan dos espacios donde el autor
escribió uno; `\\` es una barra invertida de verdad. Los colores son los
dieciséis del Spectrum, los mismos que en las láminas: del 8 en adelante es el
mismo color brillante. El cambio dura hasta el siguiente y no hasta el final
del mensaje.

**Cómo viaja.** El código 1 del juego de caracteres, que estaba reservado desde
que el juego pasó a ser fijo, dice que la tinta cambia, y el código siguiente
dice a cuál —y ese va como **carácter imprimible**: el 0 es `0` y el 15 es `?`.
Es raro a primera vista y tiene motivo: el compresor empareja códigos, y un
color guardado como número crudo sería un código por debajo del espacio, que es
donde viven las letras que el ASCII no tiene. Como carácter es un código
corriente, así que un cambio de tinta se empaqueta y se desempaqueta con el
texto que lo rodea y el compresor no sabe que está ahí. De paso, ningún color
puede ser nunca el 0, que es lo que termina una cadena.

**Qué significa un color en cada máquina**, que es lo mismo que ya resolvían las
láminas:

| máquina | qué hace con el número |
|---|---|
| Spectrum y Next | el color tal cual, con el brillo del bit de arriba |
| MSX | el más parecido de los suyos, por la misma tabla que las láminas |
| Amstrad | en una aventura de Amstrad, la pluma, de cero a tres, que es lo que un color significaba en las aventuras de esa máquina; en una de Spectrum, el color, en la pluma a la que va en la lámina del cuarto (ver «El texto, que comparte las cuatro plumas con la lámina») |
| PCW | nada: lee el comando y sigue, que es como una máquina de un solo color tiene que comportarse |

En el Spectrum eso obligó a **guardar el borde en memoria** —el puerto no se
puede leer y el altavoz es otro bit del mismo— y a poner el atributo de cada
celda al imprimir, que es una escritura más por carácter. En el Amstrad hubo
que darle plumas al impresor: en modo 1 los dos bits de un píxel viven en
mitades distintas del byte, así que una pluma son dos máscaras y una Y con cada
una.

**El intérprete de PC también lo hace**: el de texto se lo quita, porque no
tiene colores, y el de pygame, que tiene atributos como la máquina que copia,
lo obedece.

~~**Lo que queda de esto**: decidir si un mensaje debería empezar siempre con
la tinta por defecto.~~ **Decidido y hecho: un cambio de tinta dura hasta el
final del mensaje en el que está.**

Antes duraba hasta el siguiente `\ink`, y **no tenía por qué haber uno
siguiente**: nada reiniciaba `text_attr`, que se fija al ensamblar y sólo la
toca un cambio de tinta. Un mensaje que ponía el texto en rojo y no lo
devolvía dejaba en rojo la descripción de la sala siguiente, el prompt y lo
que dice el parser cuando no entiende. Es el peor tipo de fallo: **se ve lejos
de la línea que lo causa**, y el autor no puede verlo mientras escribe esa
línea. El propio ejemplo lo tenía, en `#VICTORIA`.

Lo que se da a cambio es pintar a lo largo de varios mensajes, y en GAC vale
poco: la unidad que el autor escribe **es** el mensaje —un renglón es un
mensaje, la descripción de una sala es un mensaje— y cuando de verdad se
quiera, cuesta un `\ink` en el segundo. Y la regla se dice en una frase, que
es la que uno supone al ver que el comando va dentro del texto.

**No había original al que ser fiel**: el GAC del 86 no tenía color en el
texto, así que esto es diseño nuestro de cabo a rabo, y ninguna de las ocho
aventuras lo usa.

**Dónde va el remedio.** En `print_packed`, que es lo que imprime un mensaje
entero, y no en `text_end`, que parecía el sitio: a `text_end` llega también
`print_digit`, de modo que un contador impreso en mitad de una frase habría
cortado la tinta ahí mismo. Cada máquina dice su `TEXT_INK_DEFAULT` —siete en
Spectrum, Next y MSX; en el Amstrad un «dos» que, por un cruce de plumas en
`text_ink`, era la pluma uno, que es la del original --ver «El texto, que
comparte las cuatro plumas con la lámina»--; y cualquier cosa en el PCW, que
lee el comando y no hace nada—.

**Y dos cosas en el intérprete de pygame**, que obedece la tinta y tenía que
seguir la misma regla. La primera es la regla. La segunda es un fallo que
estaba al lado: metía el número del color entero en el atributo con un `or`,
y en un atributo de Spectrum el brillo es el bit seis, no parte del color, así
que `\ink 12` colaba su bit tres en el papel. **Arreglado a ojo y sin
comprobar**, porque aquí no hay con qué correr pygame. **Comprobado después**,
cuando ya lo había: `tests/test_pygame.py` lo corre sin ventana y mira el
atributo de una letra con cada una de las dieciséis tintas, y se comprobó que
falla con el bit tres metido en el papel.

**Y el fleco que dejó la decisión, atado en el mismo sitio.** La tinta por
defecto estaba fijada al ensamblar, una por máquina, y la aventura no podía
elegirla. Antes se podía de refilón —ponías un `\ink` en el primer mensaje y,
como no se reiniciaba nunca, te quedaba toda la partida de ese color—, de
modo que la regla nueva **cerraba la única forma que había de colorear una
aventura entera, aunque fuera por accidente**. Así que ahora se dice en su
sitio: `ink n` en `/CTL`.

Va al final de la sección `config`, que es donde va lo que se añade después,
y **el cero significa «no se ha dicho nada»** en vez del color cero —que en
todas estas máquinas es el papel, y texto del color del papel no se ve—. Eso
es lo que hace que añadirlo no rompa nada: una base de datos que no lo traiga
se lee con un cero ahí y obtiene la tinta de siempre.

Lo lee `config_init`, que corre **antes** que `screen_init`, y eso resulta no
importar: `cls_window` limpia los atributos con la constante y no con la
variable, y de todas formas una celda vacía no tiene píxeles, así que su
tinta no se ve. Lo que la variable decide es con qué se dibuja cada letra.

## Las teclas que se solapan, que ya no se pierden

Lo destapó la prueba de `TEXT` del PCW, que una vez de cada varias se quedaba
con `>ANDA` en pantalla y sin contestar: el enter se había perdido. No era del
emulador. `read_key` era igual en las cinco máquinas: esperaba a que no hubiera
**ninguna** tecla pulsada y luego a que hubiera una. Si la siguiente tecla
bajaba antes de soltar la anterior —la A todavía abajo cuando ya se pulsa el
enter, que es escribir deprisa—, nunca había un instante sin teclas, y la
espera de soltar se comía el enter entero.

**Lo que hace el original, medido.** Su lectura está en `$7157` de MegaCorp:
pone a cero el bit 5 de `FLAGS`, espera a que la interrupción de la ROM lo
encienda y lee `LAST_K`. O sea que lo que cuenta como teclear una tecla es de
la ROM. Probado en la máquina: L, O y K pulsadas cada una antes de soltar la
anterior dan **LOK**, y una X mantenida dos segundos sale **seis veces**. Las
reglas de la ROM, que son las que hay ahora en
[`keys.asm`](../z80/common/keys.asm) para las cinco:

- una tecla que no es la última tecleada cuenta en el acto, siga o no la otra
  abajo;
- mientras hay dos teclas que no son mayúsculas no se decide nada, así que la
  que se queda abajo no sale dos veces cuando sube la otra (y la que se pulsó
  y soltó encima se pierde, como en la ROM);
- una tecla soltada se olvida a los cinco cuadros: pulsada otra vez antes, es
  la misma que sigue abajo;
- una tecla mantenida se repite a los treinta y cinco cuadros, y luego cada
  cinco.

Cada máquina sólo pone su parte: su `scan_keyboard` cuenta en `key_count` las
teclas que no son mayúsculas. Las pruebas están en
[`keystrokes.py`](../tests/keystrokes.py) —rodadas, dos a la vez y
mantenida— y se tocan en el Amstrad, el MSX y el PCW sobre `read_line`, y en el
Spectrum y el Next sobre el juego entero. Al Amstrad le hizo falta que su banco
de pruebas de teclado supiera leer una línea, como los otros.

**Y destapó otro fallo, más viejo: los cuadros no eran cuadros.** Sin
interrupciones no hay reloj, así que un cuadro son `LOOKS_A_FRAME` miradas al
teclado, y ese número se había calculado a ojo. La repetición no llegaba nunca
en el Amstrad, y medido con el contador de ciclos del procesador —una espera
como la de `HOLD`, sin nada pulsado— salió esto:

| máquina | ciclos por mirada | miradas por cuadro, antes | medidas |
|---|---|---|---|
| Spectrum | 1840 | 38 | 38 |
| Amstrad | 6680 | 40 | 12 |
| MSX | 5780 | 28 | 12 |
| PCW | 5750 | 20 | 14 |
| Next | 2080 | 38, las del Spectrum | 268, que no caben en un byte: 255 |

Y una mirada **con una tecla pulsada** cuesta más que una sin nada: 2370 en el
Spectrum contra 1840. Contando la repetición en las miradas vacías, una tecla
mantenida empezaba a repetirse un 30 % tarde, así que el bucle usa
`LOOKS_A_FRAME` mientras no ve nada y `LOOKS_HELD` mientras ve una tecla: 29 en
el Spectrum, 11 en el Amstrad, 12 en el MSX, 13 en el PCW y 247 en el Next.
Medido con eso puesto, el cuadro con una tecla pulsada dura 67633 ciclos en el
Spectrum, 74364 en el Amstrad, 71448 en el MSX, 77117 en el PCW y 579134 en el
Next, contra 69888, 80000, 71591, 80000 y 559104.

O sea que **`HOLD` esperaba 3,3 veces de más en el Amstrad**, 2,3 en el MSX y
1,4 en el PCW, y **siete veces de menos en el Next**, que lee el teclado del
Spectrum a veintiocho megahercios y usaba su número. El del Spectrum estaba
bien, y la prueba que lo mide saltó en cuanto se le puso uno medido con una
tecla pulsada, que cuesta un 30 % más: por eso la medida buena es sin teclas, y
una tecla mantenida se repite un poco tarde. Con los números nuevos: 79872
ciclos por cuadro en el Amstrad, 69304 en el MSX y 80371 en el PCW, contra
80000, 71591 y 80000 de verdad; el Next queda un 5 % corto. Los bancos de
pruebas de teclado de esas tres tienen ahora una espera de cien cuadros y una
prueba que la cuenta en ciclos. El Next dice su número con un `DEFINE` antes
de incluir el teclado: con `IFNDEF` sobre una etiqueta, el ensamblador la ve
definida en la segunda pasada venga de donde venga.

**Y una tercera cosa, que costó media tarde.** `test_and_parts_them_too`
empezó a fallar una vez de cada cinco diciendo que un `HOLD` de dos segundos
había durado 0,02. No era el `HOLD`: era la orden. Con una tecla pulsada y el
ordenador anfitrión atascado un segundo —que es lo que pasa con la suite
entera corriendo—, la tecla se repite, que es lo correcto, y la línea sale
`ESPPPPPPPERA AND SALIR`. Entonces «ESPPPPPPPERA» no es un verbo, la orden que
llevaba el `HOLD` no se ejecuta, el `AND` parte igual y `SALIR` acaba la
partida al instante. Reproducido a mano manteniendo una tecla tres segundos:
sale el mismo número exacto de segundos que en el fallo, 0,01997142857142857.

O sea que la repetición convierte un atasco del anfitrión en una letra de más,
y una prueba que da por hecho lo que tecleó miente. Las que comprueban letra a
letra —los separadores del Spectrum y la línea del MSX y del PCW— **leen ahora
lo que entró de verdad** y repiten la vuelta hasta tres veces si no coincide,
diciendo qué llegó cuando se rinden.

**Lo que cambia para las pruebas.** Dos letras iguales seguidas necesitan ahora
un hueco de una décima de segundo **de la máquina** entre soltar y volver a
pulsar, que en un emulador que va a un cuarto de velocidad —el Next— son cuatro
de reloj: `Session.SAME_KEY_GAP` es medio segundo y lo usan todos los que
teclean. Con el hueco de antes, `XYZZY` salía `XYZY` en el Next.

Para medir, una cosa que no se entiende del todo y conviene saber: con una
tecla pulsada, parar la máquina un momento con `Session.held()` hace que al
soltarla el intérprete ya no la vea pulsada. Las medidas de arriba se hicieron
sin parar la máquina.

## La aventura de ejemplo, que ya está escrita

[`ejemplo/faro.gac`](../ejemplo/faro.gac): **El faro de Santa Bárbara**, cinco
salas, cuatro objetos y un solo enigma, con su
[fichero de proyecto](../ejemplo/faro.toml) y su tipografía
(`ejemplo/letras.bin`, dibujada aquí). Se construye para las ocho máquinas con
`python -m regac make ejemplo/faro.toml` y se juega de principio a fin: coger
la llave, abrir la puerta, coger el candil, encenderlo, subir y encender la
lente.

Es pequeña a propósito. No enseña lo que el intérprete aguanta, sino cómo se
escribe una aventura, y de paso ejercita lo que las ocho de 1986 no pueden
ejercitar porque es nuestro: los acentos, las palabras propias que parten una
orden (`COGE LLAVE Y NORTE`), los ruidos de `/SOUND`, los nombres para los
números y una tipografía que viene en un fichero. Su prueba es
[`test_example.py`](../tests/test_example.py): compila, comprueba que nada
apunta a donde no debe, construye las ocho máquinas y la juega entera en un
Spectrum.

**Y encontró cinco cosas**, que es para lo que estaba en la cola:

1. **`SWAP` no intercambiaba dos objetos**, y llevaba así desde que existe.
   Movía uno de los dos y dejaba el otro donde estaba. Se tapaba solo: como
   `obj_location` leía la posición del objeto que hubiera en `vm_arg` en vez
   de la del que le pasaban, y la prueba de `SWAP` sólo preguntaba por uno de
   los dos, todo parecía correcto desde fuera. El candil encendido de esta
   aventura no llegaba nunca a las manos del jugador. Arreglados los dos, y la
   prueba pregunta ahora por los dos objetos.
2. **Una aventura sin `/FONT` se construye sin quejarse y sale muda**: cada
   letra son ocho ceros, así que juega perfectamente e imprime líneas en
   blanco. Ahora `regac check` lo avisa.
3. **`regac make` buscaba los ficheros del fuente donde se lanzara el
   comando**, no junto al fuente, que es lo que dice el formato; `regac
   compile` sí lo hacía bien. Con la aventura en `ejemplo/` la tipografía no
   aparecía.
4. **Decía «carries no music» a una aventura que no tiene ninguna**, sólo
   porque pide ruidos.
5. Y una lección del propio GAC que ahora está escrita en la aventura, porque
   cuesta un rato descubrirla: **el número de un nombre del vocabulario y el
   del objeto que nombra son el mismo**, ya que coger es `GET NO1`.

**Las dos cosas que quedaron pendientes de esto ya están medidas**, y para
medirlas hubo que aprender a jugar al original:

- **Su protección no era un muro.** MegaCorp arranca en su sala 5000 pidiendo
  la clave, y la clave está en la propia aventura: esa sala acepta el verbo 29,
  que en su vocabulario es **REBECA**. Con eso el original se juega desde una
  instantánea sin saber nada de su manual.
- **Y su pantalla se lee con su tipografía.** El juego de caracteres sale de
  su base de datos y la primera casilla es el código cero. Lo que costaba era
  otra cosa: **las ocho líneas de píxel de un renglón están a 256 bytes una de
  otra y no a 32**, porque esta máquina las entrelaza, y leerlas seguidas
  deja las letras cortadas en tiras. Está en `original.py` del scratchpad de
  aquella sesión, y el método es el de siempre: escribir condiciones propias
  encima del principio de una de sus tablas, que se encuentra buscando en su
  memoria los bytes que compila `regac`.

**`WAIT` acaba la tabla en la que está, y no sólo el turno.** Medido dos
veces: dos condiciones que el mismo verbo satisface, una detrás de otra, en su
tabla de alta prioridad y en la de baja; las dos veces habló sólo la primera.
Para asegurarlo, un control: la segunda, puesta sola, sí habla. El Z80 corría
la tabla entera --de ahí que la aventura de ejemplo dijera «la puerta se abre»
y «no tienes con qué abrirla» de una sentada-- y `runGAC.py` cortaba la tabla
local y la baja pero no la alta. Las dos arregladas, con prueba en
`test_conditions_z80.py`.

**La coma al principio de una línea es del original.** Comparadas línea por
línea la primera sala de MegaCorp en el original y en el nuestro: **idénticas**,
espacio suelto al principio del tercer renglón incluido. O sea que una marca
de puntuación se imprime donde cae, sin preguntar si cabe, en los dos. No hay
nada que arreglar.

**Y esa misma comparación destapó dos diferencias más**, de las cuales una
está arreglada y la otra medida y no:

**La apertura de MegaCorp: decían su sala una vez y nosotros dos.**
Arreglado, y lo que costó fue el orden de dos cosas dentro del turno.

Su primera condición de alta prioridad es `IF ( AT 5000 ) SET 3 LOOK END`, y
lo medido fue esto:

| pregunta | cómo se midió | respuesta |
|---|---|---|
| ¿abre diciendo su sala una vez o dos? | cargando el original de su cinta, que es la única forma de verlo empezar, y mirando la pantalla cuatro veces por segundo | **una**, y nada la borra |
| ¿se mira esa tabla antes de la primera pregunta? | cambiándola por `IF ( SET? 3 ) MESS 89 END`: si su bandera está puesta, es que la suya corrió | **sí** |
| ¿un `LOOK` ahí describe todos los turnos? | poniéndole `IF ( AT 1 ) LOOK END` y jugando dos turnos | **sí** |
| ¿la pantalla de título viene dibujada en la cinta? | decodificando los 6912 bytes de pantalla que trae su bloque de 48K con la tipografía de la aventura | **es dibujo, no texto**: la descripción la imprime el intérprete |
| ¿un `LOOK` paga la descripción que una sala nueva debe? | tabla cambiada por `IF ( AT 1 ) LOOK END` y luego la clave, que lleva a la sala uno | **sí**: descrita una vez |

Con la última encaja todo: **la tabla de alta prioridad va antes de la
descripción que una sala nueva debe, y un `LOOK` en ella la da por pagada**.
Así una aventura abre en la sala que quiera describiéndola ella misma, y el
intérprete no la repite. Nosotros describíamos primero y mirábamos la tabla
después, de modo que MegaCorp decía su primera sala dos veces.

Ahora `play_turn` mira la tabla y luego describe lo que quede debiéndose, y
`LOOK` borra esa deuda. La apertura de MegaCorp sale ya idéntica a la del
original, línea por línea. La prueba está en `test_markers_z80.py`, y las que
usan esa tabla como sonda escriben ahora una orden antes: en la primera vuelta
la tabla se mira cuando todavía no se ha descrito nada, que es lo que hace el
original.

**Lo de «Perdón?» no era lo que parecía, y queda a medias.** El original
también lo dice: lo que pasaba es que en la sala de la clave no lo decía, y
ahí está lo que falta por entender. Medido con tres tablas de alta prioridad
distintas, tecleando la misma palabra desconocida en esa sala:

| lo que hace su condición | qué contesta |
|---|---|
| `LOOK`, que es la que trae | la sala, y **ninguna queja** |
| `MESS 89` | «Perdon?» y luego el mensaje |
| nada | «Perdon?» |

O sea que **una descripción dentro del turno calla la queja** y un mensaje no.
Nosotros nos quejamos igual, porque lo único que miramos es si alguna condición
de la tabla local o de la baja se cumplió. Falta decidir qué cuenta
exactamente como que algo pasó --describir la sala, imprimir, las dos-- antes
de tocarlo, que es de esas cosas que se arreglan en diez minutos y se eligen
mal en uno.

**Cerrado sin tocarlo, porque no había nada que decidir.** Lo explicó lo que
se leyó después, en «Leyendo el intérprete original»: el original se queja
siempre, y lo que la tapa es que **una descripción vuelve a la columna cero de
la línea en la que está y escribe encima**, y la tabla alta corre al principio
del turno siguiente, justo detrás de la queja. Un mensaje no hace eso. Así que
no hay que elegir qué cuenta como que algo pasó: nosotros también nos quejamos
siempre, y desde que `describe_location` vuelve a la columna cero la tabla sale
igual. `test_markers_z80.py` lo pregunta con las tres tablas de arriba y las
tres salen como en el original; la sala de la prueba dice más que la queja,
como la de MegaCorp, porque una más corta deja asomar la cola --que es lo que
el original hace también, «INTRODUZCA LA CLAVEsa...»--.

## Leyendo el intérprete original, que es el camino corto

Lo de hoy dejó claro que medir de una en una sale caro: cuatro fallos de fondo
en un día --`SWAP` que no intercambiaba, `WAIT` que no cortaba la tabla, el
orden del turno cambiado y el banco del texto sin paginar-- todos en partes que
nunca se habían mirado contra el original. Así que se ha empezado a leer su
código.

**La regla, primero.** Se lee para **documentar qué hace**, nunca para copiar:
`z80/` es nuestro y es MIT, y su intérprete tiene dueño. El desensamblado se
queda en el scratchpad, fuera del repositorio, como las instantáneas.

**Cómo se entra**, que es lo que costaba:

- Sus tablas de condiciones se encuentran buscando en su memoria los bytes que
  `regac` compila de la misma aventura: en MegaCorp, la de alta prioridad está
  en `$ADA0` y la de baja en `$B3ED`.
- **Su tabla de saltos de opcodes está en `$A157`**, y la entrada *n* es el
  opcode *n+1* de `regac/opcodes.py`, que es su propia numeración. Se reconoce
  por la forma de las rutinas: `SET?` y `RES?` son la misma con el salto al
  revés. Con eso se tiene la dirección de cada opcode del original.
- Los puntos de parada del emulador no sirven para esto: fuera del modo paso a
  paso no detienen el procesador. Lo que vale es leer la memoria y
  desensamblar.

**Lo que ya se ha leído**, y de paso confirma dos arreglos de hoy:

| dónde | qué es |
|---|---|
| `$759F` | `SWAP`: coge las dos fichas y **cambia sus dos direcciones**, que es lo que el nuestro no hacía |
| `$78F8` | `WAIT`: pone el bit 6 de `$A4E7` y vuelve |
| `$A4E7` | su byte de estado: el bit 6 es el `WAIT`, el 7 se pone y se quita en `$72AE` y `$72BB`, el 3 en `$73EB` |
| `$7315` | apilar un valor; su pila de condiciones tiene el puntero en `$A537` y la base en `$A4E3` |
| `$73E0`–`$7410` | el recorrido de una condición: se salta lo que no toca mirando el bit 7 de cada byte --que es como marca una constante-- hasta el `$3F`, que es `END` |

**El despachador, leído** (`$797B`). Recorre la tabla byte a byte: un byte con
el bit 7 puesto es una constante y se apila; si no, los seis bits de abajo son
el opcode, que se busca en `$A155 + 2n` y se llama. **Y después de cada
opcode mira su byte de estado: si el bit 6 o el 5 están puestos, sale de la
tabla.** Al entrar en una tabla los limpia --`AND 9F`-- y vacía la pila. Eso es
lo que hoy se había medido a ciegas: `WAIT` pone el bit 6 y por eso acaba la
tabla en la que está.

**El bucle de turno, leído** (`$7C5D`), que es lo que más costaba medir:

    tabla de alta prioridad -> describir la sala si es nueva -> preguntar ->
    la orden -> tabla local -> tabla baja -> la queja -> otra vez

Exactamente el orden que hoy se había deducido a base de medir aperturas: la
tabla de alta prioridad va **antes** de la descripción que una sala nueva debe.
Después de ella mira el bit 5, que es el de acabar la partida.

**Y los bits de su byte de estado, `$A4E7`:**

| bit | qué significa | quién lo pone |
|---|---|---|
| 6 | el turno está servido | `WAIT` en `$78F8`, `OKAY` en `$78ED` |
| 5 | la partida se acaba | `EXIT` en `$7918` |
| 3 | algo atendió la orden | la evaluación de un `IF` que sale cierto, en `$73EB` |

El bit 3 se limpia **justo antes de la tabla local** (`$7B03`), así que lo que
haga la de alta prioridad no cuenta para la queja; y la queja misma
(`$7B2C`) elige entre el 241 y el 242 **mirando el verbo y el nombre**: si
alguno de los dos es algo, «no puedo hacer eso»; si ninguno, «perdón».

**Y eso era una diferencia nuestra, ya arreglada**: mirábamos sólo el verbo,
de modo que un nombre suelto que la aventura conoce --`JARRO` en MegaCorp--
contestaba «perdón» en vez de «no puedo hacer eso». Comprobado en el original
antes de tocar nada, y con prueba en `test_markers_z80.py`.

### Los sesenta y dos opcodes, leídos de una sentada

No era una tarde por opcode: la tarde era **medir**. Con la tabla de saltos en
la mano se sacan los sesenta y dos de una vez --`disassemble` en cada
`$A155 + 2n`-- y se leen seguidos. Lo que se midió después fue sólo lo que
salió distinto, que es como debe ser: **primero preguntarle al original, y
sólo entonces tocar código**.

**El error gordo: `CARR` y `AVAI` estaban cambiados.** Su opcode `$1F` mira la
mano **y** la sala, y el `$20` mira sólo la mano. `deGAC` los tenía al revés,
y de ahí lo heredó `regac`, así que toda aventura decompilada traía el nombre
cambiado y --lo que importa-- **nuestro intérprete ejecutaba sus bytes con el
sentido contrario**: un `AVAIL` suyo, que es la comprobación corriente de «lo
tengo o lo veo», sólo se cumplía con el objeto en la mano. En MegaCorp son
dieciocho sitios.

Medido en los dos sentidos, poniendo el objeto 1 en la sala y preguntando por
`HERE`, `$1F` y `$20` con un mensaje cada uno:

| dónde está el objeto | `HERE` | `$1F` | `$20` |
|---|---|---|---|
| en la sala, no en la mano | sí | **sí** | no |
| en la mano | no | **sí** | **sí** |

Arreglado en `regac/opcodes.py` (los códigos), en la tabla de saltos de
`z80/common/opcodes.asm`, en `deGAC.py` y en las bases ya decompiladas, donde
los dos nombres se han intercambiado. `runGAC.py` trabaja con los nombres y no
hacía falta tocarlo.

**Y otras seis diferencias, todas medidas antes de tocar nada:**

| qué | el original | lo nuestro, antes |
|---|---|---|
| `NOUN n` | vale para **los dos** nombres de la orden: `COGE DISCO AGUJA` responde a `NOUN 4` | sólo el primero |
| `GOTO` | es su `LOOK` con una sala puesta antes (`$7805`), así que **describe ahí mismo**: `GOTO 20 MESS 89` sacó la sala 20 y luego el mensaje | lo dejaba a deber al principio del turno siguiente |
| `FIND` | va a donde esté; lo que no está en ninguna parte da el 252 y **acaba el turno** | no decía nada |
| `BRIN` | lo que ya se lleva da el 245 y lo que no está en ninguna parte el 252, y acaba el turno | lo movía sin más |
| `GET`, `DROP` | sus tres negativas --ya lo tengo, no está aquí, peso-- **acaban el turno**, y hay **peso**: rechaza cuando el total *alcanza* la fuerza, que empieza valiendo 250 | ni peso ni fin de turno |
| `<` y `>` | miran el **signo de la resta**, no el acarreo | sin signo |
| `QUIT` | **una tecla**, y sólo la N lo deja correr: contestado con una X, la aventura se acabó | leía una línea entera y una lista de síes |

La fuerza y lo que se lleva encima van ahora dentro del bloque que se guarda,
como en el original, y sólo `GET` y `DROP` lo llevan: un objeto que `TO` o
`SWAP` saquen de la mano deja la cuenta como estaba, que es lo que hace él.

**El bucle, mejor leído.** `CALL 7B79` no era la pregunta: es **seguir la
salida**. Si el verbo nombra una salida de la sala, mueve, describe y vuelve
al principio del bucle, **sin pasar por la tabla local ni por la baja**.
Medido: con un `MESS` puesto encima de la tabla baja, `COGE` lo saca y
`NORTE` no.

**Y no hay ninguna descripción «a deber»**, que era todo un mecanismo nuestro
de menos. Describe quien mueve --`LOOK`, `DESC`, `GOTO`, `FIND`, la salida
que la orden nombra-- y el arranque de la partida, que acaba en un `LOOK`
(`$7B75`).

**Entonces, ¿por qué MegaCorp no dice dos veces su primera sala**, si miran el
arranque y su propia tabla alta? **Porque una descripción vuelve a la columna
cero de la línea en la que está y escribe encima**, sin borrar ni terminar la
línea antes. La segunda cae sobre la primera y no se ve.

Esto costó una medida mal leída y conviene apuntar por qué. La primera vez se
preguntó en la sala 1, cuya descripción son cinco líneas, con `MESS 89 LOOK`
en la tabla alta: el mensaje no aparecía y pareció que describir **borraba** la
ventana. No: se había ido por arriba, empujado por las cinco líneas. Repetida
la pregunta en la sala de la clave, que es de una línea, el mensaje sigue ahí
y lo que queda en pantalla es

    INTRODUZCA LA CLAVEsa...

que es la descripción escrita sobre `El tiempo pasa...`, con su cola asomando.
Y en modo `TEXT` ni siquiera eso --su `DESC` se salta esa parte entera-- y la
descripción sale seguida del mensaje en la misma línea, medido también.
**La lección: una medida sobre una sala de cinco líneas no dice nada de lo que
pasa con la ventana.**

**Ya es lo que hacemos.** `play` describe la sala de salida antes del primer
turno, `follow_exit` describe al pasar por la salida y marca el turno servido,
`play_turn` ya no debe nada a nadie, y `describe_location` pone la columna a
cero cuando no se está en modo `TEXT`. La bandera `vm_new_room` se llama ahora
`vm_moved` y sólo dice una cosa: que la orden se fue por una salida, y que ahí
se acaba el turno.

**Y la sala sin lámina, medida** en *Los pájaros de Bangkok*, que tiene salas
de los dos tipos. Su `DESC` reparte (`$75F2`): la que tiene lámina se lleva la
ventana debajo y el dibujo; la que no, `CALL 72C0`, que es la misma llamada que
hace `TEXT` --toda la pantalla--. Y **no borra nada**: al llegar a una sala sin
lámina, la lámina anterior sigue donde estaba y el texto gana la fila que antes
era el borde, hasta que a fuerza de líneas se le va escribiendo encima. Una
lámina posterior vuelve a quedarse con sus filas.

Ya lo hacemos, y la prueba lo mira donde de verdad se ve: en `text_top`, que es
el alto de la ventana --bajo la lámina en una sala con dibujo, cero en una sin
él, y otra vez abajo al dibujar la siguiente--.

### El parser, leído y medido

Su parser son tres rutinas cortas. Una prueba una palabra contra una lista
(`$79E3`), otra la prueba contra las tres listas por orden (`$7A53`), y otra
recorre la línea (`$7A64`).

**Cómo reparte una palabra** (`$7A53`): la prueba como **verbo** si el verbo
está vacío, luego como **adverbio** si el adverbio está vacío, y luego como
**nombre**, que va al primer hueco --el nombre uno si está vacío, si no el
dos--. Una palabra que no está en ninguna lista se pasa por alto sin más.
Nosotros probábamos el nombre antes que el adverbio; ahora es su orden.

**Cómo compara** (`$79E3`): letra a letra hasta que **la palabra tecleada**
se acaba, no la del vocabulario, que es por lo que `EX` encuentra `EXAMINA`
y `EXAMINAR` no encuentra nada. Pasa las minúsculas a mayúsculas por el
camino. Eso ya lo teníamos igual, medido en su día.

**Qué parte una orden de la siguiente** (`$7A64`): la coma, el punto, el
punto y coma y la admiración, y las palabras `AND` y `THEN`. Y nada más: la
tabla de puntuación de la aventura le sirve sólo para **partir palabras**.
Medido escribiendo dos verbos en una línea con cada marca entre ellos:

| línea | órdenes |
|---|---|
| `COGE MATA` | una |
| `COGE,MATA` | **dos** |
| `COGE.MATA` | **dos** |
| `COGE-MATA` | una |
| `COGE?MATA` | una |
| `COGE:MATA` | una |
| `COGE AND MATA`, `COGE THEN MATA` | **dos** |

Nosotros tomábamos por fin de orden **toda** la tabla de puntuación, que en
MegaCorp trae también el `-`, el `?` y el `:`. Ahora `ends_statement` son esas
cuatro marcas y `parts_word` es el espacio más la tabla, que es además lo que
ya usaba el ajuste de líneas para no partir `Salidas:Sur.` por la mitad.

**El pronombre** (`$7BA4` y `$7C16`): al empezar cada orden guarda el
**último** nombre de la anterior --el segundo cuando dijo dos-- y deja la
palabra marcada con un `$FF` que cambia por él en cuanto la línea está
leída. Medido en *Los pájaros de Bangkok*, que es la única de las cuatro con
pronombres: después de `COGER AGUA BAR`, el `LO` de `COGER LO` sale valiendo
87, que es el BAR. Nosotros guardábamos el primero, y el pronombre sólo valía
para el primer hueco.

**Y una prueba del parser destapó un fallo del teclado.** Al escribir
`ESPERA?SALIR` en el Spectrum llegaba `ESPERA?CSALI`: la interrogación es
símbolo+C, y nuestro `next_key` decidía si una tecla era nueva **comparando el
carácter**. Como las dos teclas nunca se sueltan en la misma trama, en cuanto
el símbolo se suelta la misma pulsación pasa a decir `C`, que es otro carácter
y por tanto otra tecla; y la letra que venía detrás se perdía mientras eso
pasaba. El ROM guarda **la tecla**, no lo que dice. Ahora se compara
`key_found`, que es lo que el explorado de cada máquina deja antes de aplicar
ningún shift, y `A?B`, `A.B`, `A:B` y `A-B` llegan enteras.

### El dibujo, y el original como juez

Las 44 láminas de las cuatro aventuras salen punto por punto como las dibuja
la referencia, así que el camino corriente está comprobado. Lo que no lo
estaba es **lo que una aventura nueva sí puede dibujar y esas cuatro nunca
dibujaron**: una línea que se sale, un punto fuera del marco, un rectángulo
más grande que la pantalla. Ahí la referencia es sólo nuestra opinión.

Así que se le preguntó al original, y se puede preguntar cuanto haga falta:
**sus láminas son una tabla de registros** --id, longitud, cuántas órdenes, y
las órdenes--, que es como las lee `deGAC`, así que se le escribe una lámina
nuestra encima de una suya y se le manda describir esa sala. Lo que dibuje es
la respuesta. El guión está en el scratchpad (`draw_oracle.py`), fuera del
repositorio.

**Su marco**: las órdenes se escriben en un espacio de 256 de ancho por 176 de
alto con la **y contando hacia arriba**, y la lámina son las dieciséis filas de
arriba de la pantalla: y=175 es la fila de píxeles de arriba y y=48 la última
de la lámina. Su `$643C` sujeta la x a 0..255 y la y a 48..175 antes de pasarle
la línea a la ROM (`$24BA`), que es la que dibuja: GAC no escribió la suya.

**Lo medido**, con láminas nuestras escritas en su memoria:

| caso | el original |
|---|---|
| `PLOT` fuera del marco | **lo salta**, y la lámina sigue |
| `LINE` con el segundo punto fuera | lo trae al borde y la dibuja |
| `LINE` con el **primer** punto fuera | **deja de dibujar la lámina**, y lo que venga detrás tampoco sale |
| `RECT` con cualquier esquina fuera | lo mismo: nada, ni la parte de dentro |
| `ELLIPSE` mayor que el marco, líneas que se salen por los cuatro lados, rellenos en las esquinas | **iguales que los nuestros** |

Lo de dejar de dibujar viene de la ROM: el primer punto lo pone su `PLOT`, que
da error fuera de rango. **Ninguna lámina de las ocho bases se sale del marco**,
así que esto sólo toca a las aventuras que se escriban ahora.

**Lo que hemos hecho con ello**: el `PLOT` fuera del marco ya no se dibuja
--era un fallo nuestro claro, pintábamos un punto pegado al borde que el
original no pinta-- y hay prueba en las cinco máquinas. Lo de abortar la lámina
**no** se copia: se dibuja lo que cabe y `regac check` avisa, diciendo qué orden
se sale y qué habría hecho el original. Ninguna aventura original depende de
ello, y un autor nuevo prefiere ver su dibujo a ver una pantalla en blanco.

Dos detalles que costaron su rato y evitan repetirlos:

- **El aviso es sólo para `PLOT`, `LINE` y `RECT`.** El segundo par de una
  `ELLIPSE` no es un sitio: es de donde salen los radios, por la distancia al
  centro, así que cae fuera del marco como cosa corriente --el faro de la
  aventura de ejemplo lo hace cinco veces--. Eso lo encontró el propio aviso
  saltando sobre nuestra aventura. De los rellenos no se ha preguntado qué
  hace con una semilla fuera, así que tampoco avisan. **Preguntado después, y
  ya avisan**: ver «La semilla de un relleno fuera del marco», justo aquí
  debajo.
- **Al Next no le sobran bytes.** La comprobación se escribió primero en
  dieciséis y no cabía bajo su máscara; queda en doce aprovechando que el
  marco son ciento veintiocho filas justas: se le resta el fondo y basta una
  comparación, porque lo que está por debajo se envuelve y falla igual.

### La semilla de un relleno fuera del marco

Preguntado con el mismo guión de `test_fills_original.py`: una caja de y=60 a
y=130, un `FILL` con x=80 y la semilla fuera, **cada caso con la instantánea
recién cargada** --la primera vuelta los encadenó en la misma máquina, y el que
se desbocó estropeó los de detrás; lo que salía allí no valía--.

| semilla | el original | nosotros |
|---|---|---|
| y=176, justo encima | rellena de y=175 abajo hasta la caja: 45 filas | nada |
| y=180 | nada | nada |
| y=200 | nada | nada |
| y=250 | **no vuelve**: se queda en $8A37 con parte de la caja pintada | nada |
| y=47, justo debajo | rellena de la semilla arriba hasta la caja, **y la fila de la semilla es ya la primera de la ventana de texto** | nada |
| y=30 | igual: de y=30 arriba, 18 filas de la ventana de texto incluidas | nada |

O sea que su comprobación de dónde se para no mira que la semilla esté dentro:
por debajo pinta lo que haya debajo, que es el texto, y por encima depende de
cuánto se pase.

**Decidido: no se copia.** Nosotros no rellenamos nada con la semilla fuera y
`regac check` lo avisa, diciendo lo que habría hecho el original --lo mismo que
se decidió con `PLOT`, `LINE` y `RECT` fuera del marco: se dibuja lo que cabe y
se avisa--. Copiarlo sería pintar la ventana de texto desde una lámina, y el
caso de y=250 no hay forma sensata de copiarlo. Ninguna de las ocho aventuras
tiene un relleno así, ni la del faro. Pruebas en `test_check.py`, que de paso
estrena la del aviso de `PLOT`, `LINE` y `RECT`, que no tenía ninguna.

**Lo que queda por leer**: nada del intérprete original, y desde ahora tampoco
queda nada por preguntarle. Los casos raros del relleno --lo último que
faltaba-- están preguntados con el mismo guión que los tres modos, y
`tests/test_fills_original.py` los lleva: seis formas donde un relleno no es
obvio, metiendo la rutina del original en marcha y comparando los 6144 bytes
contra el renderizador de referencia. **Las seis salen idénticas.**

| forma | qué hacen los dos |
|---|---|
| hueco de un píxel, en el borde de un byte | se escapa |
| hueco de un píxel, en mitad de un byte | se escapa igual |
| una diagonal por pared | no pasa: se para en la escalera |
| un pasillo de un píxel de ancho | sí lo recorre |
| la semilla encima de la pared | no hace nada en absoluto |
| una caja abierta contra el marco | se para en el marco |

Y el escape tiene forma, que era lo que no se sabía: **sale un rayo de un
píxel de alto y no se ensancha**. Medido en la caja del hueco: 135 píxeles
encendidos fuera de ella, **todos en la misma fila**, desde el agujero hasta
el borde de la lámina. Ni uno arriba ni uno abajo.

Los dos huecos se probaron a propósito en sitios distintos --uno en `x=120`,
que es frontera de byte, y otro en `x=124`, dentro de uno-- porque nuestro
relleno anda por bytes y el del original por columnas, y ésa era la primera
grieta por donde podían separarse. No se separan.

## El espejo: la misma aventura jugada dos veces a la vez

Todas las diferencias de estos días aparecieron porque alguien tropezó con
ellas: `SWAP` que no intercambiaba, `WAIT` que no cortaba la tabla, `CARR` y
`AVAIL` cambiados. **Esto va a buscarlas.** MegaCorp en el intérprete original
y MegaCorp decompilado y construido con el nuestro, uno al lado del otro en dos
emuladores, las mismas órdenes tecleadas en los dos y la ventana de texto leída
después de cada turno con la tipografía de la propia aventura. Comparten
pantalla y tipografía, así que un solo lector vale para los dos.

Está en `tests/test_mirror_z80.py`, con un paseo de veinticinco órdenes: andar,
chocar con paredes, coger lo que ya se lleva, soltar, coger lo que no está, un
nombre suelto, un verbo que no entiende, subir y bajar.

**Encontró algo en su primer paseo en condiciones**: una palabra que acaba
justo en la última columna. La calle de Nyhmir dice «Paseantes de varias
razas», y el `razas` termina exactamente en el borde: el original lo baja a la
línea siguiente y nosotros lo dejábamos. O sea que **una palabra tiene que
acabar antes de la última columna, no en ella**. Un byte en `textout.asm`
--`cp SCREEN_COLS` en vez de `cp SCREEN_COLS + 1`-- y las veinticinco órdenes
vuelven a salir idénticas. El modelo del ajuste que usan las pruebas de texto
(`emulator.wrapped`) llevaba el mismo error.

**Tres cosas del arnés**, cada una de las cuales costó una vuelta:

- **Las máquinas se turnan.** Dos emuladores a la vez hacen un anfitrión
  ocupado, un anfitrión ocupado pierde letras, y una letra perdida no es una
  diferencia entre intérpretes: es otra orden. Mientras se teclea en una, la
  otra se tiene quieta.
- **Una pantalla quieta no quiere decir turno terminado.** Mientras se dibuja
  la lámina --que son segundos-- la ventana está parada con la orden todavía
  en eco. Lo que dice que el turno acabó es que la última línea sea el prompt
  sin nada escrito detrás.
- **El eco se mira antes de dar al enter**, porque en cuanto corre el turno la
  descripción cae encima de esa misma línea: su `DESC` vuelve a la columna cero
  y escribe encima. Eso, que ayer se midió, aquí se ve en vivo.

Las dos ventanas se alinean **por abajo**: en qué fila cae una línea es historia
de la máquina --la instantánea del original se tomó con su título ya
desplazado-- y no cosa del intérprete.

### Alargado: dos aventuras, y lo que encontró

Ahora juega **MegaCorp** (treinta y tres órdenes) y **Los pájaros de Bangkok**
(dieciocho), que es la única de las cuatro con pronombres. Doce minutos y medio
las dos.

**Lo que encontró en Bangkok, y es gordo**: su tabla baja acaba con un cajón de
sastre, `IF ( VERB COGER ) GET NO1 OKAY END`. Así que `COGER AGUA` es un `GET`
del **objeto 56**, y la aventura tiene catorce objetos. El original no pregunta
si existe: lee más allá del final de su tabla, lo que encuentra no es esta sala,
dice «no veo uno de esos por aquí» y acaba el turno. Nosotros lo pasábamos por
alto en silencio y el `OKAY` de detrás contestaba «Vale». Eso pasa con **casi
cualquier nombre que no sea un objeto**, o sea todo el rato.

Arreglado en `GET` y en `DROP`, que son los dos que hablan, con prueba en
`test_conditions_z80.py`.

**Y una falsa alarma que enseñó algo**: en Bangkok el original repetía lo
tecleado en minúsculas y nosotros en mayúsculas. No es del intérprete: es el
**bloqueo de mayúsculas de la ROM**, y las instantáneas no se toman igual
--MegaCorp y Vajillas lo tienen puesto, Bangkok y el Quijote no--. El espejo lo
enciende antes de jugar, como ya nivelaba el desplazamiento de la ventana. Se
llegó a cambiar los cinco teclados para conservar la caja de lo tecleado y se
revirtió entero al ver la causa; lo que sí queda es saber **dónde mirar la
próxima vez**: `$5C6A`, bit 3.

**Tres cosas más del arnés**, por si hay que tocarlo:

- Una letra perdida se arregla **antes de dar al enter**: se borra la línea y se
  escribe otra vez, que así las dos máquinas siguen en el mismo turno. Y la
  línea tiene que ser el prompt y la orden y nada más: preguntar si la orden
  está *dentro* de la línea deja pasar una letra suelta, porque `ISUBIR`
  contiene `SUBIR`.
- El prompt se compara **quitando espacios por los dos lados**: el de Bangkok
  lleva uno delante. Con `rstrip` no fallaba nada --se esperaba el plazo entero
  en cada turno, y el paseo pasaba de cinco minutos a media hora.
- Tras teclear hay que **darle a la máquina un respiro** antes de leer el eco,
  o se lee la pantalla antes de que le haya llegado la última letra.

### Las claves de las cuatro

Las cuatro aventuras se abren ya sin tocar nada:

| aventura | cómo se entra |
|---|---|
| MegaCorp | `REBECA` --su sala 5000 acepta el verbo 29-- |
| Los pájaros de Bangkok | ninguna: sólo hay que pasar la portada con una tecla |
| El Quijote II | `HIDALGO INGENIOSO` --verbo 80 y nombre 80, en ese orden--, **y hay un solo intento**: cualquier otra cosa imprime el mensaje 100 y se acabó |
| Las vajillas | `SPIELBERG` --un **nombre**, no un verbo: nombrarlo lleva a la sala 21-- |

El espejo juega hoy tres de las cuatro. La que falta es Las vajillas, y por
qué está más abajo.

De paso, la condición de la tabla alta del Quijote que pide un adverbio número
80 es **madera muerta**: sus adverbios son cuatro palabras todas con el número
1, y así está también en el original --comprobado leyendo su lista en memoria--.

### Cómo corta las líneas el original, leído en su propio código

Las dos diferencias que quedaban --el título del Quijote y el eco de
Vajillas-- eran la misma rutina, y las dos se cerraron leyendo, no midiendo.
La rutina es **`$778A`**, por la que pasa cada carácter de un mensaje:

```
$778A  CALL $631E      ; imprime el carácter
       CALL $864B      ; ¿es separador?  (Z si lo es)
       RET NZ          ; no -> nada que decidir
       CALL $6321      ; H = columna donde caerá el siguiente, empezando en 1
       LD B,H
       POP HL
loop:  INC HL          ; cuenta lo que viene hasta el próximo separador
       LD A,(HL)
       INC B
       CALL $864B
       JR Z,fin
       CP $FF
       JR NZ,loop
fin:   LD A,B
       CP $21          ; 33
       CALL NC,$754F   ; a partir de ahí, salto de línea
```

`$864B` da los separadores: fin de texto, espacio, `.`, `,`, `-`, `!`, `?` y
`:` --los mismos que ya teníamos--. Y hay dos detalles en ese bucle que
explican todo lo que no cuadraba:

**Uno: el conteo empieza una letra más allá.** Cuando `$886C` llama a `$778A`,
HL ya ha pasado del carácter que se está imprimiendo, y el bucle hace otro
`INC HL` antes de mirar. O sea que de lo que viene **se salta el primer
carácter**. Haciendo la cuenta, para una palabra de n letras que empezaría en
la columna x, corta cuando `x + n >= 32`: **exactamente la regla que ya
teníamos**. Bien.

**Dos: pregunta después de cada separador, no antes de cada palabra.** Y como
se salta un carácter, lo que mide después de un espacio que va seguido de otro
espacio es el trecho **que empieza en el tercero**. De ahí salen dos cosas que
no teníamos:

- Un separador en mitad de una tirada, con otro detrás y otro más, mide un
  trecho de uno: desde la penúltima columna ya no le cabe, y corta.
- Cuando la palabra que viene no cabe, el que pregunta primero y corta es el
  separador **anterior** al que la precede --si lo hay--, porque su cuenta da
  lo mismo. Así que **un espacio salido de una tirada baja con la palabra** y
  se ve al principio de la línea, mientras que **un espacio que cierra una
  palabra se queda donde está** y la palabra baja sola.

Esas dos son las que faltaban, y con ellas la apertura del Quijote sale
carácter por carácter como la del original:

```
           DON QUIJOTE
             PART II
         PROGRAMA: EGROJ
    GRAFICOS: PABLO Y EGROJ
COPYRIGHT DINAMIC SOFTWARE 1987
 Si en esta parte quieres jugar
la clave tendras que teclear.
```

Fíjese en las dos últimas: `COPYRIGHT` empieza en la columna cero --el espacio
que lo precede cerraba `EGROJ` y se quedó arriba-- y ` Si` empieza en la uno
--ese espacio venía de una tirada de treinta y bajó con la palabra--. La
línea de `COPYRIGHT` mide 31 caracteres, y la de `DON QUIJOTE` también.

### Lo que costó, y de dónde salió el sitio

Está puesto: `word_over` y `word_print` de `z80/common/textout.asm` guardan lo
que cerró la última palabra en vez de imprimirlo, con la marca de si venía
detrás de otro separador en el bit alto del mismo byte; `wrapped()` de
`tests/emulator.py` hace lo mismo, y `runGAC.py` también --resulta que lo de
las palabras ya lo hacía bien sin saberlo y sólo le faltaba lo de las tiradas--.

Costó **66 bytes de código común**, y eso destapó que dos máquinas no los
tenían: al Next con música le quedaban **3** y al CPC 464 con música, **10**.
Ninguna de las dos estaba corta por este cambio; estaban corta y punto, y lo
próximo que creciera las habría roto igual.

**El Next**: la pared de `$A000` no era el final de la máquina. `gfx_clear`
borra la máscara de los rellenos y para ahí, y la pila baja desde `$BF00`, de
modo que entre las dos hay casi cuatro kilobytes que nadie tocaba y que el
fichero ya lleva, porque `SAVENEX BANK 2` se lleva entero `$8000`-`$BFFF`.
`picture.asm` vive ahora en `$B200` --que era por encima de la tabla del modo
dos y de su rutina, y ya no hay ni una ni otra: ver más arriba-- y bajo la
pared quedan quinientos bytes largos.

**El CPC 464**: ahí el código y la base de datos comparten `$4000`-`$B100` y
no hay más, pero debajo de `$4000` hay dieciséis kilobytes de RAM que el
intérprete puede usar --corre con las dos ROMs fuera; por eso la música vive
en `$0300`-- y que sólo estaban esperando a que alguien los cargara. Eso ya
estaba resuelto para el Quijote, con `LOW_CODE`: un mover baja el intérprete a
`$0400` y una isla arriba guarda las llamadas de cinta, que necesitan la ROM.
Lo único que faltaba era que ese build admitiera música, porque la música
estaba justo donde ahora va el intérprete.

Ahora la admite, y **la música se va al otro extremo**: los cinco kilobytes
bajo la isla, que son sitio que habría tenido la base de datos. Se probó
primero ponerla encima del intérprete, y dejaba 183 bytes entre los dos --un
apaño, no una solución--. Así el intérprete se queda la RAM baja entera:

| | intérprete | base de datos |
|---|---|---|
| como estaba | 10 bytes libres | 20593 como mucho |
| bajo, con la música arriba | **4586 libres** | 22272 |

Y no hay que elegir a mano: `regac` ya reintentaba con `LOW_CODE` cuando el
build normal se pasaba del firmware, así que una aventura que no quepa se
cambia de sitio sola. Las dos pruebas del Amstrad hacen lo mismo.

De paso quedó medido lo que cuesta la música de verdad dentro del intérprete
del CPC: **53 bytes** --8282 sin ella, 8335 con ella--. Quitarla de las cinco
máquinas para hacer sitio habría sido pagar una función entera por 53 bytes.

**Lo que queda apretado**: el 464 con MegaCorp II, que ya **no cabe** del
derecho y se repliega solo al mapa bajo. Llegó a tener catorce bytes libres, y
los 103 del clic de tecla se los comieron. No rompe nada, y de hecho ahí gana:
en el mapa bajo el intérprete tiene 6949 libres y la base de datos pasa de
20572 a 27392 bytes. Las otras siete siguen cabiendo del derecho, con entre
1100 y 3100 libres.

### El eco de Vajillas: el original se pasa del terminador

La misma mirada hacia delante **no se para en el `$FF`**. El bucle hace
`INC HL` y mira, y si el carácter siguiente al separador era el terminador ya
se ha pasado de él: sigue contando bytes del buffer de desempaquetado
--`$5E18`-- que son las sobras del mensaje anterior.

Por eso el prompt de Las vajillas, `QUE VAS A HACER AHORA?...`, unas veces
deja el eco detrás y otras lo manda a la línea siguiente: acaba en punto, que
es separador, en la columna 24, y lo que decide es lo que quedara en el buffer
pasado el terminador. Turno a turno es distinto.

**Eso no se copia.** Depender de basura de un buffer no es una conducta del
intérprete sino un accidente de su memoria, y reproducirlo exigiría imitar
también el desempaquetado byte a byte. Las vajillas se queda, por eso, fuera
del espejo, y su clave --`SPIELBERG`, un nombre, no un verbo: nombrarlo lleva
a la sala 21-- queda apuntada aquí para cuando haga falta.


## Las tintas del Amstrad, que nunca se habían puesto

**Cómo se escondió.** El original pone ocho bytes de tintas delante de cada
lámina, y `deGAC` los guardaba en `gfx_inks` desde que se leyó el primer
disco. El formato no los llevaba, y lo que quedó dicho de eso fue un
comentario en `z80/cpc/screen.asm` --«until the format holds them these are
the four the machine starts with»-- y nada en este diario. Salió a la luz por
casualidad, preparando el PC. **Lo que se aplaza va aquí, no a un
comentario.**

**Lo que hace el original**, leído en su intérprete (el detalle, con las
direcciones, en `graficos.md`, «Las tintas de una lámina»): la lámina de un
cuarto pone sus tintas --el borde de la primera pareja, luego las cuatro
plumas--, una lámina llamada desde otra se salta las suyas, y una pareja de
dos colores parpadea al ritmo del firmware, diez fotogramas cada uno, el
segundo byte primero.

**Lo que hace el nuestro ahora:**

- **El formato** lleva los ocho bytes delante de la longitud de cada lámina,
  sólo en el CPC y sólo si la aventura los trae; el último byte de la
  configuración dice cuántos son. Ver `binario.md`. (Una aventura de Spectrum
  salía entonces igual que antes más ese byte; desde que el CPC la dibuja con
  las reglas del Spectrum lleva doce por lámina: ver más abajo.)
- **El formato fuente** los escribe en la cabecera de la lámina,
  `#9 inks=0,13,17/0,20`; las 44 láminas de Bangkok hacen el viaje de ida y
  vuelta sin perder ninguna, las tres que parpadean incluidas.
- **El intérprete** los pone en `draw_picture`, que es el camino de un cuarto,
  y no en `CALL`. El parpadeo va en `scan_keyboard`: con las interrupciones
  cortadas no hay fotogramas que contar, pero cada espera de tecla es mirar el
  teclado `LOOKS_A_FRAME` veces por fotograma, que está medido. Cambia en el
  retrazo, como el firmware, esperándolo como mucho un fotograma de cada diez
  y sólo mientras una pluma parpadea.

**La diferencia que queda, dicha**: el firmware parpadea siempre; el nuestro,
sólo mientras espera una tecla. Mientras dibuja una lámina o escribe un
mensaje, las tintas se quedan quietas. Hacerlo siempre pediría las
interrupciones, y el intérprete las corta a propósito --el baile del teclado
con el chip de sonido no admite que nadie lo interrumpa, ver `keyboard.asm`--.
Afecta a cuatro láminas de las 91 de las tres aventuras de Amstrad, y durante
lo que tardan en dibujarse.

Le costó al 464 **105 bytes** de intérprete, y siguieron cabiendo sin cambiar
nada las mismas cinco aventuras de las ocho; la que va más justa, Bangkok2,
quedó a 1070 bytes del firmware. (Con las reglas del Spectrum, más abajo,
son 614.)

### Y los tres fallos que había debajo, que ninguna prueba veía

Al mirar la pantalla por colores y no por plumas salieron tres, y los tres
son del primer día:

| | qué hacía | qué salía |
|---|---|---|
| elegir pluma | con `%01...`, que es *dar color* a la pluma elegida, no elegirla | **ninguna tinta se puso nunca**: la pantalla enseñaba las del firmware, 1, 24, 20 y 6, dijera lo que dijera `picture_inks` --que decía 0, 24, 20, 6--, y el fondo salía azul en vez de negro |
| `mode_init` | `inc hl` sobre un HL que `hardware_ink` acababa de machacar | las plumas uno a tres, de la tabla del hardware y no de las tintas; no se notaba porque nada llegaba a ponerse |
| `firmware_inks` | la 24 y la 26 cambiadas | pedir amarillo daba blanco |

Ninguno lo podía ver una prueba: todas leían la pantalla como plumas. Ahora
`tests/test_inks_cpc.py` le pide al emulador la pantalla como imagen
(`save-screen`, un BMP con sus colores) y mira qué tintas hay en ella; y las
27 de la tabla están comprobadas contra el emulador, de cuatro en cuatro.

Las tintas de una lámina de Amstrad sin tintas propias pasan a ser
**1, 24, 20 y 6**, las del firmware al arrancar: es lo que la pantalla enseñó siempre --por el
primer fallo--, y es lo que el comentario de `picture_inks` decía querer.

Y un cuarto, de acuerdo con la referencia y no de la pantalla: `BORDER n`, que
sólo tiene una lámina de Spectrum, le daba al borde la tinta del firmware
número `n`. `AmstradDevice` le da el color de la pluma `n & 3`, y ahora el Z80
también.

### Y lo que salió al mirar: las aventuras de Spectrum no se ven en el CPC

El intérprete del CPC dibuja con las reglas del Amstrad: el relleno se para
donde cambia la pluma, la tinta es `& 3`, y un relleno va en la pluma que
diga `PENS`, que ninguna lámina de Spectrum tiene, así que va siempre en la
uno. La prueba de las 196 láminas lo compara punto por punto contra
`AmstradDevice`, que hace lo mismo, y por eso pasa. Contra el Spectrum, que es
lo que esas láminas son, cubriendo cada relleno más de un 2 % distinto:

| aventura | láminas | rellenos |
|---|---:|---:|
| Bangkok1 | 30 de 32 | 240 de 793 |
| Bangkok2 | 23 de 28 | 221 de 402 |
| megacorp1 | 8 de 33 | 37 de 681 |
| megacorp2 | 20 de 31 | 59 de 783 |
| quijote1 | 22 de 25 | 375 de 975 |
| quijote2 | 17 de 20 | 541 de 926 |
| vajillas1 | 11 de 11 | 470 de 1384 |
| vajillas2 | 15 de 16 | 233 de 1816 |

**146 de las 196.** Comprobado en el emulador con Bangkok1 #7: una figura
sobre fondo negro en el Spectrum sale como unos trazos azules sobre una
lámina entera amarilla. Y las herramientas no lo decían: `checkgfx -m cpc`,
que `manual.md` recomienda para esto, mide con `PixelDevice`, un modelo que la
máquina no usa, y dice que todo está bien; `render -m cpc` dibuja con ese
mismo; y `render -m amstrad` se cae, porque `AmstradDevice.to_rgb` devuelve
enteros donde el PNG quiere ternas. (Las tres cosas quedaron bien con lo de
más abajo: el CPC dibuja ahora con ese mismo modelo, `render` enseña lo que
enseña la máquina y ya no se cae.)

**Decidido: fiel a GAC.** Una aventura se dibuja con las reglas del GAC de su
máquina: una de Amstrad con las del Amstrad, que es lo que hay; una de
Spectrum con las del Spectrum --el relleno se para en un punto encendido, con
la máscara de un bit que ya llevan el Next y el Sam, y la tinta y el papel
llevados a cuatro tintas por lámina, elegidas contra la referencia--. Es lo
que `graficos.md` planeaba en «Las dos familias de color» y el Z80 nunca
llegó a hacer. Cada compilación lleva un solo modelo, el de la aventura, así
que el código no se suma. Y la máscara, 4 KB, cabe: en el 464 normal, debajo
de $4000, que con las ROM fuera es RAM libre --el firmware no la puede leer,
pero la máscara sólo la usa el intérprete mientras dibuja--; en el del
Quijote, entre el final del código, hacia $2400, y $4000; en el 6128, en los
casi ocho kilobytes que quedan por encima del intérprete.

**Y al revés, decidido también: una aventura de CPC se dibuja con las reglas
del CPC en cualquier máquina, pero sólo va a las máquinas que tengan sitio.**
Las reglas del CPC necesitan saber de qué pluma es cada punto, y en una
máquina de un bit por punto --el Spectrum, el PCW-- eso es un búfer aparte de
dos bits por punto, 8 KB para la lámina, que sale del sitio de la base de
datos; en un Spectrum 48 es mucho. El código no crece --cada compilación
lleva un solo modelo, el de la aventura--; la memoria, sí. Cuánto le cuesta a
cada máquina está por medir --el Next, el MSX y el PC no se han mirado--, y
donde no quepa, `regac` lo dice con un mensaje claro en vez de compilar algo
que dibuja mal. (Hecho, y ya no detrás del PC: el Next sabe, y las demás lo
dicen; ver «Las aventuras de Amstrad en el Next, y en ninguna otra».)

### Hecho: el CPC dibuja las aventuras de Spectrum con las reglas del Spectrum

**Qué modelo lleva una compilación** lo dice de dónde viene la aventura: el
`model` que `deGAC` escribe y el formato fuente guarda en `/CTL`. Con `CPC`,
`regac` ensambla con `-DAMSTRAD_PICTURES` y entran `draw.asm`, `shapes.asm` y
`fill.asm`, que son lo de siempre. Sin él entran `spectrum.asm`,
`../common/shapes.asm` y `spectrum_fill.asm`: el dibujo del Next --la máscara,
la recta de la ROM, la elipse del Spectrum, el relleno del Spectrum-- con la
pantalla del CPC debajo. Lo que comparten los dos, las tablas de plumas y
dónde cae un punto, está en `pixels.asm`. **Una compilación lleva uno solo.**

**Los colores**: cada lámina lleva cuatro tintas y la pluma a la que va cada
uno de los dieciséis colores, en los mismos bytes delante de la longitud que
abrieron las tintas del Amstrad --doce aquí: las cuatro por parejas y cuatro
de mapa--. Se eligen al construir la base de datos con `cpc_picture_colours`,
pesando cada color por lo que cubre en la lámina de referencia, y **la
referencia de las pruebas sale de la misma función**, así que las dos no
pueden discrepar. Un relleno se tiende de byte en byte: el patrón del
Spectrum va alineado con la x, así que un byte de pantalla, que son cuatro
puntos, lleva siempre su primera mitad o la segunda, y las dos se calculan una
vez por tramo.

**La máscara** va en $3000 en el 464, con y sin `LOW_CODE`, y en el 6128 en la
primera página detrás del intérprete, compartiendo sitio con donde se monta
una partida guardada: nunca se quieren a la vez.

**Lo que dio**: las **196 láminas, punto por punto iguales** a la referencia
fiel en el emulador. En el 464 siguen cabiendo las mismas cinco aventuras; la
más justa, Bangkok2, a 614 bytes del firmware. **Y el tiempo, que era lo que
el presupuesto de 4-5 s no cumplía**: con las reglas del Amstrad sólo tres
aventuras lo cumplían, y con las del Spectrum lo cumplen las ocho. Por qué
tanto en el Quijote no está medido; lo que se ve es que con las reglas del
Amstrad sus rellenos cubrían otra cosa --son de las láminas de la tabla de
arriba--.

| aventura | reglas del Amstrad | reglas del Spectrum |
|---|---:|---:|
| Bangkok1 | 2,4 s | 3,2 s |
| Bangkok2 | 4,1 s | **5,0 s**, en el borde |
| megacorp1 | 2,3 s | 2,8 s |
| megacorp2 | 2,9 s | 3,5 s |
| quijote1 | 16,8 s | 2,9 s |
| quijote2 | 25,3 s | 3,6 s |
| vajillas1 | 7,8 s | 4,2 s |
| vajillas2 | 6,9 s | 3,7 s |

Los techos de `test_all_pictures_cpc.py` van con estos números.

**Y el rechazo decidido**: `Database` no construye una aventura de Amstrad
para otra máquina, y `checkgfx` no compara una aventura de Amstrad con el
Spectrum, que no es lo que es. El C64, cuyas láminas también son de plumas,
sigue aparcado y no se toca aquí.

### El texto, que comparte las cuatro plumas con la lámina

**El original del CPC imprime en la pluma uno sobre la cero y no las cambia
nunca mientras se juega**: `TXT SET PAPER` no está en ningún sitio, y
`TXT SET PEN` sólo en $2630, que pone una pluma, imprime y deja la uno --y a
$2630 sólo la llaman $29AD, $2F92 y $320A, que por la zona son del editor de
láminas--. O sea que el color del texto es el de las plumas cero y uno de la
lámina del cuarto, y cambia con ella.

**Decidido**, y hecho:

- **Una aventura de Amstrad**: la letra en la pluma uno sobre la cero, como
  el original. Un `\ink n` en un mensaje --que es nuestro, el GAC del 86 no
  tenía color en el texto-- sigue siendo la pluma `n`.
- **Una aventura de Spectrum**: blanco sobre negro, como en el Spectrum, y un
  `\ink n` o el `ink n` de `/CTL` son **colores**, que van a la pluma a la que
  va ese color en la lámina, como un color de la lámina. Para que eso no
  estropee el texto que ya está escrito cuando llega otra lámina, las cuatro
  tintas se reparten con la más cercana al negro en la pluma cero y la más
  cercana a la tinta del texto en la uno --qué pluma lleva cada tinta no le
  cambia nada a la lámina--. Así el papel y la letra son siempre las plumas
  cero y uno, como en el original.

Contado sobre las 196: **194 dejan el texto legible**. Las dos que no son las
láminas de los cuartos 1001 de megacorp1 y 5000 de megacorp2, que son negro,
azul, azul brillante y rojo y no tienen ninguna tinta clara: ahí el texto sale
en azul brillante sobre negro. Es lo que la lámina da de sí; está dicho para
que no sorprenda.

**Y lo que había debajo, otra vez sin que nada lo viera**: `text_ink` tenía
cruzadas la pluma uno y la dos. Lo que lo tapaba es que la tinta por defecto
se había escrito como un dos, y un dos cruzado es la pluma uno, que es la del
original; un `\ink 1` o un `\ink 2` en un mensaje salían en la otra. La
prueba nueva mira el texto por colores, con un `\ink 3` a propósito: con un
cambio a la dos la pantalla enseña los mismos tres colores estén cruzadas o
no, y se comprobó que así sí falla con las plumas cruzadas.

## Las aventuras de Amstrad en el Next, y en ninguna otra

Lo decidido era que una aventura de Amstrad se dibuja con las reglas del
Amstrad en cualquier máquina **que tenga sitio**. Mirado máquina por máquina
--lo marcado *deducido* sale de los fuentes y de los binarios, no de una
medida--:

| máquina | ¿guarda la pantalla la pluma de cada punto? | un búfer de 8 KB para las plumas | color |
|---|---|---|---|
| Next | **sí**: layer 2 es un byte por punto | no hace falta | paleta programable |
| MSX1 | no: dos colores por cada 8×1 | cabría detrás de la base de datos (*deducido*) | con choque en horizontal |
| Spectrum 128 y +3 | no: un bit por punto, color por celda | hay bancos, pero se ven por la ventana de $C000 que usa la base de datos, y dibujar necesita las dos a la vez | con choque de 8×8 |
| PCW | no: un bit por punto, sin color | bancos de sobra, sin mirar cómo mapearlo | las plumas a tramas |
| Spectrum 48 | no | quedan 3-8 KB según la aventura (*deducido*) | con choque de 8×8 |

Y dos cosas que pesan: **sólo hay tres aventuras de Amstrad** --Bangkok,
MegaCorp y las Vajillas, seis partes--, y **las tres tienen versión de
Spectrum**, que va a todas las máquinas. En todas salvo el Next habría que
decidir cómo se ven cuatro plumas por punto en una pantalla con choque o sin
color, y eso ya no es leer el original: el GAC de esas máquinas nunca dibujó
una lámina de Amstrad.

**Decidido: el Next, y ninguna otra.** Las demás no las construyen: `regac
build` y `regac make` lo dicen con una frase --«this adventure was written on
an Amstrad, and its pictures are drawn with the Amstrad's rules; msx does not
know them; cpc and next do»-- y no con una traza, que es lo que salía la
primera vez. Prueba en `test_errors.py`.

**Cómo lo hace el Next.** Una compilación con `-DAMSTRAD_PICTURES` lleva
`next/amstrad.asm`, `../cpc/shapes.asm` --la elipse del Amstrad, que sólo pide
la recta-- y `next/amstrad_fill.asm`, en vez del dibujo del Spectrum; lo que
comparten, en `next/pixels.asm`. Un punto de layer 2 es su pluma, de cero a
tres, y **no hay máscara**: el relleno que se para donde cambia la pluma mira
las plumas en la propia pantalla. El código acaba en $9EA8 con cualquiera de
las seis, y los 4 KB de la máscara quedan libres.

- **Las tintas** de cada lámina van a las cuatro primeras entradas de la
  paleta de layer 2, con las mismas reglas que en el CPC: las pone la lámina
  del cuarto y no la llamada con `CALL`, y parpadean mientras se espera
  tecla, en el retrazo --aquí, esperando a que la línea de vídeo pase de la
  192--. **No son exactas**: los tres niveles de cada canal del Amstrad van al
  más cercano de los ocho del Next, así que el medio del Amstrad, 128, sale
  146.
- **El borde** es el de la ULA, así que se le da la tinta a la entrada 16 de
  la paleta de la ULA --la del papel del color cero-- y al puerto un cero.
  Comprobado en pantalla.
- **El texto**, como en el Amstrad: pluma uno sobre pluma cero, y `\ink n` es
  la pluma `n`.

**Lo que dio**: las **187 láminas de las seis aventuras de Amstrad**, punto por
punto iguales a `AmstradDevice` **en el Next y en el CPC**. Es la primera vez
que el intérprete del CPC dibuja en una prueba láminas de Amstrad de verdad
--hasta hoy sus reglas se probaban con las ocho de Spectrum, que no eran para
ellas--, y `AmstradDevice` es el que se contrastó contra el original punto por
punto. En el CPC la peor tarda 2,6 s. Las aventuras las saca de los discos de
`juegos/` `tests/amstrad_games.py`, con `disk.py` y `deGAC`; las pruebas son
lentas y van con `REGAC_SLOW=1`.

### Y el magenta brillante del Next, que no se veía

Al mirar el Next por colores salió otro de los que nadie veía. **Layer 2 no
enseña los puntos del color $E3**: es su color transparente de fábrica, y deja
ver lo que haya debajo. Y $E3 es justo lo que el magenta brillante del
Spectrum da en nueve bits --y el del Amstrad también--. Comprobado en el
emulador: una caja rellena de magenta brillante salía en negro. Lo usan **dos
láminas de las ocho aventuras**, Bangkok1 #46 con 288 puntos y Bangkok2 #20
con 839, y en el Next esos puntos no estaban. Ahora el intérprete le da al
registro de transparencia $01, que no es ningún color de los que le pone a la
paleta, ni del Spectrum ni del Amstrad. `test_inks_next.py` lo mira en
pantalla, y se comprobó que falla sin el arreglo.

## PC XT con CGA: el paso uno, que era el que podía matarlo

No está decidido hacerlo. Lo que sigue es lo único que había que saber antes
de decidir: **si un 8088 a 4,77 MHz puede dibujar nuestras láminas dentro del
tope de cuatro o cinco segundos**. Sale que sí, y con holgura.

### Por qué el Amstrad es la máquina con la que comparar

CGA en modo 4 es 320 por 200, dos bits por píxel, cuatro colores, ochenta
bytes por fila. Eso es **exactamente** el modo 1 del Amstrad, hasta el ancho
de fila. **En la forma, no en el color**: el Amstrad puede poner cualquiera
de sus veintisiete tintas en cada pluma y la CGA sólo deja libre el fondo
--ver «Y una cuarta: la paleta», más abajo--. Para el dibujo y su cuenta da igual, y en la
forma hay dos diferencias, las dos a favor:

- **El empaquetado de CGA es más simple.** El Amstrad reparte los dos bits de
  cada píxel por el byte --los pares 3/7, 2/6, 1/5, 0/4-- y CGA los pone
  seguidos, de dos en dos.
- **Cuarenta columnas de texto**, que es lo que tiene el Amstrad, así que la
  regla de partir líneas vale tal cual.

Y a favor está también lo que ya sabemos: las peores láminas del Amstrad están
**medidas**, con el contador de ciclos parado en seco, después de la
optimización que las bajó de cuarenta y cinco segundos: **4,17 s y 4,87 s**.

### La cuenta

Los tres bucles de los que está hecho el dibujo, contados en relojes del Z80
como el gate array los cobra de verdad --cada instrucción redondeada hacia
arriba a múltiplo de cuatro-- y contra la instrucción del 8088 que hace lo
mismo:

| | Amstrad | XT | veces |
|---|---:|---:|---:|
| recorrer un tramo, por byte | 9,00 µs | **3,14 µs** | 2,9 |
| pintar un tramo, por byte | 8,00 µs | **2,10 µs** | 3,8 |
| un punto suelto | 16,00 µs | 12,58 µs | 1,3 |

Los dos primeros son `cpi`/`cpd` con sus dos saltos y `ld (hl),a` / `inc hl` /
`djnz`, que es lo que hay en `z80/cpc/fill.asm`; en el 8088 son `repe scasb` y
`rep stosb`, una instrucción cada uno.

**Y aquí está lo que no esperaba.** La debilidad del 8088 es su bus de ocho
bits, que le cuesta cuatro relojes de más por cada acceso de dieciséis y le
mata la cola de prefetch en cada salto. Nuestros dos bucles calientes son
**instrucciones de cadena de un byte**: no leen palabras, y mientras un `rep`
corre no se busca ni una instrucción. O sea que caen justo en el único sitio
donde un 8088 corre a la velocidad de un 8086. El caso peor de esa máquina es
precisamente el que no le toca.

### Lo que sale

Si una lámina entera fuera tramos, saldría por lo bajo; si fuera toda puntos
sueltos, por lo alto. La verdad está en medio, y más cerca de lo bajo, porque
la optimización del Amstrad consistió justamente en que casi todo fueran
tramos:

| lámina | Amstrad, medido | XT, estimado |
|---|---:|---|
| quijote1 #8 | 4,17 s | entre **1,1 y 3,3 s** |
| megacorp2 #29 | 4,87 s | entre **1,3 y 3,8 s** |

Contra un tope de cuatro o cinco. **Cabe.**

### Los asteriscos, que son dos y uno es gordo

**La nieve de CGA.** Una tarjeta CGA de IBM auténtica no frena al procesador
cuando se escribe en `B800` mientras el haz pinta: deja escribir a toda
velocidad y lo que sale es *snow*. La cuenta de arriba vale tal cual **si se
acepta la nieve**. Si no se acepta, hay que escribir sólo fuera del barrido, y
eso multiplica por varias veces la parte que toca pantalla y se come la
holgura entera. Los clónicos no nievan. **Es una decisión, no un detalle**, y
conviene tomarla antes y no descubrirla con hardware real, porque un emulador
normalmente no la modela.

**La base de datos en otro segmento.** Un `es:` de más cuesta dos relojes por
acceso, y nuestra contabilidad interna --la pila de tramos-- es de dieciséis
bits, que es donde el 8088 sí paga sus cuatro relojes. Eso queda fuera de esta
cuenta, que mira sólo el dibujo.

### Y qué es esto y qué no es

**No es una medida, es una estimación con la cuenta a la vista**, hecha de
tres bucles y de los tiempos publicados del 8088. Lo que la hace fiable es
que los dos bucles que deciden son de una instrucción y no dependen del
prefetch; lo que la hace una estimación y no otra cosa es que el tercero sí.

### El paso dos, hecho: la cadena entera funciona

Probada de punta a punta, y **sin descargar nada**: NASM y DOSBox-X ya
estaban en la máquina.

```
spike.asm --nasm -f bin--> spike.com --DOSBox-X (machine=cga)--> SCREEN.BIN --> Python
```

El programa pone el modo 4, pinta diez filas con `rep stosb` --la instrucción
de la que depende toda la estimación-- y vuelca los 16384 bytes de `B800` a un
fichero. Lo que volvió:

| | |
|---|---|
| tamaño | 16384 |
| lo pintado | todo a `FF`, diez filas de ochenta bytes |
| detrás de eso | a cero |
| banco impar | a cero, que es lo correcto: las filas pares viven en el banco 0 |

Exacto, hasta el entrelazado de bancos.

**Y aquí está lo que hace fácil este target**, que no se ve hasta que se
prueba: un DOS tiene sistema de ficheros, así que **el programa entrega su
propia pantalla como fichero**. Ni protocolo remoto, ni escribir en la memoria
de una máquina en marcha, ni apuntarle el contador --que es justo la parte del
arnés que más guerra ha dado en las cinco máquinas Z80--. La prueba se reduce
a: ensamblar, correr, leer un fichero.

**La pega, que costó encontrarla:** DOSBox-X se cuelga si se lanza sin
`-fastlaunch`. Con `-conf`, `-fastlaunch` y `-exit` corre, hace lo suyo y se
va solo.

```
[dosbox]
machine=cga
[cpu]
cycles=fixed 315
[autoexec]
mount c .
c:
spike.com
exit
```

**Lo que falta para un target de verdad**, por orden:

1. ~~La **cabecera MZ** para el `.EXE`, que son 28 bytes escritos por `regac`
   --sin reubicaciones si los segmentos se calculan en marcha desde `CS`--.~~
   Hecha: ver «La cabecera MZ, cargada por el DOS de verdad», más abajo.
2. ~~Un **`CgaDevice`** en `regac/devices.py` y la comparación de láminas
   contra la referencia, antes de que exista intérprete: es como se hicieron
   las otras cinco.~~ Hecho: ver «El `CgaDevice`, como el CPC», más abajo.
3. ~~Sólo entonces, el intérprete en 8086.~~ Hecho: empezado por las láminas
   --ver «El intérprete de PC empieza por las láminas, y salen iguales»-- y
   terminado en «El intérprete de PC, entero», más abajo.

**Y un emulador con reloj fiel, si alguna vez se quiere verificar la
estimación de tiempos** y no sólo que las láminas salen bien. DOSBox-X con
`cycles=fixed 315` se parece a un XT pero no es exacto al ciclo; para eso
harían falta **86Box** o **MartyPC**, que no están instalados. Para la
corrección, DOSBox-X sobra.

### Tres decisiones tomadas, para no volver a discutirlas

**El *snow* de la CGA se ignora.** Sólo lo hacían las tarjetas CGA originales
de IBM, y de ésas apenas queda ninguna. Nada de sincronizar con el retrazo ni
de leer el puerto de estado antes de escribir: se escribe en `B800` y ya.

**El XT a 4,77 MHz es el mínimo, no el objetivo.** Lo recomendado es un
clónico XT turbo. Eso importa para leer bien la estimación de arriba, que está
hecha **a 4,77**: en la máquina recomendada el margen de dibujo es
aproximadamente el doble. O sea que el presupuesto de 4-5 s, que es lo que
podía matar este target, está más holgado de lo que dice el número.

**NASM solo, sin enlazador.** `nasm -f bin` saca un binario plano y `regac` le
escribe delante la cabecera MZ, que es exactamente lo que ya
se hace en las otras cinco máquinas: sjasmplus saca el binario y Python
escribe el contenedor —`.tap`, `.cdt`, `.dsk`, `.nex`, `.cas`—. Una cabecera
MZ es el más pequeño de los seis. Tres razones:

- **El código cabe en un segmento.** Los intérpretes Z80 andan por los 8-9 KB
  y un 8086 no se irá mucho más lejos; lo grande es la base de datos, que no
  es código. Sin pasar de 64K de código, un enlazador no resuelve nada que
  tengamos.
- **Sin reubicaciones**, calculando los segmentos desde `CS` en marcha.
- **La cadena está probada en esta máquina y sin descargar nada.**

**Y lo de Watcom queda abierto a propósito, para el intérprete --el tercero
de la lista de lo que falta-- y no para antes.**
El argumento a favor es mejor de lo que parece: **el intérprete de PC duplica
toda la lógica de todas formas**. Los 9 KB de `z80/common/` —el parser, la
máquina de condiciones, el reparto de texto, el intérprete de láminas— no se
comparten ni escribiéndolo en 8086, así que «C no comparte nada» vale igual
para el ensamblador; y si hay que mantener una segunda implementación, en C
cuesta menos escribirla y menos equivocarse.

En contra está el dibujo: en el Z80 el relleno del Amstrad pasó de 45 s a 4
apretándolo a mano, y eso en C no sale. El camino sensato sería C para la
lógica y ensamblador para los bucles de relleno y recta, y eso ya pide `wlink`
y dos herramientas nuevas.

No hace falta decidirlo ahora: **el `CgaDevice` no necesita intérprete
ninguno**. Él y la comparación de láminas se hacen en Python contra la
referencia, igual que en las otras cinco máquinas, y cuando eso esté se decide
el lenguaje con las láminas ya comparando.

(Los números de «paso uno» y «paso dos» de los títulos no son los de la
lista de lo que falta, que vuelve a empezar en uno. Por eso aquí se dice
qué es cada cosa y no su número.)

### Decidido ya: NASM solo, sin enlazador, y no en un segmento

**El intérprete de PC va en ensamblador, con NASM y sin enlazador.** Lo que
inclinó la balanza: los bucles que deciden el tiempo tienen que ir en
ensamblador de todas formas, y escrito así el intérprete puede seguir rutina a
rutina la forma de `z80/common/`, que es lo que deja comprobar que hace lo
mismo que los de 8 bits y que el original.

**El enlazador se miró y se descartó por el usuario de `regac`**, que es quien
tiene que conseguir las herramientas. NASM es un zip de 626 KB
(`nasm-3.02-win64.zip`, en nasm.us) que va a `tools/` o al PATH, como
`sjasmplus`. Open Watcom no publica `wlink` suelto: sería bajarse un paquete de
128 a 150 MB para sacar un fichero. JWlink no tiene versiones publicadas y
ALINK es de 1999. Y lo que un enlazador daría, aquí lo da NASM: módulos con
`%include`, como los intérpretes de Z80, y las direcciones de las etiquetas en
el mapa que escribe con `[map]`, que es lo que las pruebas leen del listado de
sjasmplus.

**Una corrección a lo de arriba**: en esta máquina *sí* había enlazadores sin
descargar nada --`wlink` de Open Watcom 1.9 en `E:\proyectos\DOSDEV\WATCOM1`
y ALINK 1.6 en `E:\proyectos\DOSDEV\bin`, los dos arrancan--. No cambia la
decisión, que es por el usuario y no por esta máquina.

**Y no todo en un segmento de 64 KB**, que habría sido un límite sin motivo. El
`.EXE` que carga el DOS puede ser mucho mayor que eso, y un programa puede usar
los segmentos que quiera si calcula dónde empieza cada uno desde `CS` al
arrancar, que es lo que ya estaba decidido para no tener reubicaciones:

- el código, en `CS` --los intérpretes Z80 andan por los 9 KB--;
- los datos y la pila, en un segmento suyo;
- la base de datos detrás, del tamaño que sea, **en bancos de 64 KB** como los
  del 128, el 6128 o el Next: el formato ya viene partido en secciones y
  bancos, y aquí traer un banco es cambiar `ES`;
- y la memoria de trabajo --la máscara, la partida-- la que se le pida al DOS
  en la cabecera, detrás de todo.

Un solo `.EXE`, hecho con NASM y `mz_exe`, y el límite es la memoria del PC.
Un enlazador sólo haría falta para código en varios segmentos que se llamen
entre sí, y el intérprete no va a pasar de 64 KB de código.

### Y una cuarta: la paleta, trío y fondo por lámina

Lo que el «exactamente el modo 1 del Amstrad» de arriba callaba. En el modo 4
de la CGA el color 0 es el fondo, y ése se elige entre los dieciséis, pero los
otros tres vienen en tríos fijos:

| | normal | brillante |
|---|---|---|
| paleta 0 | verde, rojo, marrón | verde, rojo y amarillo claros |
| paleta 1 | cian, magenta, gris | cian, magenta claros, blanco |
| modo 5 | cian, rojo, gris | cian, rojo claros, blanco |

El último es el modo 5, que en la CGA quita la señal de color y en un
monitor RGB da ese trío. Seis tríos por dieciséis fondos son **noventa y seis
paletas**.

**Decidido: trío y fondo por lámina.** Y conviene dejar escrito lo que pasó al
decidirlo, porque se dijo mal: se dio por hecho que el CPC ya elegía sus
tintas por lámina, y no las elegía --cargaba siempre las mismas,
«until the format holds them» decía el código, y ni siquiera ésas, como se
vio después: ver «Las tintas del Amstrad, que nunca se habían puesto»--.
`choose_inks` sólo lo usaba el lado de Python.

**Y lo medido aquí está medido sobre el modelo equivocado.** La elección se
probó dibujando cada lámina con las plumas del Amstrad --tinta `& 3`, el
damero de dos plumas, el relleno que se para al cambiar de pluma:
`AmstradDevice`-- y mirando para cada pluma qué colores tiene la referencia de
Spectrum en esos puntos. Pero la regla es **ser fiel a GAC**: una aventura de
Spectrum se dibuja con las reglas del Spectrum en cualquier máquina, y el
modelo del Amstrad sólo vale para una aventura de Amstrad. Así que en el PC la
elección tendrá que hacerse sobre el dibujo con las reglas del Spectrum, igual
que el CPC después de su arreglo, y la tabla de abajo **hay que rehacerla**
entonces --rehecha en «El `CgaDevice`, como el CPC»--. Se queda como lo que es:
la prueba de que una paleta fija se queda corta. Sobre las 196 láminas, con
aquel modelo:

| trío | láminas |
|---|---:|
| paleta 0 | 143 |
| paleta 0 brillante | 28 |
| modo 5 | 13 |
| paleta 1 | 11 |
| modo 5 brillante | 1 |
| paleta 1 brillante | 0 |

Y el fondo: negro en 121, gris en 42, cian en 23, gris oscuro en 8 y cian
claro en 2. La paleta fija que se habría puesto de oficio --cian, magenta y
blanco sobre negro-- no la elige **ninguna**. Las 196 se eligen en 28
segundos de Python, que es lo que cuesta dibujar cada una dos veces.

Para que llegue a la máquina, el formato tiene ya dónde: los bytes que cada
lámina lleva delante de sus órdenes, que se abrieron para las tintas del
Amstrad y que dice cuántos son el último byte de la configuración. Va con el
intérprete, el tercero de la lista. Al intérprete le cuesta un byte en el
puerto `3D9h` por lámina, que lleva el fondo, la paleta y el brillo; el trío
del modo 5 pide además otro en `3D8h`, que es donde se pone ese modo. Una paleta fija
para todas las láminas era más simple y habría sacado feas muchas de ellas.

Como el GAC no tuvo versión de PC, aquí no hay original al que ser fiel: es
una decisión y no una lectura.

### El `CgaDevice`, como el CPC

**Decidido: el PC se hace como el CPC**, que es lo que el modo 4 de la CGA es
en forma --320 por 200, cuatro plumas, cuarenta columnas--. Una aventura de
Spectrum se dibuja con las reglas del Spectrum, con la máscara, y cuatro
colores elegidos para cada lámina contra la referencia; una de Amstrad, con
las del Amstrad, que la CGA puede hacer porque, como el CPC, tiene la pluma de
cada punto en la pantalla. El texto, con las reglas del CPC. Y **el dibujo no
es de la CGA**: es `PixelDevice` o `AmstradDevice`, los mismos contra los que se
comparan las otras máquinas. Lo de la CGA en `regac/devices.py` es sólo:

- **Los colores**: los dieciséis del monitor de IBM, con su marrón, y los seis
  tríos, cada uno con los bytes de `3D9h` y `3D8h` que lo ponen.
- **La elección**: de las noventa y seis paletas, la que menos se aparta de la
  lámina, pesando cada color por lo que cubre.
- **La memoria**: `cga_screen` pone la lámina como la tiene la tarjeta en
  `B800` --cuatro puntos por byte, las filas pares en un banco y las impares
  en otro, ocho bytes adentro--, que es contra lo que se comparará lo que
  vuelque el intérprete en DOSBox-X.
- `render -m cga` la dibuja.

**Lo único que la CGA obliga a hacer distinto del CPC es el orden.** Allí las
cuatro tintas se ponen en las plumas que se quiera; aquí el valor cero es el
fondo y del uno al tres el trío tal como viene. De eso salen dos cosas:

- **En una aventura de Spectrum** el papel y la letra del texto van donde
  caigan el negro y la tinta del texto, no a la cero y a la uno. Medido: el
  negro queda en el fondo en 185 de las 196, y el blanco en el valor tres en
  190.
- **En una de Amstrad las plumas se reparten.** Si la pluma dos tuviera que
  ser el valor dos, una lámina en amarillo y blanco sobre negro --Bangkok #3--
  saldría con el blanco en el magenta del trío que tiene blanco. Pero lo que
  las reglas del Amstrad le piden a una pluma es sólo que se distinga de las
  otras: un relleno para donde cambia la pluma, y eso sigue igual con las
  cuatro plumas repartidas entre los cuatro valores en cualquier orden,
  siempre el mismo en toda la lámina. Así que se reparten como convenga a los
  colores --de las noventa y seis paletas por veinticuatro repartos, la más
  cercana a las tintas de la lámina, pluma a pluma, pesada por lo que cubre
  cada una--. Bangkok #3 sale con el blanco en el fondo y el negro en su
  sitio, y el amarillo en rojo claro: ningún trío con negro tiene amarillo.

**Rehecha la tabla de antes**, ahora con las reglas del Spectrum, que son con
las que se dibujan estas láminas:

| trío | láminas |
|---|---:|
| paleta 1 | 92 |
| modo 5 | 44 |
| paleta 0 brillante | 38 |
| paleta 0 | 21 |
| modo 5 brillante | 1 |
| paleta 1 brillante | 0 |

El fondo, negro en 176. Colores que se pierden, contando los que cubren algo:
**ninguno en 60** láminas, uno en 103, dos en 27 y tres en 6 --peor que en el
CPC, que elige entre veintisiete tintas y no pierde ninguno en 125--. Y el
texto, blanco sobre negro pasado por el mapa de cada lámina, legible en 192 de
las 196 y justo en las otras cuatro.

**Lo que queda para el intérprete, dicho ya**: el parpadeo de una aventura de
Amstrad. En la CGA sólo se puede cambiar el fondo o el trío entero, no un color
del trío, así que parpadeará lo que se pueda --el fondo, o el trío entero
cuando las dos tintas caigan en tríos que existan-- y lo demás se quedará
quieto, con la limitación escrita cuando se haga.

Pruebas en `tests/test_cga.py`: dónde cae cada punto en `B800`, los bytes de
los puertos, una lámina de Spectrum en cuatro colores de la CGA, y el reparto
de plumas de una de Amstrad, uno a uno.

### La cabecera MZ, cargada por el DOS de verdad

`mz_exe` en `regac/media.py`. La cabecera son 28 bytes, pero la imagen tiene
que empezar en un párrafo de 16 bytes, porque el campo que dice dónde empieza
cuenta en párrafos; así que en el fichero van **32**: los 28 y cuatro ceros.
Sin tabla de reubicaciones. El DOS suma el segmento de carga a `CS` y a `SS`
sin que se lo pidan, y el resto de segmentos se calculan desde `CS` en
marcha.

Detrás de la imagen, la memoria que el programa quiere y el fichero no
lleva, y detrás de eso la pila, en un segmento suyo. El mínimo que se pide al
DOS es eso; el máximo, toda la que haya, que es lo que hacen los enlazadores.

La prueba, `tests/test_media_pc.py`, no se fía de haber leído bien el
formato: ensambla un programa que le pregunta al DOS dónde lo ha puesto y lo
escribe en un fichero. Pidiendo 3000 bytes de memoria, con una pila de 1 KB y
la entrada en `40h`, lo que contestó DOSBox-X:

| | salió | tenía que salir |
|---|---|---|
| `CS` | PSP + `10h` | el PSP son 256 bytes |
| `SS` − `CS` | 196 párrafos | 8 de imagen + 188 de los 3000 bytes |
| `SP` | `400h` | la pila entera |
| cima de la memoria | `9FFFh` | toda, que es lo pedido |
| lo leído con `DS` = `CS` | `REGAC` | lo que la imagen lleva |

La prueba tarda un segundo y medio, DOSBox-X incluido, y va en la puerta.
`tests/dosbox.py` es el arnés: ensamblar con NASM, escribir la
configuración, correr y esperar a que se vaya. Lo usará también lo que
venga.

### El intérprete de PC empieza por las láminas, y salen iguales

Como en las otras máquinas, lo primero es la construcción de prueba de
láminas: `x86/test_picture.asm` dibuja una tras otra todas las láminas de su
base de datos y, después de cada una, escribe los 16384 bytes de `B800` en un
fichero con su número --`P001C.BIN`, en hexadecimal--. La prueba,
`tests/test_graphics_pc.py`, ensambla con NASM, le pone la cabecera con
`mz_exe`, la corre en DOSBox-X y compara cada fichero con `cga_screen`, que
es la misma lámina de la referencia tal como la tendría la tarjeta.

**Lo que hay en `x86/`**, que sigue fichero a fichero a los de Z80 para que se
pueda comprobar que hace lo mismo:

| fichero | qué es | lo sigue |
|---|---|---|
| `database.asm` | las secciones, en el segmento de la base de datos por `ES` | `z80/common/database.asm` |
| `picture.asm` | el intérprete de órdenes de lámina | `z80/common/picture.asm` |
| `cga.asm` | filas, píxeles, paleta de cada lámina, tendido de un tramo | --de la CGA-- |
| `line.asm` | la recta de la ROM, con los extremos ordenados si es de Amstrad | `z80/next/draw.asm`, `amstrad.asm` |
| `shapes.asm` | rectángulo y elipse, con el medio píxel del Amstrad si toca | `z80/common/shapes.asm`, `z80/cpc/shapes.asm` |
| `draw.asm`, `fill.asm` | las reglas del Spectrum: la máscara y su relleno | `z80/next/draw.asm`, `fill.asm` |
| `amstrad.asm`, `amstrad_fill.asm` | las del Amstrad: la pluma leída de la pantalla | `z80/next/amstrad.asm`, `amstrad_fill.asm` |

Una construcción lleva unas reglas u otras, nunca las dos, según
`AMSTRAD_PICTURES`, igual que el Next.

**Las dos cosas que son de la CGA**:

- **El tendido de un tramo de relleno.** El patrón del Spectrum es de ocho
  puntos y va alineado con la x, así que un byte de pantalla, que son cuatro,
  lleva siempre la primera mitad del patrón --en una columna par de bytes-- o
  la segunda; las dos se calculan una vez por tramo y se escriben byte a
  byte, mezclando sólo los dos extremos. El damero del Amstrad es aún más
  simple: los cuatro puntos de un byte empiezan en columna par, así que todos
  los bytes del tramo son el mismo.
- **La pluma no se escribe como tal**: cada lámina reparte sus cuatro plumas
  entre los cuatro valores (ver «El `CgaDevice`, como el CPC»), y el relleno
  del Amstrad compara valores, que es lo mismo porque no hay dos plumas con
  el mismo valor. Y recorre el tramo como el del Spectrum recorre la máscara:
  un byte entero del valor de la semilla son cuatro puntos de un golpe.

**Lo que lleva cada lámina en la base de datos del PC**: seis bytes delante de
su longitud --ocho desde el parpadeo: ver «El intérprete de PC, entero»-- --el último byte de la configuración lo dice--: los de los puertos
`3D9h` y `3D8h`, y en cuatro bytes el valor de cada uno de los dieciséis
colores. Una lámina de Amstrad lleva ahí sus cuatro plumas **cuatro veces
seguidas**, de modo que el intérprete busca una tinta tal cual y sus dos bits
bajos eligen la pluma. `regac build -m pc` acepta ya las aventuras de Amstrad
--el PC está en `AMSTRAD_RULES`--, y la negativa de las demás máquinas dice
ahora «cpc, next and pc do».

**El `BORDER` de una lámina no hace nada en el PC.** En el modo de 320 por 200
el borde de la CGA es el fondo, un mismo registro para los dos: no puede tener
un color propio sin cambiar todos los puntos del valor cero de la lámina.

**Lo que sale:**

| | láminas | distintas |
|---|---:|---:|
| los trece dibujos de las pruebas del Next, con las reglas del Spectrum | 13 | 0 |
| los doce de las del CPC, con las del Amstrad | 12 | 0 |
| las ocho aventuras de Spectrum | 196 | 0 |
| las seis de Amstrad (con `REGAC_SLOW`, como en el Next) | 187 | 0 |

Y la prueba **se ha visto fallar**: tocando a mano la fase del patrón y el
desplazamiento de un punto en el Spectrum, y en el Amstrad la fase del damero,
el redondeo del medio píxel y el orden de los extremos, cada cambio lo pilla
su caso --la media tinta, 2591 puntos; el damero, 4661--.

`tests/dosbox.py` ensambla ahora con carpeta de `%include` y definiciones, y
corre a la velocidad que se le pida: las pruebas de corrección van a
`cycles=max`, porque sólo importa lo que sale. Las ocho aventuras de Spectrum
son una prueba cada una.

**Y van todas en un mismo trabajador**, el grupo `pc` de `conftest.py`. En el
primer lote en paralelo con ellas falló
`test_a_noise_is_a_hiss_and_not_a_note[next]` --el ruido del AY salió con
forma de nota--, que a solas pasó. Es una prueba que depende de cuánto tiempo
de máquina le toca, y hasta cuatro DOSBox-X a toda velocidad a la vez son
carga. **No está demostrado que fuera eso**; juntas en un trabajador no
cuestan nada y el lote siguiente salió entero en verde, en el mismo tiempo:
dieciocho minutos.

**Y el tiempo, que no es una medida.** La construcción apunta, por lámina, los
tics del reloj de la BIOS --18,2 por segundo-- entre pedirla y tenerla, y los
escribe en `TIMES.BIN`. Corrida a `cycles=fixed 315`, que es lo que DOSBox-X
llama un XT a 4,77 MHz, la peor de cada aventura, al lado de la del CPC con
las mismas reglas --la tabla de «Hecho: el CPC dibuja las aventuras de
Spectrum con las reglas del Spectrum»--:

| aventura | PC, DOSBox-X a 315 | CPC, medido | la lámina en el PC |
|---|---:|---:|---|
| Bangkok1 | 3,13 s | 3,2 s | #26 |
| Bangkok2 | **4,67 s** | 5,0 s | #28 |
| megacorp1 | 2,75 s | 2,8 s | #10 |
| megacorp2 | 3,41 s | 3,5 s | #291 |
| quijote1 | 2,86 s | 2,9 s | #15 |
| quijote2 | 3,57 s | 3,6 s | #15 |
| vajillas1 | 4,06 s | 4,2 s | #13 |
| vajillas2 | 3,46 s | 3,7 s | #14 |

Las 196 suman 339 segundos. Las 187 de las seis aventuras de Amstrad, con
sus reglas, van más holgadas: la peor, bangkok_fac #35, 2,69 s, y todas
suman 226. Todo dentro del tope de cuatro o cinco segundos, **pero DOSBox-X
no es exacto al ciclo** --lo dicho en «El paso dos» y en `tests/dosbox.py`:
sirve para saber si algo sale bien y no para cuánto tarda--, así que esto es
una aproximación. Las dos láminas de la estimación de arriba caen dentro de
su horquilla: quijote1 #8, 1,98 s contra 1,1 a 3,3; megacorp2 #29, 3,35 s
contra 1,3 a 3,8. Pero ninguna de las dos es la peor, y Bangkok2 #28 se va a
4,67. Que salga casi igual que el CPC, aventura a aventura, puede ser
casualidad de lo que DOSBox-X llama 315. Medirlo de verdad
pide 86Box o MartyPC, que no están instalados. Y 4,77 MHz es el mínimo y no
la máquina recomendada.

**Lo que seguía en el PC**, hecho en «El intérprete de PC, entero»: el resto
del intérprete, el parpadeo, `regac make` y NASM en el manual.

### El intérprete de PC, entero

Juega. `x86/` tiene ya todo lo de `z80/common/` --la base de datos, la
configuración, el desempaquetado de mensajes, el reparto de palabras entre
líneas, la máquina de condiciones con todos sus opcodes, el parser y el
turno--, cada fichero siguiendo al suyo rutina a rutina, y lo que es de la
máquina: la pantalla de texto, el reloj, el teclado, el altavoz y guardar.
`regac make` hace el `.EXE` con NASM --en `tools/` o en el PATH, como
sjasmplus-- y el proyecto de ejemplo lo pide: `[targets.pc]`.

**Tres decisiones, tomadas por el usuario antes de escribir nada:**

- **Al acabar la partida**, la puntuación se queda en pantalla, una tecla, y a
  DOS con la pantalla de texto como estaba. Las de 8 bits se quedan paradas;
  en un PC eso obligaría a reiniciar.
- **`SAVE` y `LOAD`**, un solo fichero junto al programa, con su nombre y
  `.SAV` --`MEGACORP.EXE` guarda en `MEGACORP.SAV`, lo corran desde donde lo
  corran--, sin preguntar nada, como el 6128 y el PCW. El nombre sale del
  propio DOS, que dice al final del entorno dónde está el programa; un DOS de
  antes del 3.0 no lo dice y guarda en `GAME.SAV`. Lo que se guarda son los
  743 bytes de siempre, en el mismo orden que en las demás.
- **El teclado, con las reglas de la ROM del Spectrum, como en todas**, y el
  carácter de cada tecla el que diga la distribución de DOS (`KEYB SP` y las
  demás). Para saber qué teclas están abajo se toma la interrupción del
  teclado: anota cada tecla que baja o sube, llama a la del BIOS como siempre,
  y saca de su búfer el carácter que ésta hizo. Las letras, en mayúsculas.

**Los segmentos, como quedó decidido**: el código en `CS`, los datos en un
segmento suyo detrás, la pila en el suyo --el de la cabecera--, y la base de
datos detrás de todo, **en bancos de 64 KB**, con el texto y las láminas en
ellos y lo demás residente, como en el 128, el 6128 o el Next. Pero en un PC
no hay que traer un banco: el `.EXE` entero está en memoria, así que cada
sección tiene su propio segmento, calculado al arrancar, y leerla es cargar
`ES`. Una sección no puede pasar de 65520 bytes y `regac build` lo dice; el
relleno detrás del último banco no viaja. Sin enlazador: NASM, con secciones
`.text`, `.data` y `.database` una detrás de otra, cada una en un párrafo, y
el párrafo de cada una calculado con etiquetas de fin de sección.

**El reloj** es el contador 0 del temporizador, que cuenta igual en un XT a
4,77 MHz que en un Pentium. Se deja dando al BIOS sus 18,2 tics de siempre y
sólo se cambia al modo que cuenta de uno en uno, de modo que la diferencia
entre dos lecturas es el tiempo entre ellas; al salir se deja como estaba. De
ahí salen los **fotogramas de 1/50 s** que cuentan todas las máquinas --la
espera de `HOLD`, la repetición de una tecla, el parpadeo-- y los medios
periodos del altavoz.

**El altavoz** es el motor del Spectrum 48 --un bit, la misma tabla, el tono
que anda--, con las esperas contadas en ese reloj y no en ciclos: medio
periodo de tono p son p·60/11 de sus cuentas, que es lo que dura en un
Spectrum. El cuarto byte de un ruido se lee y no se usa, como allí. Hace clic
en cada tecla, como el original.

**El texto, como el del CPC**: cuarenta columnas, nueve filas bajo la lámina,
`TEXT` y `PICT` igual. La tinta y el papel van en el valor al que su color
llega en la lámina que está en pantalla --el papel, el negro de una aventura
de Spectrum o la pluma cero de una de Amstrad--, así que se recalculan cada
vez que una lámina trae los suyos. Antes de la primera, la paleta y los
valores son los de la referencia para una pantalla sin lámina: cian, magenta
y blanco sobre negro.

~~**Lo que eso deja, dicho**: el texto ya escrito no cambia de valor cuando
cambia la lámina, así que si en la nueva el negro cae en otro valor --en 11
de las 196 láminas de Spectrum no cae en el cero--, el papel del texto viejo
y el del nuevo se ven distintos hasta que el viejo se va. En el CPC no pasa
porque el papel es siempre la pluma cero.~~ **Era un fallo y no una
consecuencia**, y era peor de lo que decía: ver «El papel, siempre en el
fondo», más abajo.

**El parpadeo de las aventuras de Amstrad, lo que se pueda.** Cada lámina
lleva ahora ocho bytes: los seis de antes y la segunda paleta, la que un
color que parpadea enseña la mitad del tiempo, elegida por
`cga_amstrad_flash`. La CGA sólo puede cambiar el fondo o el trío entero, y
la regla es que **una pluma que no parpadea no se mueve**: la segunda paleta
es la que acerca más las plumas que parpadean a su otra tinta sin cambiar el
color de ninguna de las quietas. Mientras se espera una tecla, cada diez
fotogramas, se alternan, al empezar el retrazo vertical como hace el
firmware del Amstrad. Contado sobre las seis aventuras de Amstrad: **parpadean
11 láminas de 187 en el Amstrad, y en el PC se ve el parpadeo en 2**
--bangkok_fac #9 y bangkok_exp #27--. En las otras nueve la pluma que parpadea
comparte el trío con plumas quietas, y la lámina se queda en su primera
paleta.

**Las pruebas**, que como en las otras máquinas juegan de verdad:

| | qué |
|---|---|
| `test_game_pc.py` | MegaCorp: la clave, el inventario, una palabra que no conoce y una que sí, `FIN`; y el texto en los valores de la lámina |
| `test_save_pc.py` | una partida guardada vuelve en otra, 743 bytes con la sala delante; un `LOAD` sin fichero no toca nada |
| `test_textmode_pc.py` | un mensaje largo no pasa de sus nueve filas hasta `TEXT`; con `TEXT` una sala no dibuja |
| `test_keyboard_pc.py` | teclas solapadas, dos a la vez, una mantenida (a los 35 fotogramas y luego cada 5), el rebote, y `HOLD` de 2 s |
| `test_sound_pc.py` | el clic y los cinco ruidos duran lo que en un Spectrum |
| `test_inks_pc.py` | la paleta de cada lámina y la que parpadea, y los valores del texto en aventuras de Amstrad y de Spectrum |
| `test_example.py` | el faro, jugado de principio a fin también en el PC |

Se juega **tecleando por el teclado de la máquina**: DOSBox-X tiene
`AUTOTYPE`, que pulsa y suelta cada tecla por la interrupción de verdad. Lo
que el juego escribe va además, en la construcción de pruebas
(`-DTRANSCRIPT`), a `TRANSCR.TXT` según sale, confirmado en el disco carácter
a carácter para que se pueda leer aunque se cuelgue; la tarjeta se vuelca a
un fichero cada vez que pide una orden y al acabar, y cada paleta que se pone
a `PALETTE.BIN`, porque los puertos no se pueden leer. Como `AUTOTYPE` sólo
pulsa y suelta, las reglas del teclado se prueban con `x86/test_keys.asm`,
que mueve las teclas desde un guion fotograma a fotograma por debajo de las
mismas `next_key` y `wait_or_key`. Se ha visto fallar: con la demora de
repetición a 30 fotogramas en vez de 35, y con el medio periodo del altavoz a
57/11 en vez de 60/11.

**Dos cosas de DOSBox-X que costaron**: con `AUTOTYPE` se estrella siempre al
salir, después de que el programa ha escrito y cerrado sus ficheros, así que
en esas corridas manda lo que salió y no cómo acabó; y el `dosbox-x` del PATH
es un lanzador de scoop, y matarlo no mata al emulador, así que una corrida
que se pasa de tiempo se corta con `taskkill /T`, el árbol entero.

### El papel, siempre en el fondo, como en el Amstrad

**Lo vio el usuario en la partida de Vajillas**: colores que se salían del
dibujo. En el desierto de Vajillas 1 --la lámina 11-- el cielo azul era el
fondo, el valor 0, y el negro, que es la pluma 0 y el papel del texto, había
ido a parar al valor 1, que en esa paleta es verde claro. Así el borde y los
márgenes que nadie escribe salían azules, y el texto que había subido por
toda la pantalla en la casa --una sala sin lámina, que le da al texto la
pantalla entera-- salía verde al lado de la lámina.

**Era un fallo de haber hecho el PC distinto del CPC en esto.** En el CPC el
papel es siempre la pluma 0 y el borde la lleva también: `cpc_picture_colours`
pone en la pluma 0 la tinta a la que llega el papel. En la CGA el valor 0 es a
la vez el fondo, el borde y todo lo que hay fuera de la lámina, así que ahí es
donde tiene que ir el papel, y yo dejé que el reparto lo mandara a cualquier
sitio con tal de parecerse más dentro de la lámina. Lo que tenía apuntado
como consecuencia --«11 de las 196 láminas de Spectrum»-- era este mismo
fallo, y en las aventuras de Amstrad, que se ven mucho menos, pasaba en 10 de
las 187.

**Arreglado con la regla del CPC**: en una aventura de Amstrad la pluma 0 va
siempre al valor 0 y las otras tres se reparten entre el trío; en una de
Spectrum sólo se elige entre las paletas cuyo fondo es, de sus cuatro
colores, el más cercano al papel del texto. Así el borde, los márgenes y el
papel son siempre el mismo color. Lo que cuesta, contado igual antes y
después sobre las 196 láminas de Spectrum:

| colores perdidos | antes | ahora |
|---|---:|---:|
| ninguno | 60 | 61 |
| uno | 99 | 95 |
| dos | 30 | 33 |
| tres | 7 | 7 |

Y el fondo negro en 181 en vez de 176. (Esta cuenta mira si dos colores
usados comparten valor; la de «El `CgaDevice`, como el CPC» contaba de otra
manera, y por eso sus cifras de antes no son éstas.) El parpadeo no cambia:
se sigue viendo en 2 de las 11.

Pruebas: `test_the_paper_is_the_background_in_every_picture` en
`test_cga.py`, con una lámina de Spectrum y una de Amstrad donde la regla
antigua ponía el papel fuera del fondo --comprobado con ella--; y la de los
repartos, que fijaba el reparto viejo (el blanco al fondo y el negro a un
valor del trío), dice ahora el nuevo.

### La letra de las aventuras de Amstrad, que no estaba

Al mirar la pantalla de esa misma partida salió otra cosa, **y no era del
PC**: el texto no se veía. Las seis aventuras de Amstrad salían de `deGAC`
con la letra vacía --256 ceros--, porque el GAC de Amstrad no guarda letra:
escribía con la del firmware, que está en la ROM de la máquina. Construidas
para el CPC, el Next o el PC, sus 85 glifos no tenían un solo punto, así que
**en las tres máquinas salían mudas** desde que se abrieron a ellas. `regac
check` lo avisaba; ninguna prueba lo veía, porque las del CPC y el Next con
aventuras de Amstrad usan aventuras hechas a mano con letra propia y las de
láminas no miran el texto.

**Primero se hizo con la letra del firmware, sacada de una ROM del CPC en
`tools/`**, y se quitó enseguida: obligaba al que use `regac` a buscarse una
ROM que no es nuestra y dejarla ahí, que es lo contrario de fácil. Lo que
quedó, **decidido por el usuario: Modern DOS 8x8**, la letra de la CGA de
Jayvee Enaguas, versión 20190101.02, **de dominio público (CC0 1.0)**. Se buscó
una libre de verdad, porque la letra va dentro de cada aventura que se
construya y una con atribución obligatoria o «compartir igual» le pasaría
obligaciones: la CGA del Oldschool PC Font Pack de VileR, y sus copias en
pcface y font-vault, son CC BY-SA 4.0 y se descartaron. font8x8 de Daniel
Hepper era la otra de dominio público. Las dos vienen de la letra de las ROM
de IBM, cuyo estado legal está discutido --VileR sostiene que un mapa de
puntos no tiene derechos; en DOSBox dicen que la de IBM los tiene todavía--;
las dos se declaran libres y ninguna es invención propia, y eso se dijo antes
de elegir.

**Cómo está**: del repositorio del autor, que ya no existe en NotABug, queda
el espejo archivado `notpeter/ttf-moderndos` en GitHub; de ahí se bajaron el
fuente de FontForge, `ModernDOS8x8.sfd`, y la licencia, a `tools/moderndos/`,
fuera del repositorio. En el repositorio sólo están las 96 letras, del
espacio al final de ASCII, en `regac/moderndos8x8.bin`, y el guion que las
saca del fuente, `regac/moderndos.py`: cada punto del fuente es un cuadrado de
100 unidades, y un punto se enciende si su centro cae dentro de los trazos,
contando cruces para que el hueco de la A siga siendo hueco. Las mayúsculas
dejan libre la fila de abajo, como pide `regac` para bajar una fila las que
llevan tilde; la única que no es la Q, por su rabo, y ninguna Q lleva tilde.

`deGAC` se la pone **a toda aventura que no traiga letra propia**, y lo dice:
las de Amstrad siempre, y una de Spectrum que escribiera con la letra de la
ROM --ninguna de las ocho--. El C64, aparcado, no se toca.

Pruebas: `test_an_amstrad_adventure_gets_letters_it_can_print_with` en
`test_disk.py`, que saca Bangkok del disco y mira que su letra es ésta byte a
byte; `test_moderndos.py`, con las 96, la A con su hueco, las mayúsculas y, si
está el fuente en `tools/`, que el volcado es lo que el fuente dibuja; y la
partida de abajo, que mira que el texto se vea.

### La partida de Amstrad, entera en el PC

`test_an_adventure_off_an_amstrad_is_played_through_on_a_pc`, en
`test_game_pc.py`: La guerra de las vajillas, primera parte, sacada de su
disco de `juegos/` y jugada en DOSBox-X. Del desierto a la casa, que no tiene
lámina; coger la lata; el inventario; de vuelta al desierto, que sí la tiene;
una palabra que no conoce; los puntos; y `QUIT`, que pregunta y acaba con la
puntuación. Se comprueba el texto de cada paso, que la puntuación final es la
que dijo `PUNTOS`, que la última lámina en pantalla es punto por punto la de
la referencia con las reglas del Amstrad, y que el texto se ve: la pluma 1
sobre la 0, y la 0 en el fondo. Corre en el lote normal cuando están los
discos en `juegos/`: descompilar las seis tarda menos de dos segundos.

Y una carrera del arnés que salió al hacerla: la tecla que devuelve a DOS
llegaba mientras el juego escribía la puntuación y se perdía. Ahora va detrás
de un enter con su pausa, en todas las partidas del PC.

### Las teclas del PC que se perdían, y la que cambiaba de letra

Al pasar el lote con todo esto, las partidas del PC fallaban de vez en cuando:
una vez una `N` salió como `O`; otra, en `SALIR` el enter no llegó y la `X`
de después se pegó a la palabra. **Eran dos fallos de la interrupción del
teclado, y no del arnés** --lo primero que se sospechó fue la transcripción,
que escribía en disco a cada letra, y se descartó midiendo--. Un registro de
cada código que llegaba a la interrupción mostró que el enter entraba entero,
al bajar y al subir, y aun así `next_key` no lo daba.

1. **Una pulsación corta se perdía.** Una tecla que bajaba y subía entera
   mientras el intérprete no miraba --dibujando, o haciendo el clic de la
   anterior-- quedaba anotada como subida y nadie la veía. `AUTOTYPE` pulsa
   muy corto y por eso le tocaba a veces; una persona que teclee rápido,
   también. Ahora una tecla que baja queda además **pulsada** hasta que la
   siguiente mirada al teclado la ve, aunque ya haya subido: lo que el PC
   dijo que se pulsó se teclea una vez. En las máquinas de 8 bits no se puede
   hacer, porque no hay interrupción que diga que una tecla bajó; aquí sí.
2. **El carácter se apuntaba a la tecla equivocada.** Se guardaba «qué tecla
   espera su carácter» en una sola variable, y la interrupción del BIOS deja
   entrar otras antes de acabar: una segunda tecla que entraba ahí se llevaba
   el carácter de la primera. Ahora cada entrada del búfer del BIOS, que lleva
   el código de su tecla en el byte alto, va a esa tecla; el enter y la barra
   grises, que el BIOS marca con E0, a las blancas; y el búfer se vacía con
   las interrupciones cerradas.

Repetida seis veces seguidas a solas la prueba que fallaba una de cada dos, y
el lote entero de las del PC, en verde.

**Pero la conclusión estaba mal**: los dos arreglos son de verdad y se
quedan, pero los cuelgues no venían de ahí. Siguieron saliendo, y lo que eran
está en «Los cuelgues eran de `AUTOTYPE`», más abajo.

Y el tiempo que se le da a una partida del PC ya no es fijo: sale de lo que
se teclea --un cuarto de segundo por tecla, medio por pausa-- más un margen.
Los treinta segundos de siempre eran justo lo que tarda la de MegaCorp a
solas, y en el lote en paralelo se pasaba.

### Una lámina borra sus filas enteras, en el CPC y en el PC

En la pantalla del desierto de Vajillas quedaban a los lados de la lámina
trozos de texto --«ESTA», «FREN», «NE.»--: la casa no tiene lámina y le da al
texto la pantalla entera, el texto sube por las filas de la lámina de borde a
borde, y la lámina siguiente sólo borraba sus 256 puntos. **El CPC hacía lo
mismo**: su `gfx_clear` borraba 64 bytes de cada fila. En el Spectrum, el Next
y el MSX la lámina ocupa todo el ancho y no hay márgenes.

**Decidido por el usuario: borrar los márgenes en los dos.** Ahora dibujar una
lámina deja a cero sus 128 filas enteras, los 80 bytes: `wipe_picture_rows`
en `z80/cpc/pixels.asm`, que usan las dos maneras de dibujar del CPC, y en
`x86/cga.asm`, que usan las dos del PC. El cero es el papel en los dos --la
pluma 0 en el CPC; el valor 0 en la CGA desde que el papel va siempre al
fondo--, así que lo que queda es la lámina y nada alrededor. Pasa también en
una sala a oscuras, que borra la lámina igual.

Cuesta **26 bytes** al CPC. En el 464, con las ocho aventuras: siguen cabiendo
las mismas cinco, Bangkok2 pasa de 614 a 588 bytes de holgura y la más justa
es ahora megacorp1, con 535; las otras tres ya iban del revés, con el
intérprete bajo `$4000`.

Pruebas: `test_a_picture_clears_what_the_text_left_either_side_of_it`, en
`test_textmode_cpc.py` y en `test_textmode_pc.py`: con `TEXT` un mensaje largo
llena de texto las filas de la lámina de borde a borde, y una lámina dibujada
después deja vacíos los ocho bytes de cada lado de cada fila. Se han visto
fallar las dos, volviendo a borrar sólo el ancho de la lámina.

### Los cuelgues eran de `AUTOTYPE`, y las partidas ya no lo usan

Con los márgenes, el lote en paralelo siguió sin salir verde: alguna partida
del PC se quedaba parada, la última letra en pantalla y ninguna tecla más, y
a solas pasaban. Salió también con las pruebas una detrás de otra, una vez
cada diez o veinte. **Lo que costó saberlo, para no repetirlo**:

- Cada diagnóstico que escribía en disco desde el camino del teclado --un
  registro de códigos, marcas a la entrada de `next_key`, latidos-- hacía que
  el fallo dejara de salir: cambia los tiempos. Lo que funcionó fue mirar
  **desde la interrupción del reloj**, que va aparte de todo lo que hace el
  juego: cada 5 s apuntaba dónde estaba el programa y el estado de las cosas.
- Estaba vivo, dando vueltas en `next_key`; la tecla que no llegaba estaba
  abajo para él y la repetía --«LARGOOOOOO»--, que es la regla de la ROM.
- La interrupción del teclado había entrado nueve veces, las nueve con su
  código, y la última era una tecla al bajar: **nunca llegó su subida ni
  nada de después**. El controlador de interrupciones, en reposo: nada en
  servicio, nada pedido, el teclado sin enmascarar; el de teclado, sin nada
  que dar. La máquina esperaba teclas que nadie le mandaba.
- Y en el código de DOSBox-X, `AUTOTYPE` teclea **desde otro hilo del
  ordenador, sin ningún cerrojo** con el que emula, cada tecla sujeta 50 ms
  de reloj real; el propio código lo avisa: «not necessarily reentrant and can
  cause screw ups when called from multiple threads». Falla de vez en cuando
  y más con la máquina cargada, que es lo que se veía.

Por el camino se sospechó de dos cosas que no eran, y se descartaron: el
puerto `61h` del clic, que en un XT tiene bits del teclado --DOSBox-X sólo
atiende los dos del altavoz--; y leer el puerto `60h` antes que el BIOS, que
en DOSBox-X trae el código siguiente 0,3 ms después --se llegó a enganchar la
INT 15h, función 4Fh, para no leerlo, y se deshizo: no era la causa, y su
camino para los primeros XT habría sido código sin ejecutar nunca--.

**Decidido por el usuario: las partidas se teclean desde un guion, y una con
el teclado de verdad.** El guion es el de las reglas del teclado, ahora en
`x86/script.asm` y compartido: una construcción de juego con `SCRIPTED_KEYS`
no toma la INT 9 y mueve las teclas fotograma a fotograma desde `KEYS.BIN`.
Los fotogramas sólo corren mientras el juego espera una tecla, así que una
tecla llega cuando el juego pregunta, siempre igual, sin pausas a ojo, y
mucho antes que tecleando con pausas. El camino de
verdad --la INT 9, el BIOS, la distribución de DOS-- lo sigue probando
`test_the_machines_own_keyboard_gets_the_keys_there`, con `AUTOTYPE`: la
construcción cuenta cada código que entra por la INT 9 y lo apunta una vez
por segundo, desde la interrupción del reloj, en `WATCH.BIN`, de modo que si
falla dice si fue DOSBox-X el que dejó de teclear --entraron menos códigos de
los que se le dieron-- o el juego el que dejó de contestar. Ésa puede fallar
de vez en cuando, y cuando lo haga lo dirá.

**Y las pruebas del PC ya no abren ventanas ni hacen ruido**: DOSBox-X
arranca con el vídeo `dummy` de SDL y `nosound`. Salió porque una prueba de
esfuerzo abrió más de un centenar de ventanas en el escritorio del usuario,
que no debió lanzarse sin decírselo.

### Dos pruebas que dependían de la carga

- **Los ruidos del PC duraban de más con la máquina lenta**, hasta un 5 %. Era
  del intérprete: cada medio periodo esperaba «tanto desde ahora», y lo que
  cada espera se pasaba se sumaba a la siguiente; en un XT de verdad, que
  mira el reloj despacio, pasaría igual. Ahora cada cambio del altavoz espera
  hasta una hora contada desde el principio de la nota (`beat_until`, en
  `x86/timer.asm`), y lo que una espera se pasa no se acumula: medidos, el
  clic y los cinco ruidos a menos de un 0,25 % de lo que deben, y la prueba
  pide ahora un 1 % por arriba y por abajo, donde antes admitía un 5 % de más.
- **El parpadeo del Next** esperaba 10 s fijos y miraba doce veces en dos
  segundos; con carga la primera lámina aún se estaba dibujando y todas las
  miradas veían el mismo color. Ahora mira hasta haber visto los dos, con un
  tope, y exige lo mismo que antes: los dos colores y nada más.

Y una que se vio y no es de esto: en el lote de serie,
`test_keyboard_pcw.py::test_keys_typed_over_each_other_all_arrive` dio `OL`
en vez de `SOL` una vez --la primera tecla de las solapadas, perdida--. No se
ha tocado nada del PCW ni de `z80/common/`, y a solas pasó tres de tres. Queda
apuntada: es de las que dependen del ritmo con que ZEsarUX recibe las teclas,
como las del teclado de las otras máquinas, y si vuelve hay que mirarla.

Y otra del mismo pie, en el lote en paralelo después de `DO`:
`test_textmode_cpc.py::test_a_picture_clears_what_the_text_left_either_side_of_it`
vio las filas de la lámina vacías después de `TEXTO`, como si el texto no
hubiera llegado. A solas pasó tres de tres, y el CPC se construye sin `PROCS`.
Lo que tenía era una espera fija, `settle` segundos después de teclear, sin el
`emulator.longer()` con que crecen las demás cuando hay cuatro emuladores a la
vez; ahora lo lleva.

## El Next guarda en la tarjeta

**Decidido por el usuario**: `SAVE` y `LOAD` del Next van a un fichero de la
tarjeta, y la cinta se quita; el fichero se llama como el proyecto, con
`.SAV` --`faro.nex` guarda en `FARO.SAV`--, como en el PC. No se pregunta
nombre, como en el 6128, el PCW y el PC. `regac make` lo pasa al ensamblador
como `SAVE_NAME`, en 8.3 (`dos_name`); una construcción a la que nadie se lo
dice guarda en `GAME.SAV`. El nombre no lleva carpeta, así que va a la carpeta
en la que está el sistema, que es la del `.nex` cuando se arranca desde el
navegador.

Un `.nex` siempre lo arranca NextZXOS, y NextZXOS contesta las llamadas de
esxDOS: `RST $08` y un byte detrás (`F_OPEN`, `F_READ`, `F_WRITE`,
`F_CLOSE`). Está en `z80/next/save.asm`, que sustituye a `tape.asm`. Dos
cosas de esta máquina:

- **El sistema no contesta sin la ROM en `$0000`**, y ahí está la ventana de
  la base de datos. Se trae la ROM mientras duran las llamadas y se devuelve
  la ventana, como hacía la cinta. Quitándolo, la máquina se pierde en `SAVE`:
  visto con NextZXOS de verdad.
- **Una carga se lee primero aparte**, en la memoria libre de `$4000`, y sólo
  se copia encima de la partida cuando ha llegado entera: un fichero que no
  está, o más corto que una partida, deja la partida como estaba.

Se sospechó una tercera y **no era**: que el sistema, al volver, paginara los
16 K de arriba como un 128 a partir de sus variables --que el `.nex` pone a
cero, porque lleva el banco 5 entero--, y ahí está la parte de layer 2 que se
dibuja. Se guardaron y repusieron los dos registros; quitándolo todo sigue
igual con NextZXOS, así que se quitó.

Las pruebas, en `test_save_next.py`, juegan Vajillas --`NORTE` lleva de la 1
a la 4 y `SUR` de vuelta-- de dos maneras:

- Con el sustituto que ZEsarUX pone al abrir un `.nex`, que contesta las
  llamadas desde la carpeta del fichero. Rápido, y ahí se prueban los fallos:
  sin fichero, `LOAD` no cambia nada; con un fichero de diez bytes, tampoco;
  `SAVE` lo rehace con la partida dentro, y un `LOAD` después vuelve a ella.
  Se ha visto fallar leyendo directamente sobre la partida: acaba en la sala 0.
- Con **NextZXOS de verdad**, arrancado de la imagen `tbblue.mmc` que trae
  ZEsarUX, copiada: se pone en ella el `.nex` en `/games`, un `autoexec.bas`
  que hace `.cd /games` y `.nexload vajillas.nex`, que es lo que hace el
  navegador, y un `config.ini` con el modo de vídeo elegido, porque tal como
  viene el primer arranque saca una carta de ajuste y espera un Enter. Después
  se lee la tarjeta desde fuera (`tests/fat16.py`) y `/games/VAJILLAS.SAV`
  tiene 743 bytes, empezando por la sala. Se ha visto fallar sin la ROM.

`test_example` mira además que el `.nex` que hace `make` lleve `FARO.SAV`.

## Lo que viene, en cola

Pedido por el usuario el 2026-09-25, después de la 0.1.0. En este orden, y
cada ampliación del lenguaje se concreta con él antes de hacerla, porque
cambia lo que hacen las máquinas:

1. ~~**El visor de láminas**, `regac draw`.~~ Hecho: ver «El visor de
   láminas», abajo.
2. ~~**`DO n`**: una tabla de condiciones con número, llamada desde cualquier
   condición, para no copiar lo repetido en cada sala.~~ Hecho: ver «`DO` y
   `/PROC`», abajo.
3. ~~**Huecos en los mensajes**: un marcador que escriba dentro del texto el
   nombre de un objeto o lo que vale un contador, como ya hace `\ink` con el
   color.~~ Hecho: ver «Los huecos del texto», abajo.
4. ~~**Utilidades para quien escribe**: `regac map` (el mapa de salas y
   salidas), `regac lint` (salas a las que no se llega, objetos que no se
   pueden coger, palabras y mensajes que no usa nadie), `regac play` con un
   guion que dice si la aventura se gana, y el resaltado de sintaxis de
   `.gac` para VS Code.~~ Hecho: ver «Las utilidades para quien escribe»,
   abajo.
5. ~~**La distribución**: una orden `regac` instalable (`[project.scripts]`,
   que `pyproject.toml` no tiene), CI en GitHub Actions con las pruebas que no
   piden emulador, y el faro construido para las nueve máquinas adjunto a la
   release.~~ Hecho: ver «La distribución», abajo.

Y dos cosas vistas por el camino, sin hacer:

- ~~**`.if pc` no existe.** `MACHINE_LABELS`, en `regac/srcparse.py`, no tiene
  el PC: un fuente que lo nombra da «there is no machine called 'pc'», y la
  construcción del PC lee el fuente sin etiqueta ninguna, así que de un `.if`
  sólo le llega el `.else`. Añadirlo no cambia ningún fuente que hoy se lea,
  porque hoy nombrarlo es un error; pero es cosa de decidir.~~ **Decidido por
  el usuario, y hecho**: `pc` es una etiqueta suelta, como `next`. Prueba en
  `test_conditional.py`.
- ~~**`doc/gac.md` dice «ocho máquinas»** en sus secciones 8 y 10, y son
  nueve.~~ Corregido.

## `DO` y `/PROC`

**Decidido por el usuario**, las cuatro cosas:

- Las tablas se escriben en un bloque propio, `/PROC #n`, y no se toman de
  las salas.
- Lo que acaba el turno dentro --`WAIT`, `OKAY`, `EXIT`, una negativa de
  `GET`-- lo acaba también fuera: la tabla que hizo `DO` no sigue. Lo que sale
  cierto dentro cuenta como entendido.

Y lo que se eligió al hacerlo, dicho en `gac.md`: la pila de la tabla de fuera
se conserva, `DO` de una tabla que no hay no hace nada (y `check` lo avisa), y
se puede anidar hasta ocho de hondo, como `CALL` en las láminas; más allá no
hace nada. Es el opcode `$43`.

**En la base de datos no cambia nada para quien no lo usa.** Las tablas van
en la lista de las condiciones de cada sala, con el número y el bit 15
puesto: una sala es una constante del bytecode, de quince bits, así que
ninguna sala da con una, y la lista sigue acabando en la sala cero. El
decompilador las separa por ese bit.

**En el Z80** (`z80/common/`) la búsqueda de la tabla de una sala pasa a ser
`keyed_table`, con la clave en BC, y `local_table` entra en ella con la sala.
La pila de la máquina virtual tiene ahora una base, `vm_stack_base`: vacía es
llegar a ella, y `DO` la sube a donde estaba la pila antes de correr la otra
tabla y la baja al volver. Un `WAIT` hace `ret` a quien llamó a la tabla, que
es `op_do`; y como todo lo que acaba el turno pone `vm_done` antes --se miró
uno por uno: `op_okay`, `op_wait` y `end_turn`, que usan `GET`, `DROP`, `BRIN`
y `FIND`--, `op_do` sabe si seguir o volver él también. Sólo viaja con
`-DPROCS`, que `regac make` pone cuando alguna tabla tiene `DO`: el 464 cuenta
los bytes, y una aventura que no lo usa sale como antes. **En el PC**
(`x86/`) es lo mismo en 8086, y va siempre.

**En `runGAC.py`** va también, y al hacerlo salió un fallo que ya estaba: pedía
exactamente las claves de una aventura decompilada y **rechazaba el faro**,
que trae `sounds` --`start_adventure` daba `False`--, cuando el manual pone
justo `python runGAC.py faro.json` de ejemplo. Ahora admite las que un fuente
puede traer de más: `charset`, `gfx_inks`, `ink`, `procs`, `sounds` y `width`.

Pruebas en `tests/test_proc.py`: el fuente y su vuelta, el binario, `check`, y
**la misma aventura jugada en Python, en el Spectrum y en el PC**, que tiene
que decir lo mismo en los tres: que vuelve y sigue, que un `WAIT` dentro corta
la tabla de fuera sin que salga «no puedes», una tabla sin nada cierto, una
que se llama a sí misma y sale ocho veces exactas, un `DO` a una tabla que no
hay, y la pila conservada. Se han visto fallar las del Z80 quitando el `ret`
de después del `vm_done` y quitando la subida de la base, y la del PC quitando
el suyo.

## Las utilidades para quien escribe

- **`regac map`** (`regac/mapper.py`): **decidido por el usuario**, SVG con la
  brújula, sin depender de nada instalado. Las direcciones se leen en el
  vocabulario, en castellano y en inglés; `NO` sólo es noroeste al lado de
  `NOROESTE`, porque suelto es más fácil que sea un no. Se coloca desde la
  sala de salida, cada sala un paso más allá en la dirección por la que se
  llega, y si está ocupado más lejos en la misma línea; una sala a la que sólo
  se llega de vuelta va donde su salida dice. Lo que no alcanza ninguna
  salida, aparte a la derecha. Pasado por las ocho aventuras y el faro: todas
  sus salas colocadas --de 5 a 66-- y el SVG bien formado. Y visto, el del
  faro y el de MegaCorp, pasados a PNG con SDL, que dibuja cajas y líneas
  pero no texto ni puntas de flecha: eso no lo ha visto aquí nadie.
- **`regac lint`** (`regac/lint.py`): lo que está y nada usa. Un objeto que un
  `SWAP` o un `TO` a la mano pueden traer no se da por imposible de coger: era
  el candil encendido del faro. Donde un número se calcula al jugar no se
  adivina: se dice que no se ha mirado.
- **`regac play`** (`regac/play.py`): juega un fichero de órdenes con
  `runGAC.py`. La solución del faro está en `ejemplo/solucion.txt`.
- **`editors/vscode/`**: la extensión de VS Code, con la gramática hecha por
  `grammar.py` a partir de `regac/opcodes.py`; `test_editor.py` dice cuándo la
  del repositorio no se volvió a hacer. **No se ha visto en un VS Code**: lo
  probado es que cada patrón compila y reconoce lo que debe.

**Lo que encontraron al estrenarse**, que ya estaba:

- **El saludo del faro no sale nunca.** El mensaje 10, `SALUDO` --«EL FARO DE
  SANTA BÁRBARA -- una aventura de ejemplo. Escribe...»--, está escrito desde
  el primer día y nada lo imprime: el faro no tiene tabla `/HIGH`. Lo dijo
  `lint`. ~~**Sin tocar**: cambia cómo empieza el ejemplo, y es del usuario.~~
  **Decidido por el usuario, y hecho**: el faro tiene ahora una tabla `/HIGH`
  que lo dice una vez, debajo de la primera sala, con una bandera y no
  preguntando si el turno es el cero, porque la cuenta da la vuelta a los 256.
  Lleva un `LF` delante: sin él salía pegado a la lista de objetos, en el
  Spectrum y en Python.

  **Y al añadirlo salió otro, peor: el enigma del faro no lo era.** Guardaba
  la puerta en la bandera 1 y la lente en la 2, que son del intérprete --la 1
  dice que el sitio tiene luz, y está puesta desde el principio--, así que
  `SET? PUERTA_ABIERTA` era cierto antes de abrir nada: `NORTE`, `NORTE` sin
  la llave llevaba al zaguán. La solución no lo notaba porque abre la puerta
  antes de pasar. Las banderas del faro van ahora de la 4 en adelante, dicho
  en el fuente, y `test_play.py` pide la llave y el saludo una sola vez; la
  de la puerta se ha visto fallar con la bandera en el 1.
- **En `runGAC.py`, un `EXIT` en la tabla de una sala no acababa la
  partida**: la tabla baja corría después y devolvía `finished` a falso. El
  faro gana con un `EXIT` en su última sala y seguía preguntando. En las
  máquinas `EXIT` pone `vm_done` y las tablas siguientes no corren; ahora
  aquí tampoco. Lo encontró `play`.
- **Y la puntuación se caía** en una aventura sin los mensajes 249, 250 y 255,
  que el faro no tiene. En las máquinas un mensaje que no hay no escribe nada
  y los números salen igual; ahora aquí también.

## El editor de láminas

La fase dos de lo propuesto después de la 0.1.0. **Decidido por el usuario**:
es el mismo `regac draw`, no otra orden; una orden nueva va detrás de la del
cursor; y los puntos se arrastran, con los números de la línea escritos otra
vez y un nombre de `.def` que hubiera en ellos pasado a número.

- **Lo que se dibuja se escribe en el fuente en el acto** y el fuente se lee
  otra vez: la ventana enseña lo que el fuente dice. La escritura está en
  `regac/gfxedit.py`, sin ventana: una línea entra, sale o se reescribe, con
  la sangría de las de al lado, el comentario del final de la línea y los
  finales de línea que tuviera el fichero.
- **Para saber qué línea es cada orden**, el analizador guarda ahora de dónde
  sale cada una (`parse_with_places`), con lo que ya guardaba para los errores
  dentro de un `.include`.
- **No escribe donde no puede estar seguro de qué**: una lámina de otro
  fichero, un bloque con `.if` --una línea metida ahí sería de unas máquinas y
  no de otras sin que nadie lo dijera--, o un JSON.
- **Lo nuevo pertenece a la lámina que se mira**: con el cursor dentro de una
  que ella llama con `CALL`, va detrás del `CALL`. Sólo se arrastran y se
  quitan las órdenes propias.
- Ctrl+Z deshace, y no deshace encima de un cambio que alguien haya hecho en
  el fuente después: lo dice y se para.

Pruebas en `tests/test_gfxedit.py`: la escritura, los ficheros en los que no
escribe, cada herramienta en el visor sin ventana, arrastrar, quitar, deshacer
y la ventana entera con el ratón. Visto en una captura, con un rectángulo a
medio dibujar. **Sin ver en una pantalla de verdad**: todo se ha probado con
el controlador de vídeo `dummy` de SDL.

Lo que quedaba propuesto de la herramienta: ~~el calco sobre una imagen de
fondo~~ (hecho: ver abajo), ~~los avisos mientras se dibuja --fugas de un
relleno, bytes, tiempo contra el tope de 4-5 s--~~ (hechos: ver abajo) e
importar SVG.

### El calco

`regac draw fuente.gac 12 --trace boceto.png`, o `--trace bocetos/`.
**Decidido por el usuario**: la imagen se escala **sin deformarse**, tan
grande como quepa, y centrada; y vale una imagen para todas las láminas o una
carpeta con una a cada una, por su número (`12.png`, y `.jpg`, `.bmp` o
`.gif`), que cambia sola al pasar de lámina. Va **encima** de la lámina, vista
a medias --empieza al 50 %--, para que se vean las dos: `t` la esconde, `+` y
`-` la dejan ver más o menos, de diez en diez entre el 10 % y el 90 %. Son `+`
y `-` y no corchetes porque en un teclado español los corchetes piden AltGr.

Pruebas en `tests/test_trace.py`: dónde cabe una imagen cuadrada y una
demasiado ancha, cuál se coge de la carpeta, y la ventana, mirando el color
de un píxel: con la imagen roja encima está a medio camino entre el rojo y lo
de debajo, escondida es lo de debajo, con `+` es más rojo, y fuera de la
imagen centrada no cambia nada. Vista en una captura, la lámina 5 del faro
calcada sobre la 2.

### Los avisos, y el tiempo medido

En `regac/cautions.py`, sin ventana, y en el visor debajo de la lámina:

- **Un relleno que se escapa.** Se busca la forma que tiene en GAC: el
  relleno recorre la columna de su semilla y tiende una fila en cada altura,
  así que por un hueco de un píxel sale **una sola fila**, que sobresale de
  la de arriba y la de abajo. Lo que se mira es eso, una fila que va al menos
  ocho píxeles más allá, por el mismo lado, que sus dos vecinas. Para saber
  hasta dónde llega cada fila, el dispositivo se envuelve y, antes de tender
  cada una, se mira hasta dónde podría llegar. Visto en dos de MegaCorp: son
  de verdad, pasillos de una fila por los que el relleno cruza la lámina, y
  el original los hace igual, porque el renderer es fiel.
- **Un relleno que no hace nada**, con la semilla en un píxel ya puesto.
  MegaCorp los tiene a docenas: el mismo `FILL` repetido.
- **Los bytes** de la lámina y de todas: dos de largo, uno por orden y uno por
  número, dos el de `CALL`, y cuatro en el índice.
- **El tiempo: decidido por el usuario, medido y no estimado.** `c` manda la
  lámina a la construcción de cada máquina que dibuja una lámina y para,
  `test_picture.asm`, en ZEsarUX, y cuenta los ciclos del Z80, como las
  pruebas lentas: en `regac/measure.py`, que usa `tests/emulator.py` desde
  donde está. Spectrum, CPC y MSX, que son las que tienen esa construcción.
  Tarda entre 13 y 18 s de reloj, así que va en un hilo aparte y la ventana
  sigue. Dice si la medida es de antes del último cambio. La lámina 1 de
  MegaCorp: 2,30 s en el Spectrum, 2,22 en el CPC y 2,16 en el MSX.

Pruebas en `tests/test_cautions.py`: una caja con un agujero de un píxel en
la pared se escapa y dice por dónde, sin el agujero no dice nada, una semilla
en la pared no rellena, una pared inclinada no es un rayo, el faro no dice nada
más que sus bytes, `n` lleva al relleno, y la primera lámina del faro medida
en el Spectrum de verdad, dentro del tope.

## Las elipses del faro, y lo que `gac.md` decía de ellas

Al empezar el editor de láminas, que tiene que saber qué punto de una
`ELLIPSE` se arrastra: `gac.md` decía que `ELLIPSE x1 y1 x2 y2` es la elipse
**inscrita en ese rectángulo**, y no lo es. Lo que el renderer leyó en el
original, en `$88FE`, es que **el primer par es el centro y el segundo un
punto que da los radios**, lo que dista del centro. Y el faro no seguía ni lo
uno ni lo otro: sus cinco elipses llevaban los radios sueltos --`ELLIPSE 128
140 10 8`--, que con la regla de verdad son radios de 118 y 132. La lámina 1
tenía una elipse que llenaba la pantalla donde iba la luz de la linterna, y la
5 unos anillos de lente que se salían del marco. Nadie lo había mirado: las
pruebas comparan las máquinas con el renderer, y el renderer dibujaba lo que
estaba escrito.

Corregidas las cinco, con los radios que su autor quiso, y `gac.md`. Vistas
las láminas 1 y 5 antes y después.

Y una prueba que el saludo del faro había dejado torcida:
`test_it_can_be_played_to_the_end` esperaba ver «sendero» en la pantalla del
Spectrum al empezar, y la ventana de texto son ocho líneas: con el saludo
debajo, la primera línea de la sala se sale por arriba. Pasó el día del saludo
porque miró antes de que se escribiera. Ahora espera al final del saludo y
pide lo que queda a la vista de la sala; se ha pasado dos veces seguidas.

## La distribución

- **`regac` como orden**: `[project.scripts]` en `pyproject.toml`, y se instala
  desde el repositorio (`poetry install` o `pip install -e .`), apuntando a él
  y no copiándolo, porque `make` construye con `z80/` y `x86/`, que están al
  lado del paquete. Por eso no va a PyPI. Probado con `poetry install
  --only-root`: `regac -h` responde desde otra carpeta.
- **CI**: `.github/workflows/tests.yml`, en Ubuntu con Python 3.11 y el último,
  las pruebas `not serial`. Sin `tools/` ni `snapshots/`, que no están en el
  repositorio, las que piden emulador o las aventuras originales se saltan
  solas.
- **La release**: **decidido por el usuario**, un script local y no un flujo
  de GitHub. Es `regac make proyecto.toml --zip faro.zip`: lo construido, una
  carpeta por máquina, en un zip para subirlo a mano. Lo mira
  `test_every_machine_it_names_comes_out`. **Y cambiado después por el
  usuario**, con la 0.2.0 ya etiquetada: ahora lo hace GitHub,
  `.github/workflows/release.yml`. Al subir una etiqueta `v*` --o a mano desde
  Actions, para una que ya está-- instala NASM de la distribución y compila
  sjasmplus de su repositorio, en la v1.23.1 que se usa aquí y sin Lua, que
  nada de esto usa; construye el faro con ese mismo `--zip` y lo adjunta a la
  release de la etiqueta, que crea si no la hay.

**La CI se simuló aquí antes de subirla**, y encontró tres fallos que ya
estaban y que en esta máquina no se veían, porque aquí están `tools/` y
`snapshots/`: lo que va al repositorio se copió a una carpeta aparte y se
pasaron las pruebas con un PATH sin NASM ni DOSBox-X. Salían 32 fallos:

- `test_latin.py` sacaba la fuente de la que construye las letras con marca
  de `snapshots/megacorp2.json`, en 29 pruebas que no tienen nada que ver con
  MegaCorp. Ahora usa la del faro, que está en el repositorio; las 34 siguen
  pasando.
- `test_interpreter.py` guardaba y cargaba una partida de MegaCorp; ahora del
  faro, que tiene cuatro objetos.
- `test_every_machine_it_names_comes_out` construía sin mirar si había
  ensambladores; ahora se salta sin sjasmplus o sin NASM.

Con eso, la simulación da 181 pasadas y 302 saltadas. ~~**Lo que no se ha
podido probar** es Linux ni Python 3.11, que aquí no hay: lo dirá la primera
vuelta de verdad en GitHub.~~ **Probado**: la primera vuelta, con la subida de
la 0.2.0 (`28a9b1d`), salió verde en Ubuntu con Python 3.11 y con el último,
instalación y pruebas.

## Los huecos del texto

**Decidido por el usuario**: los tres, `\ctr n`, `\obj n` y `\turns`, y en
todos los textos donde vale `\ink` --mensajes, salas y nombres de objeto--.

**No queda ningún código libre por debajo del espacio**: el 0 es el nulo, el 1
el cambio de tinta y del 2 al 31 las letras con marca. Así que los huecos van
detrás del mismo código 1, con una letra que los colores (`0` a `?`) no usan
--`T`, `C`, `O`-- y el número en dos caracteres de cuatro bits, como el color
va en uno y por lo mismo: todo son caracteres imprimibles y se empaquetan con
el texto sin que el compresor sepa nada. Está en `regac/text.py`.

**Un hueco es texto, y forma parte de la palabra en la que está.** Eso pedía
dos cambios en el Z80 y en el PC:

- Un cambio de tinta acababa la palabra en cuanto llegaba el código 1. Ahora
  la acaba cuando llega el siguiente y dice que es una tinta; un hueco no la
  acaba, de modo que `(\ctr 5)` es una palabra.
- `print_digit` escribía cada cifra con `print_text`, que acaba en `text_end`:
  cada cifra cerraba la palabra, y `(42)` al final de una línea salía `(4` y
  `2)` debajo. Lo encontró la prueba. Para `PRIN` sigue así, que es lo que
  hacía; dentro de un hueco, `digit_within` manda las cifras a `text_put`.
- El nombre de un objeto se desempaqueta dentro del texto que lo pide: el
  desempaquetador guarda su estado en la pila de la máquina, así que puede
  llamarse a sí mismo. Para eso `print_packed` se partió en `unpack_message`,
  que sólo desempaqueta, y lo que hacía al final --vaciar la palabra y
  devolver la tinta--, que un nombre metido en un mensaje no debe hacer.

**Un nombre no puede llevar `\obj`**: podría ser el suyo, y el intérprete lo
escribiría para siempre. `check` lo dice y la construcción se niega. Puede
llevar `\ctr` y `\turns`.

En el Z80 viajan sólo con `-DHOLES`, que `regac make` pone cuando algún texto
tiene un hueco, como `PROCS` y los ruidos; en el PC, siempre. Además, sin eso
no ensamblaban los nueve ensamblados de prueba que incluyen `textout.asm` sin
la máquina virtual (`vm_counters`, `print_number`): `IFDEF` de sjasmplus
pregunta por definiciones y no por etiquetas, se probó.

`runGAC.py` los llena con `shown()`, que usa también `runGAC_pygame.py`; y
`split_inks` recibe ya el texto con los códigos y los huecos llenos.

**Lo que no hace**: el número se escribe con cifras, no con un nombre de
`.def`, porque los nombres se resuelven en las condiciones y el texto se
expande después; y una cifra pegada detrás del número se leería como parte de
él. Las dos están dichas en `formato-fuente.md`.

Pruebas en `tests/test_holes.py`: la codificación, la vuelta al fuente, los
espacios, lo que se llena, los números que no pueden ser, un nombre dentro de
un nombre y un `\obj` a un objeto que no hay; y la misma aventura en Python,
en el Spectrum y en el PC --un contador, un nombre con un contador dentro, los
turnos, una sala con un hueco, y `(\ctr 5)` pegado a una tinta--. Y la que
parte la línea: `(42)` donde no cabe tiene que bajar entero, en el Spectrum a
32 columnas y en el PC a 40. Se ha visto fallar en el Z80 quitando
`digit_within`.

## El visor de láminas

`regac draw fuente.gac 12 -m cpc`, en `regac/viewer.py`: la lámina en una
ventana de pygame-ce, que ya era dependencia, dibujada con el mismo
renderer que `render` y que el de las comparaciones con los intérpretes, en
el dispositivo de la máquina elegida (`device_for`, como `render`). Mira el
fuente y lo que hay a su lado tres veces por segundo y lo vuelve a leer al
guardarse, para la máquina que se ve, porque un `.if` puede darle otra
lámina. Si no se lee, lo dice y deja la última buena. Las máquinas son las
que tienen intérprete; una aventura de Amstrad, sólo donde están sus reglas
(`cpc`, `next` y `cga`).

Se recorre orden a orden, con lo que puso la última en magenta, y un `CALL`
se abre en su sitio hasta la misma hondura que dibuja el renderer. **Hacia
delante dibuja sobre lo que hay; hacia atrás vuelve a empezar**, porque un
relleno no se deshace: medido, una lámina entera tarda hasta 1,4 s en
Python (Vajillas #12 en el CPC, que además elige sus tintas dibujándola
entera), y redibujar desde el principio a cada paso no se podía. El
dispositivo limpio se hace una vez y se copia.

Un `PLOT` del Spectrum enciende 64 puntos en magenta, y no es un error: la
celda entera cambia de color, que es el choque de atributos, y se ve.

Pruebas en `tests/test_viewer.py`: recorrida orden a orden, adelante y atrás,
la lámina sale exactamente como la dibuja el renderer entera, en las seis
máquinas, con el faro y con una lámina hecha con todas las órdenes. Esa
segunda hizo falta: el faro sólo tiene un relleno, y un recorrido que se
saltaba los `FILL` pasaba con él solo; con ella falla. Además, que sigue al
fuente y guarda la última buena, las coordenadas del ratón, y la ventana
entera corriendo sin pantalla con teclas que se le dan.

**Lo que no hace, apuntado**: no pinta el borde. `BORDER` se recorre y se
dice, pero cada dispositivo guarda el borde a su manera --un color del
Spectrum, una entrada de paleta, una pluma-- y ponerlo alrededor de la lámina
pide traducir cada uno.

## Cosas menores

### Lo residente del 128 y del +3, que nadie vigilaba

En el 128 y en el +3 el intérprete va en $8000 y lo residente de la base de
datos detrás, y todo tiene que acabar antes de $C000, que es la ventana por la
que entran los bancos: lo que pasara de ahí se lo llevaría en silencio el
primer banco que se paginara. **Ningún `ASSERT` lo miraba**, cuando el PCW, el
MSX y el Next sí tienen el suyo. Medido con las ocho, en las dos máquinas:

| aventura | margen hasta $C000 |
|---|---:|
| Bangkok2 | **338 bytes** |
| quijote1 | 1539 |
| Bangkok1 | 2422 |
| quijote2 | 2790 |
| vajillas2 | 3431 |
| megacorp2 | 3471 |
| megacorp1 | 3697 |
| vajillas1 | 4069 |

Caben todas, pero Bangkok2 va justa y nadie lo habría dicho. Ahora
`game128.asm` y `game3.asm` llevan `ASSERT last <= $C000`: no cambia ningún
binario, y una aventura que no quepa deja de ensamblar en vez de salir rota.
Salió al medir la memoria de cada máquina para las aventuras de CPC.


### `SAVE` y `LOAD` en `runGAC.py`, que eran dos `TODO` con un `pass`

Ya juegan. Lo que se guarda son las mismas cosas que el bloque `vm_state` del
Z80 —dónde está el jugador, lo que puede llevar y lo que lleva, las banderas,
los contadores, la pila y dónde está cada objeto— pero en JSON y no como
volcado de memoria, por dos motivos.

**Dos de las cosas de ese bloque no existen aquí.** `vm_seed` es el generador
de las máquinas y esto usa el de Python; y `obj_entry` son 512 bytes de
**direcciones** que apuntan a la base de datos.

Y eso segundo llevó a lo de abajo, que resultó no ser un desperdicio sino un
fallo.

### `obj_entry` fuera de la partida guardada

**El bloque eran 1255 bytes y ahora son 743.** Así se reparten:

| campo | bytes |
|---|---:|
| dónde está cada objeto (`obj_loc`) | 512 |
| los contadores | 128 |
| la pila de condiciones | 64 |
| las banderas | 32 |
| dónde está el jugador | 2 |
| lo que puede llevar y lo que lleva | 2 |
| la semilla del azar | 2 |
| el byte que fue la música | 1 |
| ~~`obj_entry`~~ | ~~512~~ |

En una cinta de Spectrum a 1500 baudios son **4,0 s en vez de 6,7**, cada vez
que se guarda y cada vez que se carga.

**Que sobraba estaba claro**: `obj_entry` lo construye `vm_init` recorriendo la
tabla de objetos y **nadie vuelve a escribirlo** —comprobado, las únicas
escrituras están en `vm_init`—. Además va casi vacío: son 256 huecos indexados
por número de objeto y las ocho aventuras tienen entre 8 y 19.

**Lo que no estaba claro es que fuera un fallo**, y lo era. Son *direcciones*
a la base de datos, que en el Spectrum va detrás del código con un
`ALIGN 256`: si el intérprete cruza un múltiplo de 256, la base de datos se
mueve y **toda partida guardada antes deja de valer**. Y no falla de frente:
`vm_init` construye la tabla buena al arrancar, `LOAD` la pisa con la vieja, y
los objetos quedan apuntando a otro sitio —pesos y nombres equivocados, sin un
aviso—.

Medido, no supuesto: construido el intérprete de antes de una tarde de tres
cambios con la misma base de datos, `database` estaba en `$A000`; después, en
`$A100`. **Se movió.** Y es también lo que impedía que una partida pasara de
una máquina a otra.

El argumento para dejarlo era no romper las partidas ya guardadas, y ese
argumento estaba vacío: **ya estaban rotas**.

`obj_entry` se queda inmediatamente **antes** de `vm_state`, de modo que el
único `ldir` de `vm_init` sigue cubriéndolo junto con `obj_loc` y no hace falta
partirlo en dos.

Y hay prueba, en `test_conditions_z80.py`: que `obj_entry` está fuera del
bloque y que el bloque no mide más que los campos que le tocan. Comprobada al
revés metiendo `obj_entry` otra vez dentro. Mira la forma y no el
comportamiento; comprobar lo segundo pediría dos construcciones de tamaños
distintos y una partida jugada entre las dos.

**Lo otro es que un fichero tiene nombre y una cinta no**, así que hay que
pedirlo; y puestos a preguntar, lo que se escribe puede ser algo que una
persona sepa leer.

Una carga que falla **deja la partida exactamente como estaba**, que es lo que
hacen las máquinas: su `LOAD` no mira si el bloque entró, sigue con la
condición. La diferencia es que aquí lo dice, porque una cinta avisa sola de
que no ha cargado y un terminal callado parece que fue bien.

Y no describe la sala después, igual que las máquinas: lo que se diga es lo
que diga la aventura a continuación.


`deGAC` ya lee las tres máquinas. Reconoce por sí solo una instantánea de
Spectrum, una de CPCEMU y una de VICE, y a una imagen plana de memoria, que es
lo que sale de un disco de Amstrad, hay que decirle de qué máquina viene con
`-m`. Las tablas están en sitios distintos en cada una, y las láminas usan
órdenes distintas, así que eso va aparte; lo demás sale igual.

Comprobado con Los pájaros de Bangkok de Amstrad contra la misma aventura de
Spectrum: 47 nombres en las dos, 11 objetos, 27 condiciones locales, y el
vocabulario palabra por palabra el mismo. Las 44 láminas coinciden con una
lectura independiente de los bytes en crudo.

Con eso son ya las tres de Amstrad leídas, las seis partes, cada una contra su
versión de Spectrum: Bangkok, Megacorp y La guerra de las vajillas. Ninguna
necesita el emulador; las tres salen del disco.

Lo de Commodore está escrito a partir del decompilador de referencia y **no se
ha probado nunca**, porque no tenemos ningún fichero de C64 a mano.
**Aparcado definitivamente.** Se queda donde está, sin tocarlo y sin contarlo
como funcionando: código que no se ha ejecutado una sola vez no es una
función, es una deuda, y decirlo aquí vale más que dejarlo pareciendo que
anda. Si algún día aparece un fichero de C64, lo primero es correrlo contra el
decompilador de referencia; hasta entonces no hay nada que hacer.

Lo de casar palabras por prefijo estaba al revés de como lo habíamos contado.
El que se equivocaba era el nuestro, no el de Python: al original le tecleas
`EX` y pregunta qué examinar, y le tecleas `EXAMINAR`, una letra más de las que
guarda, y dice que no entiende. O sea que basta escribir el principio de una
palabra, y nunca vale una más larga que la guardada. El precio es que `LA` se
la come `LAMPARA`, y el original lo paga igual. Los dos intérpretes lo hacen ya
así, y como nuestro vocabulario va en orden alfabético, de las entradas que
empiezan igual gana la más corta.

El segundo nombre tampoco se leía en Python: `__parse_input` tenía una
condición que no podía ser cierta nunca. Arreglado, y con la misma regla que el
Z80, que pide que haya un primer nombre antes de aceptar el segundo.

### Las tres pruebas que fallaban de vez en cuando, y lo que eran

Ninguna era del intérprete: las tres eran carreras de la prueba contra el
emulador. Están arregladas, y lo que se aprendió vale para la siguiente.

**Las dos de música** —`test_music_source_z80` y `test_sound_z80`— miraban el
puntero del reproductor de Arkos (`PLY_AKM_Track1_PtTrack`) una sola vez. Eso
falla por dos motivos a la vez: recién encendida la bandera el reproductor
todavía no ha tenido su primera interrupción y el puntero vale cero, y además
**el puntero da vueltas a un track que se repite**, así que dos lecturas
separadas pueden caer en el mismo sitio con la música sonando perfectamente.
Ahora hay un `pointer_moves` en `tests/test_music_z80.py` que espera a que el
puntero esté en otro sitio, con plazo. Trece vueltas seguidas en verde; antes
fallaba una de cada tres.

**La del Next** decía «never finished» de una lámina distinta cada vez, y no
era lentitud: muestreado el PC cuando falla, salía dentro del bucle de
aparcamiento. O sea que la máquina seguía parada sin haber empezado, porque
**un `set-register PC` sobre un procesador en marcha no siempre toma**. La
bandera no podía llegar nunca y el minuto de espera era tirado.

Y dos cosas que costaron encontrarse:

- ~~**No usar `enter-cpu-step` para escribir el PC con la máquina parada**,
  que deja al emulador nueve veces más lento.~~ **Falso**, y es justo lo que
  hay que hacer: ver «El indicador del modo paso a paso», más abajo.
- **Una prueba que sigue después de un fallo así miente.** Con la máquina a
  medias, todo lo que se lee después es basura: la vuelta que encontró esto
  reportó 26 láminas mal cuando había pasado una sola cosa. Ahora para en la
  primera y dice dónde estaba el procesador, que es lo que distingue una lámina
  lenta de una máquina que no arrancó.

La prueba de las 196 del Amstrad tenía la misma carrera aunque no se la hubiera
visto saltar, y lleva el mismo remedio.

**Y el remedio no lo era del todo.** Dos días después la del Next volvió a
fallar de vez en cuando —tres de trece vueltas—, y ahora con otra cara: el
PC en el relleno o en las rectas, dibujando sin acabar nunca. Metido un
diagnóstico en la prueba, la vez que cayó el procesador estaba **dentro de la
base de datos**, con la pila también ahí y bytes de código cambiados, como
`config_init+4` y `text_init+3`: la máquina se había ido a ejecutar basura.

Lo que encaja con eso es que el emulador atiende las órdenes en un hilo propio,
y **un `set-register PC` puede caer entre el primer byte de una instrucción y
el resto**, que entonces se lee de donde apunta el PC nuevo. En el bucle de
aparcamiento del Next hay un `call map_piece`: si el cambio cae después del
`CD`, la dirección sale de los primeros bytes de `redraw` —`ld sp`, `31 00 9F`—
y la llamada va a `$0031`, a la base de datos. Las órdenes «perdidas» que
arreglaban los reintentos eran seguramente la cara buena de lo mismo. Con el
intérprete de antes no había saltado en diez vueltas, pero cambiar el tamaño
del código cambia qué instrucciones están donde cae la orden.

Ahora **no se escribe el PC con la máquina en marcha**. Los cuatro bancos de
pruebas que dibujan lámina tras lámina —Spectrum, Amstrad, MSX y Next— tienen
un byte `go_flag` que su bucle de aparcamiento mira, y la prueba escribe ese
byte en vez del PC. Un byte de memoria no tiene un medio donde caer. Con eso la
del Next salió **diez de diez, y ninguna vuelta necesitó volver a pedir**,
cuando antes una de cada tres o cuatro tardaba el minuto de más del reintento.
Los reintentos se han quitado.

~~Quedan otras pruebas que escriben el PC, pero una sola vez, y ya reintentan.~~
Ya no queda ninguna: ver lo que sigue.

### Y una que aparecía en el PCW, que era escribir en marcha

`test_graphics_pcw` fallaba cada pocas vueltas --una lámina con puntos
distintos de los de la referencia, nunca la misma, y nunca una que no
acabara-- y pasaba al repetirla a solas. Lo que encaja es lo que ya estaba
escrito en `start_code`: un PCW sin disquete sigue ocupado con el cargador que
le da su teclado, y de vez en cuando ese cargador pisa lo que se le acaba de
escribir.

Los reintentos que había cubrían que **no arrancara**, no que arrancara con un
byte cambiado: código con un byte distinto puede llegar igual hasta el final y
poner la marca que iba a poner, de modo que esperar la marca no lo ve. Quien lo
ve es la pantalla, y para entonces parece un fallo del dibujo.

Ahora `start_code` hace dos cosas. **La máquina se queda parada mientras se
escribe**, de modo que no corre nada suyo entre el primer byte y el salto y no
hay momento que pisar; y **se relee lo escrito y se compara** antes de
apuntarle el contador, que es lo que la parada no puede prometer --un byte que
se torciera antes de empezar la parada se encontraría de la otra manera--. Si
la comprobación falla, o la marca no llega, se vuelve a escribir entero.

Y el mecanismo tiene prueba propia, en `tests/test_harness.py`, contra una
máquina de papel que pierde un byte del primer build que le dan: comprueba que
se vuelve a escribir, que **no se arranca nada sin comprobar**, y que una
máquina que nunca lo coge entero se da por imposible en vez de arrancarla sobre
algo que se sabe mal. Son cuatro pruebas y tardan seis centésimas, que es lo
que vale poder tocar esto sin montar un emulador.

**Y lo mismo para todos, por si acaso.** Sólo el PCW había dado la cara, pero
escribir en una máquina en marcha lo hacían cinco sitios más, y el del Quijote
bajo era el peor de todos sin que nadie se hubiera fijado: entre el mover y la
isla, la máquina vuelve del `ret` del mover a lo que hubiera detrás y corre eso
--cualquier cosa-- mientras se le está escribiendo la base de datos encima. Así
que la parte de escribir está ahora en `Session.put`, que para la máquina, lo
escribe, lo relee y sólo entonces hace lo que haya que hacer todavía parada
--apuntarle el contador, que es lo que `start_code` quiere--. Lo usan las de
gráficos del Amstrad, la de las 196 láminas, la partida del Amstrad y la del
MSX, y la del Quijote bajo. Un byte suelto escrito como señal a código que ya
corre no pasa por ahí: ése está para que lo vean y lo cambien.

### El indicador del modo paso a paso, que costaba ocho segundos por orden

La prueba gráfica del MSX empezó a fallar de vez en cuando por lo mismo, pero
en el arranque: `start_code` escribe el código y apunta el PC **una vez**, con
el MSX dentro de su BIOS, y a veces la máquina no llegaba a dibujar ni en tres
intentos. No se pudo cazar a propósito —veinticinco arranques seguidos sin
fallar—, así que se fue a la causa: no escribir el PC con la máquina en marcha
en ningún sitio.

La manera limpia es parar el procesador, escribir y soltarlo, que es
`enter-cpu-step`, `set-register` y `exit-cpu-step`. Se había descartado porque
«dejaba al emulador nueve veces más lento». **No lo deja**: medido en ciclos
por segundo, 2,04 millones antes de parar y 2,04 después. Lo lento era nuestro
lector del socket. Con el procesador parado el emulador contesta
`command@cpu-step> ` en vez de `command> `, el lector sólo reconocía el
segundo, y cada orden dada en ese estado esperaba entera su espera máxima de
ocho segundos. Aquella vuelta del Next daba cuatro órdenes así por lámina —la
parada, las dos escrituras y la del PC—, y treinta y una láminas por cuatro
por ocho segundos son los diecisiete minutos de más.

Ahora el lector reconoce los dos indicadores, y `Session.jump` para, escribe y
suelta. **Las catorce pruebas que escribían el PC lo hacen por ahí**, y
`start_code` también. La del MSX vuelve a tardar sus dos minutos. Las pruebas
de láminas se quedan con su `go_flag`, que ni siquiera necesita parar nada.

Y la suite con eso puesto destapó **otra de la misma familia**, que llevaba
mucho tiempo fallando de vez en cuando sin estar apuntada:
`test_fills_original[shade]`, «the original never came back from its fill».
Esa prueba llama al relleno del GAC original con una pila de dos bytes que
apuntan a un bucle suyo, y ponía **el `SP` con la aventura original en marcha**.
Si en ese instante la aventura hacía un `RET`, se comía la vuelta preparada
para el relleno, y cuando el relleno acababa su propio `RET` sacaba basura. Toda
su preparación va ahora dentro de `Session.held()`, que para la máquina
mientras dura el bloque y la suelta al salir; `jump` es ese mismo bloque con
sólo el PC dentro. Ocho vueltas seguidas en verde. No queda en las pruebas
ningún registro escrito con la máquina en marcha.

De paso se miró lo otro que se había dado por imposible, `run` en paso a paso
con un punto de parada, que sería un reloj exacto al ciclo: no era el
indicador. Tumba el emulador. El reloj sigue siendo el de mirar la bandera cada
centésima.
