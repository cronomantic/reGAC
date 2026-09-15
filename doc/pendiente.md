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

**Lo que queda de esta máquina**: que dibujar cuesta aproximadamente vez y
media lo que en el Spectrum —6,15 segundos contra 4,31 en la lámina más
pesada—, repartido y sin un solo sitio donde apretar.

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

**Los efectos de sonido, puestos.** Un efecto de Arkos es un instrumento suelto
que el reproductor superpone a uno de los tres canales la próxima vez que la
interrupción lo llama: pedirlo escribe cinco bytes y vuelve, la melodía sigue
por debajo con un canal menos, y cuando el efecto se acaba el canal vuelve a la
melodía. Va al canal tercero, porque las melodías de estas máquinas suelen
llevar la voz en el primero y el bajo en el segundo.

**Lo que falta**, que es todo lo que toca al intérprete:

- **Dónde vive la melodía.** Hoy se ensambla con el intérprete, que es lo que
  hace que la interrupción pueda tocarla con cualquier banco en la ventana. En
  el formato binario ya hay una sección de música reservada; cuando se use,
  tiene que quedar en la parte residente o en un banco que no se pagine nunca,
  y hay que decidir cuántas melodías caben.
- **Cómo se pide desde el fuente.** Un comando para empezar una melodía, otro
  para pararla, y otro para un efecto, con la aventura eligiendo el número. Eso
  es opcodes nuevos y sintaxis nueva.
- **Cuándo se calla sola.** Al grabar y cargar en cinta, seguro: el temporizado
  no admite interrupciones. En el Amstrad hay además un detalle que no se puede
  olvidar —el AY está detrás del mismo 8255 por el que se lee el teclado, así
  que un barrido interrumpido a la mitad lee la fila que no es. El barrido
  tendrá que llevarlas quitadas, y sólo en las versiones con música: volver a
  ponerlas donde no hay rutina sería saltar a lo que haya en el $0038.
- **Cómo la trae el autor.** Lo mismo que con las fuentes: exportar de Arkos e
  incluir. Falta decidir si la herramienta de autoría se traga el `.aks` o sólo
  el fuente ya exportado.
- **El PCW no entra en nada de esto**: no tiene AY, sólo un zumbador.

Las melodías no están en el repositorio, que no son nuestras: las pruebas
piden una en `music/` y se apartan si no hay.

## Un comando para cambiar el color de la letra

Pedido, y no hecho. La idea es tener **renglones de distintos colores**: que un
mensaje pueda decir que lo que viene detrás va en otra tinta, y que el
intérprete lo obedezca al imprimir.

Media pieza está puesta ya: el **código 1 del juego de caracteres está
reservado** para esto y no se lo lleva ninguna letra, así que puede aparecer en
mitad de un texto empaquetado sin chocar con nada. Lo que falta es lo otro:

- cómo se escribe en el fuente —lo más parecido a lo que ya hay sería una
  secuencia en el propio texto del mensaje, del estilo de `\ink 5`, que el
  compilador convierte en el código 1 y un byte de color;
- que `textout.asm` lo entienda al imprimir, en lugar de mandarlo a la pantalla
  como si fuera una letra;
- y qué significa un color en cada máquina, que es lo mismo que ya resuelven
  los dispositivos de las láminas: el Spectrum tiene tinta y papel por celda, el
  Amstrad plumas, el PCW no tiene color ninguno y el Next un byte por píxel.

Conviene decidir de paso si el cambio dura hasta el final del mensaje o hasta
que otro lo cambie, y si el papel también se puede tocar o sólo la tinta.

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
