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
porque el campo se escribía vacío.

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

**El presupuesto de bytes está agotado.** `ASSERT last <= MASK` mide lo que
hay entre el final del intérprete y la máscara de los rellenos, y desde que el
ajuste de líneas aprendió a guardarse el separador la cuenta sale **clavada**:
`last` vale `$A000`, que es la máscara. No es holgura, es el tope. Lo próximo
que crezca en `z80/common/` lo va a romper, y entonces hay dos salidas: apretar
lo que haya crecido --así se resolvió ésta, juntando `word_out` y `word_piece`,
midiendo con `add a,a` en vez de `and`, y metiendo dos banderas en un byte-- o
mover algo a un banco. El aviso salta al compilar, no en la máquina.

**Lo que queda de esta máquina**: nada urgente. Guardar en fichero por el API
de NextZXOS, si alguna vez se quiere en vez de la cinta. El sonido ya está, por
el AY compatible y con la interrupción en modo 2.

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

**Lo que queda de esta máquina**: una lámina, una sola, que pasa del tope.
Están medidas las 196 de las ocho aventuras, con un contador de ciclos parado
en seco por un punto de ruptura, y **todas salen idénticas a la referencia**;
la más lenta de cada aventura va de 2,9 a 4,2 segundos, salvo en una: la 28
de Bangkok2, que cuesta **6,11 s**. Esa misma lámina en un Spectrum cuesta
**4,67 s**, así que la diferencia entre máquinas es de 1,31, no la vez y media
que decía antes este párrafo; y lo que la hace cara no es el MSX, es ella: en
el Spectrum también es la peor con diferencia (la 21 son 1,48 s y la 26, 0,30).

Dónde se van esos seis segundos no se sabe todavía, y conviene decirlo así
porque los dos modos de mirarlo se contradicen. Mirando el contador de
programa cada poco, 400 veces, sale `colour_span` 19%, `span_extent` 18% y
`mark_span` 14,5%. Poniendo un `RET` encima de cada rutina y volviendo a
dibujar, quitar `gfx_fill` entero ahorra 0,86 s, `gfx_line` 0,28 s y
`colour_span` 0,02 s. Lo segundo miente por construcción —sin los rellenos la
lámina ya no es la misma y el resto tiene menos que pintar— y lo primero
tampoco es exacto, porque preguntar detiene la máquina un instante. Antes de
decir dónde apretar haría falta un perfil de verdad, instrucción a
instrucción.

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

    $0300-$1FFF  la música, si la hay
    $2000-$3FFF  lo residente de la base de datos (desde $0300 sin música)
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
  controlador entrega un byte cada treinta y dos millonésimas y no espera, y las
  trescientas por segundo de la música perderían alguno. El bucle de los datos
  gasta unas veinte.
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
detrás (`LOAD LOOK WAIT`). Ninguna de las dos referencias implementa `LOAD`
—grackle dice «Not implemented (yet)» y `runGAC.py` tiene un `TODO`—, así que
se miró en el original de Spectrum, leído y viéndolo funcionar.

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

**Cómo viaja.** Como la música, porque la línea de BASIC que carga está ella
misma en `$0170`: el fichero entra en `$4000` con un movedor delante, el
movedor lo baja y vuelve, y entonces la base de datos se carga encima de donde
estuvo. El cargador son cinco líneas: `MEMORY &3FFF`, cargar el intérprete,
llamar al movedor, cargar la base de datos y llamar al arranque de la isla.
BASIC guarda sus variables debajo de `$3FFF` y hacia abajo; el intérprete acaba
sobre `$2450`, así que hay siete kilobytes de nadie entre los dos.

**Música y esto no van juntos** —la música vive en `$0300` y son siete
kilobytes—, y ninguna de las aventuras que lo necesitan tiene.

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

Lo que mide, con el arreglo que cuenta más abajo y la segunda vuelta de
rellenos:

| aventura | la más lenta |
|---|---|
| Bangkok1 | 2,4 s |
| Bangkok2 | 6,1 s |
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

### `TEXT` y `PICT`, medidos y sin hacer

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

**Y está hecho a medias, que es lo honesto de contar.** La mitad que es común
—con `TEXT` no se dibuja lámina— vale en las cinco máquinas: la decide
`describe_location` mirando `vm_graphics`, que se escribía desde el principio
y no leía nadie. La otra mitad, la ventana, está ya en las cinco:

