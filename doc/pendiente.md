# Pendiente

Estado a 13 de septiembre de 2026, para retomarlo sin tener que reconstruir el
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
Amstrad sí la hay, y la mitad que se puede probar aquí también se podría:
darle una cinta de Spectrum de verdad y leer un bloque de ella, como se hace
allí.

Partir la línea en varias órdenes ya está, y de paso se aclaró de dónde salen
los separadores: de ningún sitio. GAC parte al llegar a un signo de
puntuación, y en su base de datos no hay ninguna lista de palabras que hagan lo
mismo; los ocho caracteres son fijos e iguales en las ocho aventuras, hasta el
punto de que el decompilador de referencia los usa como firma para reconocer un
GAC. Las palabras `then` y `and` que traía todo lo decompilado se las inventaba
`deGAC`, y ya no las pone.

La lista de separadores se queda en el formato como extensión, y el intérprete
la respeta: una aventura escrita de ahora en adelante puede decir que "y"
separa dos órdenes. Sin ninguna declarada, se comporta exactamente como el
original.

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
verdad— y **el MSX1 entero**, que carga de cinta.

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

**Lo que queda de esta máquina**: la pantalla de carga, que aquí tendría que
entrar en la VRAM con `BLOAD"CAS:",S` y con el modo puesto antes; probar grabar
y cargar partidas, que está escrito y no probado porque el emulador no graba
cintas; y que dibujar cuesta aproximadamente vez y media lo que en el Spectrum
—6,15 segundos contra 4,31 en la lámina más pesada—, repartido y sin un solo
sitio donde apretar.

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
