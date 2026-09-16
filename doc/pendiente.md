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
cabecera delante, que es como lo hacía el original. Lo que viaja es sólo la
partida, de `vm_state` a `vm_state_end`: la aventura no cambia nunca, así que
no hace falta guardarla. El original sí la guardaba entera, de $5DC0 al final
de su base de datos, porque tenía el estado metido dentro.

De esos dos, en el Spectrum, no hay prueba automática: el emulador no sabe
grabar lo que sale por la cinta, así que sólo están comprobados a mano. En el
Amstrad y en el MSX sí la hay, y la mitad que se puede probar aquí también se
podría: darle una cinta de Spectrum de verdad y leer un bloque de ella, como
se hace allí.

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
descartada por el mapa y las partidas irán al disco por sectores, como en el
PCW. Hoy `disc.asm` es un tocón honesto que dice que no pudo.

El cargador es BASIC y pagina él: `OUT &7F00,&C4` y un `LOAD` por banco. De
paso, algo que costó una tarde: **los dos puntos que separan dos sentencias no
son el carácter `:` sino un `01`**. Con `3A` el `LIST` los enseña igual y BASIC
dice «Syntax error».

**Lo que gana**: las dos partes del Quijote, que no caben en un Amstrad de
sesenta y cuatro, caben en un 6128 con un banco y de sobra. Y el intérprete,
que en un 464 acaba a un palmo del firmware, ahí acaba en `$A011` con casi
ocho kilobytes libres.

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

**Las dos partes del Quijote no caben en un Amstrad**, y no es de ahora: sale
igual en el árbol de antes de todo esto. Es un agujero que estaba y que nadie
había nombrado. Lo que se puede hacer cuando toque es lo mismo que hace el +3
—repartir la base de datos en bancos, que el formato ya sabe y el 6128 tiene
memoria de sobra— o dibujar sus láminas más baratas, que en el Quijote son casi
la mitad del total.

Y hay un **escalón** que conviene saber, porque muerde sin avisar: como la base
de datos va alineada a 256, lo que importa no es cuánto crece el intérprete
sino cuándo cruza una página. Antes de los marcadores acababa en `$5F21` y
ahora acaba en `$5FDA` —185 bytes más— y **ninguna aventura ha perdido un solo
byte**, porque la base de datos sigue cayendo en `$6000`. Pero quedan **38
bytes** hasta el escalón, y el día que se crucen, las ocho pierden 256 de golpe
y megacorp2 se sale. Eso es justo lo que pasó a mitad de esta tanda: con una
tabla de separadores metida a capón el intérprete pasó de `$6000`, la base de
datos se fue a `$6100` y `regac make` dejó de construir esta máquina.

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

Queda cola, y está medida: vajillas1 #7 va a 12,2 s y quijote2 #14 a 36,5 (era
del orden de cuatro minutos). Lo que queda se va en los extremos de los trazos
y en `blocked`, que sigue preguntando punto a punto una vez por fila.

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

Lo que mide, después del arreglo que cuenta más abajo:

| aventura | la más lenta |
|---|---|
| Bangkok1 | 3,1 s |
| Bangkok2 | 6,5 s |
| megacorp1 | 3,0 s |
| megacorp2 | 3,8 s |
| quijote1 | 34,5 s |
| quijote2 | 51,6 s |
| vajillas1 | 12,3 s |
| vajillas2 | 11,2 s |

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
y no leía nadie. La otra mitad, la ventana, sólo está en dos, y no por pereza:

| máquina | la ventana | por qué |
|---|---|---|
| Spectrum | **sí** | |
| MSX | **sí** | |
| Amstrad | no | el intérprete acaba a **38 bytes** de un escalón de página que cuesta 256 a cada aventura; la ventana cuesta unos 60 |
| Next | no | el intérprete acaba en `$9FC6` y **lo que pase de `$A000` no llega a la máquina** |
| PCW | no | sus dos mitades viven en bancos distintos: la dirección de un renglón tendría que llevar un banco consigo |

En el Spectrum el desplazamiento pasó a recorrer los renglones de uno en uno,
porque el truco de un solo `LDIR` sólo vale mientras la ventana cabe en un
tercio de la pantalla. En el MSX bastaron dos bytes, el primer renglón y
cuántos se mueven. En las otras tres, `text_window_all` y `text_window_below`
están y no hacen nada, con el porqué escrito en su propio `screen.asm`.

Se ve en la presentación de MegaCorp, que es lo que lo motivó: antes se perdía
desplazada en ocho renglones y ahora sale letra por letra como la del
original. La prueba es [`test_textmode_z80.py`](../tests/test_textmode_z80.py).

**Lo que queda de aquí**, apuntado y medido y no hecho:

- **La pared de los `$A000` del Next.** El `.nex` lleva los bytes buenos en el
  banco 2 —leídos del fichero, el `$A017` es el que debe ser— y la memoria de
  la máquina ahí se lee como ceros. Quedan 58 bytes antes de esa pared y eso
  es un problema con esto y sin esto: cualquier cosa que se le añada a esa
  máquina la cruza. Es lo próximo que hay que entender del Next.
- **Un mensaje se desempaqueta en `text_buffer`, que son 256 bytes, y nadie
  comprueba que quepa.** Uno de 380 caracteres se lleva por delante la memoria
  del intérprete y la máquina se va a pasear. Ninguna de las ocho aventuras
  tiene uno tan largo, así que no ha mordido nunca, pero una aventura escrita
  de ahora en adelante sí puede. Lo suyo es que la construcción lo diga, que
  es donde se sabe.
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

- **No usar `enter-cpu-step` para escribir el PC con la máquina parada.** Cura
  la carrera, pero deja al emulador corriendo nueve veces más lento: la vuelta
  del Next pasó de 2 a 19 minutos. Lo que se hace en su lugar es preguntar otra
  vez —hasta tres intentos—, que no cuesta nada en una vuelta que va bien. La
  prueba del PCW sí lo usa, pero una vez y no en un bucle.
- **Una prueba que sigue después de un fallo así miente.** Con la máquina a
  medias, todo lo que se lee después es basura: la vuelta que encontró esto
  reportó 26 láminas mal cuando había pasado una sola cosa. Ahora para en la
  primera y dice dónde estaba el procesador, que es lo que distingue una lámina
  lenta de una máquina que no arrancó.

La prueba de las 196 del Amstrad tenía la misma carrera aunque no se la hubiera
visto saltar, y lleva el mismo remedio.
