# Base de datos binaria

El fichero que lee el intérprete de ocho bits. La implementación está en
[`regac/binary.py`](../regac/binary.py) y se construye así:

    python -m regac build partida.json partida.rgac -m spectrum128 -b 16k

Todo va en little endian, y cada desplazamiento dentro de una sección es
relativo a esa sección. Así una sección se puede mover a un banco de memoria sin
reescribir nada de lo que tiene dentro.

## Cabecera

| Byte | Contenido |
|---|---|
| 0 | marca `RGAC` |
| 4 | versión del formato |
| 5 | máquina |
| 6 | bits de página: 14 para bancos de 16K, 13 para 8K, 0 para sin bancos |
| 7 | modo de música |
| 8 | tamaño del buffer de música, en bytes |
| 10 | número de bancos |
| 11 | número de secciones |
| 12 | directorio, cinco bytes por sección: banco, desplazamiento, tamaño |

Un banco 0xFF quiere decir que la sección es residente.

## Secciones

`config`, `vocabulary`, `objects`, `locations`, `conditions`, `text`, `font`,
`graphics` y `music`.

Los textos de toda la aventura van a un solo almacén, así que una pareja de
códigos encontrada en un mensaje sirve también para la descripción de una
localidad. Los nombres de objeto y las descripciones no se guardan con su tabla:
guardan un índice al almacén de textos. El detalle de cómo se empaqueta está en
[textos.md](textos.md).

La sección de configuración empieza con la localidad inicial, el ancho de línea
y los códigos de los diez dígitos, en ese orden y en sitio fijo, para que el
intérprete pueda escribir un número sin buscarlos. Después van los signos de
puntuación, el primero de los cuales es el espacio.

Los números de mensaje son los que el autor escribió y están llenos de huecos,
así que la sección de texto lleva una tabla de 256 bytes que traduce número de
mensaje a su sitio en el almacén. Cuesta poco y ahorra buscar.

Las condiciones usan la codificación del original, que era buena: una constante
son dos bytes con el bit alto del primero puesto, lo que deja quince bits, y
cualquier otra cosa es su opcode en un byte. Un cero termina la tabla.

## Qué es residente y qué va a bancos

Residente es lo que el intérprete toca en cualquier momento y sin aviso: el
vocabulario, las tablas de objetos y localidades, las condiciones y la fuente.
A bancos van el texto, los gráficos y la música, que se consultan en momentos
conocidos.

Una sección nunca se parte entre dos bancos, de modo que traer una a memoria
jamás necesita dos páginas mapeadas a la vez.

Medido sobre las ocho aventuras, que ocupan entre 16 y 21 KB enteras:

| Reparto | Residente |
|---|---|
| Sin bancos | 16 a 21 KB |
| Con bancos de 16K | 3,8 a 7,4 KB, más un banco |

O sea que para estas aventuras los bancos son previsión y no necesidad: caben de
sobra en un Spectrum de 48K sin paginar nada. Hacen falta para aventuras nuevas
más grandes, y para la música.

## Cómo se pagina, ya en la máquina

El intérprete pide una sección y no sabe dónde está. Si el directorio dice que
vive en un banco, `db_section` llama a `db_page`, que es de la máquina, y
devuelve una dirección dentro de la ventana; si dice que es residente devuelve
una dirección del bloque de siempre. Una máquina sin bancos no define nada y se
queda con el `db_page` que no hace nada, en el propio
[`database.asm`](../z80/common/database.asm), así que el Spectrum de 48K y el
Amstrad no pagan ni un byte por todo esto.

Lo que sí hay que cuidar es quien se guarda un puntero. El texto y las láminas
lo hacen —`text_init` y `picture_init` apuntan una vez y luego leen muchas
veces— y son justo las dos secciones que van a bancos, así que imprimir le
quita el banco a las láminas y dibujar se lo quita al texto. Por eso
`unpack_message` y `draw_picture` empiezan pidiendo el suyo con `db_bank_in`,
que no hace nada si ya está puesto. Es una comprobación por mensaje y otra por
lámina; no se nota.

En el Spectrum de 128K la ventana es la de $C000 y las páginas que se usan son
la 1, 3, 4, 6, 7 y 0, en ese orden: la 2 lleva el intérprete y la 5 la
pantalla. El byte que elige página no se puede leer, así que se guarda el
último escrito, que además es lo que permite no escribir nada cuando ya está la
que se quiere. Está en [`paging.asm`](../z80/spectrum/paging.asm).