| máquina | la ventana | por qué |
|---|---|---|
| Spectrum | **sí** | |
| MSX | **sí** | |
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
- **El 464 sigue sin sitio.** El relleno rápido costó unos 300 bytes y se
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

## La música, que ya suena

Suena en las cuatro máquinas que tienen AY —Spectrum 128, Amstrad, MSX y
Next—, tocada desde la interrupción mientras el bucle principal no hace nada
con ella. Lo que se toca es de **Arkos Tracker 3**, que es lo que usa hoy
cualquiera que componga para estas máquinas, y su reproductor es MIT como todo
lo de `z80/`.

**El reproductor viene convertido, no copiado a mano.** Los fuentes de Arkos
están escritos para RASM y tienen tres cosas que son de RASM y no del Z80:
las marcas `(void)` de Disark, macros que fabrican etiquetas con su argumento,
y banderas que se asignan con `=` pero se preguntan con `IFDEF`. `arkos.py`,
en la raíz junto a `disk.py` y `grab.py`, las quita sin tocar un solo byte de
lo que ensambla; cuando salga una versión nueva de Arkos se vuelve a pasar. El
AKM ocupa 1602 bytes y cuesta entre el 4 % y el 5 % de un frame de Spectrum,
con picos del 7 % en los compases más cargados.

**La interrupción, máquina por máquina.** Tres van en modo 2, porque el $0038
es la rutina de la ROM —o directamente la base de datos, en las máquinas que
se quedan con toda la memoria—, y el Amstrad se queda en modo 1, porque con
las dos ROM fuera el $0038 es RAM nuestra. Cada máquina dice dónde caben la
tabla y la rutina, en la parte de su mapa que no se mueve:

| máquina | tabla | rutina | notas |
|---|---|---|---|
| Spectrum 128 | $BE00 | $BDBD | entre el intérprete y la ventana |
| MSX | $BE00 | $BDBD | en la mitad alta, donde la BIOS no vuelve |
| Next | $B000 | $B1B1 | encima de la máscara y debajo de la pila |
| Amstrad | — | modo 1 en $0038 | RAM, con las dos ROM fuera |

Ni la tabla ni la rutina viajan en el fichero. Están en un rincón al que el
intérprete no llega, y llevarlas allí obligaría a llevar también los kilobytes
de en medio —un minuto de nada en una cinta—, así que la rutina se ensambla
donde va a correr, se guarda con el código y se pone en su sitio al encender
las interrupciones.

**El ritmo es un reloj y no una cuenta.** Una melodía quiere sonar cincuenta
veces por segundo; el Amstrad interrumpe trescientas, el Spectrum y el Next
cincuenta, y el MSX las que refresque su televisión: cincuenta en Europa y
sesenta en Japón y América, y eso no se sabe hasta que arranca. Así que cada
interrupción suma cincuenta a un reloj y, cuando el reloj tiene tanto como
interrupciones da la máquina en un segundo, se le resta y se toca. Cincuenta
entre cincuenta toca siempre, cincuenta entre trescientas una de cada seis, y
cincuenta entre sesenta cinco de cada seis, repartidas lo mejor que permiten
las interrupciones enteras. El MSX lee de qué televisión es en el bit 7 del
$002B **antes** de quedarse con la máquina, que es cuando todavía hay BIOS a
la que preguntar; la prueba lo compara con lo que dice la ROM del emulador.

**Varias melodías.** El build dice las que tiene en una lista, una línea por
melodía, y arrancar una es un número y nada más:

    music_tunes:
            MUSIC_TUNE  menu, 0
            MUSIC_TUNE  menu, 1
            MUSIC_TUNE  cueva, 0
    music_tunes_end:

Una melodía es una dirección y qué subcanción tocar de ella, porque **un export
de Arkos puede llevar varias subcanciones** y comparten instrumentos y tablas:
es con mucho la forma más barata de tener más de una. Dos exports distintos
también valen, sólo que cuestan lo que ocupan. `music_start` recibe el número
contando desde cero y, si el build no tiene esa melodía, no hace nada —una
aventura puede nombrar una que se perdió, y leer la dirección que no está sería
tocar basura—. La cuenta sale sola de la longitud de la lista, así que añadir
una melodía se hace en un sitio.

