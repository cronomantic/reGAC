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

Cuatro opcodes siguen sin hacer nada, y los cuatro necesitaban el bucle
principal para tener dónde engancharse: la espera de tecla, la cinta, el disco
y la confirmación que pide salir.

Falta partir la línea tecleada en varias órdenes separadas por conectores. El
vocabulario de las aventuras españolas no trae los separadores en inglés que
deGAC pone por defecto, así que hay que decidir de dónde salen.

## Las máquinas

En Python están modeladas Spectrum, Sam Coupé, Next, MSX1, MSX2 y Amstrad, y
las seis dibujan las láminas igual que el Spectrum. En Z80 sólo existe el
Spectrum.

### Amstrad PCW, target nuevo

Merece la pena porque es Z80 y porque no se parece a ninguna de las otras, así
que obliga a que la separación entre intérprete y máquina sea real.

**Monocromo.** 720 por 256 píxeles y ni un color. Todo el modelo de tinta,
papel, brillo y parpadeo se queda sin sitio donde ir, y la única manera de
mostrar tonos es la trama. Es la máquina que pone a prueba de verdad que el
intérprete de láminas no sepa nada de color: hoy pide al dispositivo que fije
los colores en curso, y el del PCW tendrá que traducirlos a tramas o a nada.

**El ancho no obliga a escalar.** Con 720 de ancho cabe la lámina de 256
centrada, que es la regla que ya establecimos y que evita que los rellenos se
escapen. Si se quisiera aprovechar la pantalla, el doble exacto son 512 y sí
sería seguro, pero **doblando los píxeles del resultado, no volviendo a trazar
al doble de tamaño**: doblar píxeles conserva la lámina exactamente, volver a
trazar reabre el problema que medimos con el Amstrad.

**Memoria de sobra**, 256K o más en bloques de 16K, que encaja con el reparto
por bancos que ya tiene el formato binario.

**No hay AY.** Sólo un zumbador, así que toda la previsión de música que
condiciona el reparto de bancos no aplica aquí. La sección de música del
formato seguirá estando, vacía, y este destino no necesitará ni buffer
residente ni ranura propia.

**Por confirmar antes de escribir nada**: la disposición exacta de la memoria
de pantalla, que no es lineal ni como la del Spectrum, y cómo se lee el
teclado.

### Mirar las versiones de CPC, que es la lección para el PCW

Sergio puede conseguir las mismas aventuras en su versión de Amstrad CPC. Es la
mejor fuente que hay para el PCW, porque es el único sitio donde se ve qué hizo
el original al llevar las láminas a una máquina que no es el Spectrum.

Lo que se encuentra por ahí son imágenes de disco y de cinta, no instantáneas,
así que hay que cargarlas en la máquina que les toca y leer la memoria después.
Eso es lo que hace `grab.py`: arranca el emulador en la máquina que se le diga,
mete el medio, espera a que cargue y escribe la memoria en un fichero plano
donde la dirección de un byte es su posición.

    python grab.py --machine CPC464 juego.cdt juego.bin
    python grab.py --machine CPC6128 juego.dsk juego.bin

Está comprobado contra una instantánea de Spectrum, que se puede comparar
consigo misma: los 48K vuelven byte a byte salvo el contador de fotogramas y
los dos bytes de pila que usa la propia instantánea para arrancar. Falta
enseñar al decompilador a leer un volcado plano y a situar las tablas donde el
Amstrad las tiene, a partir de $4000, con la base de datos en $210C.

Las versiones de Amstrad ya están, en `juegos`, acabadas en `_ams.zip`: son
Megacorp, Los pájaros de Bangkok y La guerra de las vajillas, cada una en
disco y en cinta. Las dos primeras las tenemos también de Spectrum, así que la
misma aventura se puede comparar en las dos máquinas, que es justo lo que hace
falta.

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

**Nadie reescaló las coordenadas.** Son los mismos bytes en las dos máquinas,
así que el ajuste a la pantalla lo hace la máquina y no el dato. Eso respalda
centrar la lámina de 256 en los 720 del PCW.

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

De la versión de CPC quedan tres cabos:

- Los ocho bytes de cabecera de cada lámina. Se leen como las cuatro tintas,
  pero sobran tres bits por byte sin explicar.
- Megacorp está repartido de otra manera, con el intérprete en `MEGACOR1.BIN` a
  $2710 y las dos partes en $0428, así que sus tablas no están en $4000. Habrá
  que situarlas antes de poder leerlo.
- El disco de La guerra de las vajillas tiene los sectores renumerados para que
  no se copie, así que ése sí hay que cargarlo en la máquina con `grab.py`.

## Cosas menores

`deGAC` sólo lee instantáneas de Spectrum. El decompilador de referencia en C
también entiende las de Amstrad y Commodore 64, lo que ampliaría el catálogo de
aventuras recuperables.

El intérprete de Python casa palabras por prefijo, y el original y el nuestro
casan la palabra entera. Conviene alinearlo o dejar dicho por qué no.