Para que el ensamblador pueda repartir la imagen en páginas, la construcción le
deja dicho dónde empieza cada banco:

    python -m regac build partida.json game128.rgac -m spectrum128 -b 16k            --defs banks.inc

y eso escribe `DB_RESIDENT_SIZE`, `DB_BANK_COUNT` y `DB_BANK_BYTES`. Qué página
de la máquina le toca a cada banco lo dice el propio fuente de la máquina, en
[`game128.asm`](../z80/spectrum/game128.asm), que es de donde sale también la
tabla que camina `db_page`: la lista está una sola vez.

Probado con Los pájaros de Bangkok engordada con mensajes de relleno hasta que
el texto y las láminas no caben en el mismo banco. La aventura juega, describe
el cuarto —que es leer un banco— y la lámina que sale en pantalla es byte a
byte la que dibuja el renderizador de referencia —que es leer el otro—, con la
máquina paginando entre las dos. Está en
[`tests/test_banks_z80.py`](../tests/test_banks_z80.py).

## La cinta, que es lo que se entrega

Una instantánea no la carga nadie en una máquina de verdad, así que lo que
sale de la construcción es una cinta. La técnica es la de siempre y está
tomada de ChooseYourDestiny, que es donde Sergio ya la tenía resuelta: la
cinta es un programa en BASIC y detrás los bloques sin cabecera. El cargador
viaja dentro del propio BASIC, en un `REM` que es la línea 0, así que cargar
el BASIC es cargar el cargador; la línea 10 hace `CLEAR` por debajo del
intérprete y lo llama.

El cargador no hace más que recorrer una tabla: dónde va cada bloque, cuántos
bytes tiene y, en un 128, en qué página. Cada uno se lo pide a la ROM con
`LD_BYTES`, y si alguno no entra entero arranca la máquina de nuevo. La tabla
se arma en el ensamblado con lo que dice el `--defs` de la construcción, así
que un 48 tiene un bloque y un 128 tiene ése más uno por banco. Está en
[`loader.asm`](../z80/spectrum/loader.asm), y las cintas las escribe el propio
sjasmplus con `SAVETAP`.

De cada banco se graba sólo lo que ocupa y no la página entera, que para eso
el `--defs` dice también cuánto usa cada uno.

Probado cargando las dos cintas en el emulador como las cargaría una persona,
con `LOAD ""`: la de 48 y la de 128, ésta con una aventura engordada hasta
tener dos bancos, y con la lámina de la pantalla comparada byte a byte contra
la referencia, que sólo cuadra si cada bloque cayó en su página.

## La música con AY, que es lo que condiciona el diseño

El reproductor de AY corre desde la interrupción, cincuenta veces por segundo.
De ahí sale la única regla que de verdad importa en todo esto:

**El reproductor no puede leer nunca a través de una ventana de paginación que
el código principal pueda cambiar por debajo.**

Si la melodía vive en un banco y el programa pagina otro banco distinto para
sacar un texto, la siguiente interrupción lee basura y la música se rompe. Es el
fallo clásico de este tipo de intérpretes y hay que evitarlo por diseño, no
por cuidado.

La máquina que aprieta es el Spectrum de 128K, porque tiene una sola ventana
paginable, la de 0xC000. Amstrad, MSX, Sam Coupé y Next tienen varias ranuras y
pueden dedicar una a la música.

Por eso el formato lleva un campo de modo de música en la cabecera, con dos
valores:

**Copia a residente.** Al empezar una melodía se copia a un buffer residente, y
a partir de ahí el reproductor sólo lee memoria que no se pagina. El buffer se
declara en la cabecera para que el montador compruebe que cabe. Esto tiene una
ventaja que no se ve a primera vista: como la interrupción nunca toca la ventana
paginada, paginar no necesita deshabilitar interrupciones, y la música no da
ningún tirón al cambiar de localidad.

**Ranura propia.** La melodía se queda en su banco, mapeado en una ranura que el
código principal no usa nunca. Sale gratis en memoria pero sólo vale en las
máquinas con varias ranuras.

La sección de música está vacía todavía, pero con su forma ya fijada: una
cuenta, y para cada melodía dónde empieza y cuánto ocupa. Añadir melodías
después no moverá ninguna otra sección.

## Verificarlo

El lector de [`regac/binary.py`](../regac/binary.py) recorre la imagen como lo
hará la rutina en Z80, y la batería de pruebas compara lo que saca con la base
de datos de partida: textos, condiciones, objetos, localidades, vocabulario y
gráficos. Es la misma disciplina que el formato fuente: si el viaje de ida y
vuelta no es exacto, el formato está mal.