Un detalle que costó descubrir: el tracker **nombra las etiquetas de un export
con el título de la canción**, y una canción sin título se exporta como
`Untitled`. Dos de esas en un mismo build son la misma etiqueta dos veces y el
ensamblador para en seco, así que cada melodía va envuelta en su `MODULE`, que
le pone prefijo a todas, con la etiqueta de la dirección fuera.

**Y los ruidos son del autor en los dos lados.** Con chip, `SOUND n` toca el
efecto n del banco que exportó del tracker. Sin chip —o con uno que no está
tocando nada—, toca el n de la sección `/SOUND` de la propia aventura: tono,
pasos y paso, los mismos tres números que tienen los cinco que trae el
intérprete, que ahora son un valor por defecto y no una regla. `regac build` lo
escribe donde el ensamblador lo lee, como hace con las melodías, y de paso
`regac check` ya puede decir «`SOUND 3` y esta aventura dice tener dos».

**Los efectos de sonido, puestos.** Un efecto de Arkos es un instrumento suelto
que el reproductor superpone a uno de los tres canales la próxima vez que la
interrupción lo llama: pedirlo escribe cinco bytes y vuelve, la melodía sigue
por debajo con un canal menos, y cuando el efecto se acaba el canal vuelve a la
melodía. Va al canal tercero, porque las melodías de estas máquinas suelen
llevar la voz en el primero y el bajo en el segundo.

**Ya se pide desde la aventura.** Tres opcodes nuevos, los primeros que no son
del GAC original —había sitio de sobra: un byte con el bit 7 puesto es un
número, así que del $40 al $7F estaba libre—:

| opcode | qué hace |
|---|---|
| `MUSIC n` | toca la melodía n de la lista, contando desde cero |
| `SOUND n` | hace el efecto n del banco, contando desde uno |
| `QUIET` | calla la música |

Una versión **sin música** —el PCW, que no tiene chip; un Spectrum de 48K;
cualquier máquina antes de que el autor componga nada— lee los tres igual, se
come el argumento y sigue. Eso es lo que permite que una misma aventura se
compile para cinco máquinas sin escribirla cinco veces, y es la prueba que más
dolería perder.

**Dónde cabe la música, máquina por máquina.** Esta fue la sorpresa. Encima del
intérprete no hay sitio en ninguna parte: en el 128 el código, lo residente de
la base de datos y el rincón de la interrupción llegan juntos a $C000, y de las
ocho aventuras descompiladas **sólo una** dejaba hueco para reproductor y
melodía —y por treinta y dos bytes—. Así que cada máquina la pone donde puede:

| máquina | reproductor y buffer | las melodías | cuánto hay |
|---|---|---|---|
| Spectrum 128 | $6000, debajo del intérprete | una página propia, la siguiente a las de la base de datos | 5 KB de buffer |
| Spectrum +3 | lo mismo | la última de las cuatro que tiene libres | 5 KB de buffer |
| Next | **$4000**, en la página de lo residente | dos páginas propias, de los cientos que le sobran | 4,7 KB de buffer |
| Amstrad | **$0300**, debajo de las dos ROM | ahí mismo | 15 KB |
| MSX | encima del código | ahí mismo | 7,4 KB |

Lo del Next es lo más bonito: esta máquina dibuja en layer 2, así que los
dieciséis kilobytes donde un Spectrum tiene la pantalla están vacíos.

**Las melodías en una página, y copiadas al tocarlas.** Una melodía ensamblada
con el intérprete cuesta su tamaño para siempre, suene o no. En las máquinas
con bancos ahora viven en una página que no usa nadie más y la que se pide se
copia a un buffer al arrancarla: una versión paga la melodía más gorda una vez,
lleve las que lleve, y nada hasta que suene la primera. Lo que lo hace posible
es que la melodía se **ensambla para el buffer y se guarda donde se guarda**,
que es para lo que está `DISP` —el mismo truco con el que viaja la rutina de
la interrupción—. La lista es lo único que se queda residente, porque se lee en
cualquier momento.

**El +3 es el 128 con otro reparto de páginas y otro medio.** +3DOS se queda
dos de las ocho, así que la página de las melodías sale de las cuatro que la
base de datos podía usar: una aventura de tres bancos tiene música ahí y una de
cuatro no, y lo dice el `ASSERT` al construir. Y nada viaja en bloques de cinta:
el cargador es código máquina —BASIC no sabe paginar— y lo que lee es un solo
fichero con las piezas seguidas, así que la música son dos piezas más de ese
fichero **en el orden exacto en que la tabla las pide**. Una pieza fuera de
orden no es una melodía que suene mal: es un banco de la base de datos cargado
encima del reproductor.

En el 128 las melodías viajan en **un bloque propio**, y en la tabla del
cargador va *después* del bloque del intérprete y no antes: el propio cargador
está ahí abajo, dentro de la línea BASIC en la que viajó, y un bloque que fuese
primero le caería encima de la tabla que todavía está recorriendo. En el Next
van en un banco nombrado en el `.nex` —un banco que nadie nombra es un banco
que el fichero no lleva, y lo que sale de eso es un reproductor leyendo un
buffer lleno de ceros—.

**El Amstrad, que era el que no cabía**, se arregló con veinte instrucciones. La
música no se puede cargar donde va a vivir: vive debajo de $4000 y la línea
BASIC que carga el juego está en el $0170. Así que viaja como **fichero aparte
con un movedor delante**: el cargador la trae al $4000, donde todavía no hay
nada, la llama, y esas veinte instrucciones la bajan al $0300 —a salvo de la
línea BASIC— y vuelven. Después se carga el intérprete encima y arranca, y se
la encuentra puesta. De ser la máquina más apretada pasa a ser la que más sitio
tiene para melodías: quince kilobytes que no quiere nadie.

**Tres decisiones tomadas**, por si se vuelven a discutir:

- **`MUSIC n` arranca esa melodía siempre**, aunque ya esté sonando. Es lo
  simple y lo predecible; una aventura que no quiera cortarla se guarda una
  bandera, que es lo que ya hace para todo lo demás.
- **La partida guarda qué sonaba**, porque la música es del juego y no de la
  máquina: un byte junto a las banderas y los contadores —cero si silencio, y
  si no la melodía más uno—, el mismo byte en todas las versiones, con música o
  sin ella, para que una partida tenga la misma forma en todas partes. `LOAD`
  lo obedece; si la carga falla, vuelve lo que sonaba antes.
- **Lo del autor es una línea por melodía y `regac make`.** La aventura dice
  las suyas en `/MUSIC`, el proyecto dice cuál es el banco de efectos, y de ahí
  en adelante no hay que escribir ensamblador ni pasar opciones.

**Lo que falta:**

- **El PCW no entra en nada de esto**: no tiene AY, sólo un zumbador. Sí
  existió periférico —el de DK'tronics, que era mando y sonido, y del que
  nuestro emulador emula el mando y no el sonido—, así que hoy no hay manera
  de probar aquí nada que se escribiera para él. Si algún día se quiere: el
  reproductor ya sabe hablarle a un AY, o sea que sería decirle los dos
  puertos, montarle la interrupción a esta máquina —que no la tiene— y buscar
  sitio en su mapa.
- **La sección `music` del formato binario sigue vacía.** Hoy las melodías son
  fuente de ensamblador y las coloca el ensamblador, que es quien puede; la
  sección queda para el día en que una melodía sea dato y no fuente.
- **El exportador de Arkos no lo hemos probado de verdad.** El gancho está
  —`music-tool`, o `SongToAkm` en `tools/`— y se prueba con un doble, pero
  nadie ha corrido aquí el binario real ni ha comprobado que sus argumentos
  sean `entrada salida`. Si no lo son, se dice en `music-tool` y ya está.

**Dos cosas que la música se lleva por delante, ya resueltas.** Grabar y cargar
la callan y la vuelven a poner alrededor de la cinta —el temporizado de un byte
se cuenta en ciclos y una interrupción en mitad de uno es un byte perdido—, y
en el Amstrad el barrido del teclado lleva las interrupciones quitadas mientras
dura, porque el AY está detrás del mismo 8255 y una interrupción en mitad del
baile deja el chip apuntando al registro de otro. Son treinta microsegundos; la
música no se entera.

**Y el autor no escribe ensamblador.** La aventura dice qué música tiene en su
propio fuente, en una sección `/MUSIC`, una línea por melodía: el fichero que
exportó del tracker y qué subcanción tocar de él. `regac build --music-defs
music/tunes.asm` escribe el fuentecillo que el ensamblador incluye, con la
lista por un lado y las melodías por otro, cada una en su `MODULE` y ensamblada
para el buffer; un fichero nombrado dos veces se incluye una vez y se apunta
dos, que es para lo que están las subcanciones.

Las melodías no están en el repositorio, que no son nuestras: las pruebas piden
una en `music/` y se apartan si no hay. Una versión con música se ensambla con
`-DWITH_MUSIC`, y con efectos además con `-DWITH_EFFECTS`.

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

  Las salidas, si alguna vez se quiere: escribirlo a ciegas desde documentación
  fiable, detrás de un define y sin prueba; o meter otro emulador en las
  herramientas —Joyce, el de John Elliott— sólo para esto. Lo que sí se sabe es
  que la máquina tiene interrupción de temporizador, así que el clic de tecla
  saldría gratis el día que se sepa el puerto, y la música pediría además
  montarle la interrupción, que hoy no la usa.
- ~~El Amstrad sin música~~, **hecho**: ahí el único altavoz es el AY, así que
  ahora `SOUND` le pide la nota al chip en vez de menear un bit. Es el mismo
  baile del 8255 que ya hacía el teclado, y lee **la misma tabla** que el
  motor de un bit —las notas, las duraciones y los números son de la aventura y
  no de la máquina—: un tono de la tabla es medio periodo del chip, así que
  `SOUND 2` suena a lo mismo aquí. Una versión con música no lo usa, que ahí
  los efectos son del tracker.
- **El clic con música puesta.** En el Spectrum y el MSX el altavoz es otro
  aparato y no molesta al AY, así que suenan a la vez sin más. En el Amstrad
  no podría ser, que es el mismo chip.

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
| Amstrad | la pluma, de cero a tres, que es lo que un color significaba en las aventuras de esa máquina |
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

**Lo que queda de esto**: decidir si un mensaje debería empezar siempre con la
tinta por defecto en vez de heredar la del anterior. Hoy hereda, que es lo que
hace que se pueda pintar un renglón entero sin repetir el comando, pero también
lo que hace que un mensaje que cambia la tinta y no la devuelve tiña todo lo que
venga después.

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
  hace con una semilla fuera, así que tampoco avisan.
- **Al Next no le sobran bytes.** La comprobación se escribió primero en
  dieciséis y no cabía bajo su máscara; queda en doce aprovechando que el
  marco son ciento veintiocho filas justas: se le resta el fondo y basta una
  comparación, porque lo que está por debajo se envuelve y falla igual.

**Lo que queda por leer**: nada del intérprete original. Queda el relleno, que
es lo único suyo donde no hemos preguntado por casos raros --rellenos que se
escapan por un hueco de un píxel--, y eso se pregunta con el mismo guión.

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

Está escrito en `word_over` y `word_print` de `z80/common/textout.asm`, con un
par de bytes de estado nuevos --`held_sep`, lo que cerró la última palabra, y
`sep_in_run`, si venía detrás de otro--; en `wrapped()` de `tests/emulator.py`,
que es el oráculo de las pruebas de texto; y en `runGAC.py`, que hacía lo de
las palabras bien sin saberlo y no sabía nada de lo demás.

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

De paso: **`runGAC.py` ya hacía lo mismo para las palabras** sin saberlo --mide
la palabra junto con el separador que la cierra, que sale la misma cuenta-- y
se le ha añadido la regla de la tirada de espacios. El espejo no lo mira,
porque escribe en un terminal de verdad y no en una pantalla de 32 columnas,
pero el principio es que todos los intérpretes hagan lo mismo.

## Cosas menores

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

### Y una que sigue apareciendo, en el PCW

`test_graphics_pcw` falló una vez en una vuelta entera de la suite —una lámina
con puntos distintos de los de la referencia, no una que no acabara— y pasó
tres veces seguidas al repetirla. Lo que encaja es lo que ya está escrito en
`start_code`: un PCW sin disquete sigue ocupado con el cargador que le da su
teclado, y de vez en cuando ese cargador pisa lo que se le acaba de escribir.
Los reintentos de `start_code` cubren el caso de que no arranque, no el de que
arranque con un byte cambiado. Si vuelve a salir, el remedio es el mismo que
en las demás: escribir, volver a leer lo escrito y repetir si no coincide.

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
