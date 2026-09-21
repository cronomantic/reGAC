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
| 7 | reservado, a cero: fue el modo de música |
| 8 | reservado, a cero: fue el tamaño del buffer de música |
| 10 | número de bancos |
| 11 | número de secciones |
| 12 | directorio, cinco bytes por sección: banco, desplazamiento, tamaño |

Un banco 0xFF quiere decir que la sección es residente.

## Secciones

`config`, `vocabulary`, `objects`, `locations`, `conditions`, `text`, `font` y
`graphics`. La octava, `music`, ya no se escribe: su número se deja libre para
que las siete de delante conserven el suyo.

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
A bancos van el texto y los gráficos, que se consultan en momentos conocidos.

Una sección nunca se parte entre dos bancos, de modo que traer una a memoria
jamás necesita dos páginas mapeadas a la vez.

Medido sobre las ocho aventuras, que ocupan entre 16 y 21 KB enteras:

| Reparto | Residente |
|---|---|
| Sin bancos | 16 a 21 KB |
| Con bancos de 16K | 3,8 a 7,4 KB, más un banco |

O sea que para estas aventuras los bancos son previsión y no necesidad: caben de
sobra en un Spectrum de 48K sin paginar nada. Hacen falta para aventuras nuevas
más grandes.

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

## El disco

Para las máquinas que cargan de disco hay una librería propia,
[`regac/dsk.py`](../regac/dsk.py): un sistema de ficheros CP/M y la imagen que
lo contiene. La parte del sistema de ficheros sigue a la de
ChooseYourDestiny, que a su vez es un port de libdsk y mkp3fs, y por eso no
está escrita de cero.

Lo que cambia de una máquina a otra son diez valores —pistas, sectores, tamaño
de sector, pistas reservadas, tamaño de bloque, bloques de directorio y los
huecos— más desde qué número se numeran los sectores. Eso último es lo del
Amstrad: AMSDOS no guarda ningún registro de arranque, así que el formato no se
lee, se deduce de los números de sector, $C1 en un disco de datos y $41 en uno
de sistema. El +3 sí lo guarda, en el primer sector, y por eso su formato lleva
`boot`.

Comprobado de dos maneras, porque cada una pilla lo que la otra no. Ida y
vuelta contra el lector de `disk.py`, que está escrito contra discos de
Amstrad de verdad, con ficheros de todos los tamaños incómodos: uno de un
byte, uno de un registro, uno de justo los dieciséis kilobytes que cabe en una
entrada de directorio y uno de cuarenta mil. Y metiendo el disco en un 6128
emulado y haciendo que **AMSDOS mismo cargue** el fichero, que es lo único que
demuestra que el directorio es un directorio.

## El Amstrad: cómo se le entrega

Un Amstrad arranca la aventura como se arrancaban entonces: `RUN"JUEGO` en un
disco y `RUN"` en una cinta. Lo que corre es un BASIC de tres líneas —apartar
la memoria que hace falta, traer el intérprete y llamarlo— que va primero en el
medio, con el intérprete detrás. Lo hace
[`regac/media.py`](../regac/media.py), y se pide así:

    python -m regac release z80/cpc/game.bin salida/ -m cpc

El BASIC va **ya tokenizado**, que es como la máquina lo guarda en memoria. Un
listado en texto plano vale en disco, pero en cinta no hay manera; y como sólo
son tres sentencias, la tabla de tokens tiene tres entradas.

La cinta es el formato del propio firmware, en
[`regac/cdt.py`](../regac/cdt.py): cada fichero en bloques de dos kilobytes, y
cada bloque escrito dos veces, un registro de cabecera que dice qué viene y
otro con los datos. Dentro de un registro, los datos van en trozos de 256 con
dos bytes de comprobación detrás de cada uno y cuatro bytes de cola. Esa
comprobación es el CRC CCITT de siempre, complementado y con el byte alto
delante, y las duraciones de pulso están copiadas de una cinta de verdad y no
redondeadas de un manual.

Contrastado contra esa cinta: el cargador de Megacorp, leído de su propia
cinta y vuelto a escribir a partir de sus campos, sale **byte a byte igual**,
cabecera, datos, comprobaciones y cola. Y luego en la máquina: el disco arranca
el juego, y la cinta también. Lo de la cinta son minutos —veintiocho kilobytes
a la velocidad a la que el firmware los lee— así que esa prueba sólo corre con
`REGAC_SLOW=1`. Conviene saberlo antes de darla por colgada: una cinta de
Amstrad de verdad se comporta igual de lenta en el emulador.

## El +3, que arranca él solo

Un +3 con un disco dentro ofrece «Loader» como primera cosa de su menú, y lo
que Loader ejecuta es el programa BASIC llamado `DISK`. Así que ahí va el
nuestro: un `CLEAR` por debajo del intérprete, un `LOAD "GAME" CODE` y la
llamada, con el intérprete en el fichero `GAME`. Los dos llevan delante la
cabecera de ciento veintiocho bytes de +3DOS, con su marca, lo que ocupa todo
y los ocho bytes de cabecera que un Spectrum lleva desde siempre.

Los números del BASIC van escritos como `VAL "32767"`. Es el mismo número para
la máquina y se ahorra los cinco bytes de binario escondido que arrastra un
número tecleado, que son cinco bytes que se pueden escribir mal para nada.

    python -m regac release z80/spectrum/game.bin salida/ -m plus3

Y también con la base de datos repartida en bancos, que es donde se pone
interesante, porque paginar no es cosa que el BASIC pueda hacer. Ahí el
programa que corre el menú lleva dentro un cargador en código máquina
—[`loader3.asm`](../z80/spectrum/loader3.asm)— que abre un fichero sin
cabecera y lo va leyendo a trozos con `DOS READ`, diciéndole a +3DOS en qué
página va cada uno: **+3DOS pagina solo**, así que el cargador no toca el
puerto ni una vez. La tabla de bloques es exactamente la misma que lee el
cargador de cinta, en `blocks.asm`.

Antes de nada hay que pedirle a +3DOS que suelte lo suyo. De las ocho páginas
se queda la siete para él y retiene las impares para su disco en RAM y su
caché; `DOS SET 1346` es como se le dice que conserve la caché y devuelva el
resto. Lo que queda libre es la cero, la uno, la tres y la cuatro, que son las
cuatro que reparte esta construcción, y hay un `ASSERT` que para el ensamblado
si una aventura pide más.

    python -m regac build partida.json game3.rgac -m spectrum128 -b 16k            --defs banks3.inc
    python -m regac release z80/spectrum/game3_code.bin salida/ -m plus3            --boot z80/spectrum/game3_boot.bin --database z80/spectrum/game3.rgac

Las pruebas lo arrancan como lo arrancaría su dueño: enter en el menú y a
esperar. La del disco con bancos usa una aventura engordada hasta necesitar
dos, y compara la lámina de la pantalla byte a byte contra la referencia, que
sólo cuadra si cada banco acabó en su página.

## El PCW, que no tiene a quién pedirle nada

Ni ROM, ni sistema operativo, ni cargador que valga: la máquina lee el sector
de la pista 0, cara 0, registro 1, comprueba que sus 512 bytes suman $FF y
salta dentro. De ahí en adelante todo es nuestro, y lo que hay es
[`boot.asm`](../z80/pcw/boot.asm), que maneja el PD765 él mismo.

Ese sector hace tres cosas, y en este orden: monta la tabla que lee el vídeo y
enciende la pantalla —para que la de carga se vea mientras entra lo demás—,
lee las piezas que le diga su tabla, y salta a donde ésa le diga. Las piezas
son la pantalla, el intérprete y cada banco de la base de datos, y van todas
dentro de un fichero CP/M normal llamado `GAME`, para que el disco siga
teniendo un sistema de ficheros que una persona pueda leer.

La tabla vive en los últimos 64 bytes del propio sector, en $F1C0:

| bytes | qué |
|---|---|
| 0-1 | pista y registro donde empiezan las piezas |
| 2-3 | a dónde saltar cuando estén todas |
| 4... | por cada pieza: dónde va, cuántos sectores es, y en qué banco |
| 60-62 | pista, registro y sectores de la partida guardada |

**Y las partidas.** No hay a quién pedirle un fichero, así que lo hace el
constructor: un fichero CP/M de verdad, `GAME.SAV`, del tamaño justo y vacío,
y deja en la tabla dónde empieza. El intérprete —[`disc.asm`](../z80/pcw/disc.asm)—
escribe esos sectores él mismo y no toca el directorio jamás, que es lo que
permite que la partida siga siendo un fichero que las herramientas de CP/M
pueden copiar. El sector de arranque sigue en $F000 cuando el juego corre,
porque no se carga nada encima, así que la tabla se lee de ahí sin más.

El reparto de memoria del intérprete es el que ya suponían la pantalla y el
teclado: el código en los primeros 16K, la ventana de la base de datos en los
segundos, la mitad de pantalla que toque en los terceros y la máscara, los
buffers y la pila en los cuartos. Los bancos de la base de datos son del 5 en
adelante, porque del 0 al 4 los usa ese mapa.

    python -m regac build partida.json game.rgac -m pcw -b 16k            --defs banks.inc
    python -m regac release z80/pcw/game_code.bin salida/ -m pcw            --boot z80/pcw/boot.bin --database z80/pcw/game.rgac

La prueba lo hace como lo haría su dueño: esos dos comandos y encender un PCW
con el disco dentro. Arranca solo, lee lo suyo, dice lo que la aventura dice y
contesta a lo que se teclea.

## El Next, que lleva su medio dentro del ensamblador

Como en el Spectrum, el medio lo escribe el propio ensamblador: `SAVENEX` deja
un `.nex`, que es lo que carga un Next de verdad. Dentro van la pantalla de
carga —si la hay—, el banco con el intérprete, el banco con lo residente de la
base de datos y un banco por cada banco de ésta.

El reparto de memoria es lo que manda, y está lleno:

| dónde | qué |
|---|---|
| $0000 | la ventana de un banco de la base de datos, o la ROM del 48K mientras dura una grabación |
| $5C00 | libre, que es donde la ROM guarda sus variables |
| $5D00 | lo residente de la base de datos |
| $8000 | el intérprete, sus buffers y su pila |
| $A000 | la máscara con la que se rellena |
| $C000 | los dieciséis kilobytes de layer 2 que toquen |

Los bancos de la base de datos son de 16K, que aquí son dos páginas de las de
8K, y se mapean con `NEXTREG $50` y `$51`; la tabla que dice qué página es cada
banco está en [`paging.asm`](../z80/next/paging.asm) y la escribe el mismo
fichero que mete los datos ahí, para que no haya dos listas.

Una trampa que costó un rato: el fichero se ensambla con `-DSCREEN` cuando hay
pantalla de carga, y más abajo hay una línea `SAVENEX SCREEN`. Un `DEFINE` es
una sustitución de texto, así que el ensamblador ponía el valor de `SCREEN`
—nada— en medio de esa línea y luego no sabía qué era. Se guarda como otro
nombre y se deshace el primero.

    python -m regac build partida.json game.rgac -m next -b 16k            --defs banks.inc
    python -m regac make megacorp.toml -t next

## El MSX, que carga de cinta y no cabe en lo que BASIC alcanza

El intérprete corre con RAM en las cuatro páginas —la BIOS fuera— porque un
intérprete y una base de datos no caben en los 32K que ve el BASIC. Y ahí está
el nudo: lo único de esta máquina que sabe leer una cinta es la BIOS, que está
justo encima de donde tiene que ir la base de datos. De modo que la cinta se
carga en dos tiempos.

El primero lo hace la máquina: `BLOAD"CAS:",R` y nada más. Lo que entra es el
intérprete, que es un fichero binario normal —bloque de cabecera con diez $D0
y seis letras de nombre, y bloque de datos con dónde empieza, dónde acaba y
por dónde arranca—, y arranca por donde dice, que es lo primero que hay en él:
por eso [`game.asm`](../z80/msx/game.asm) pone `from_tape` delante de todo, y
el medio no necesita saber ninguna dirección.

El segundo lo hace el intérprete. Toma la máquina, y a partir de ahí, por cada
trozo de base de datos: devuelve la BIOS, lee el trozo con las rutinas de
siempre —TAPION $00E1, TAPIN $00E4, TAPIOF $00E7— en el buffer de $C000 (que
es la copia de la pantalla, que todavía no se usa), vuelve a tomar la máquina
y lo copia debajo de donde estaba la BIOS. El motor se para en cada vuelta, y
por eso cada trozo es un bloque suyo en la cinta, sin nombre y sin cabecera.

Delante de todo eso van tres bytes que dicen qué viene: el tamaño entero de la
base de datos y si trae pantalla de carga. Así no hay nada de una aventura
metido en el cargador. La pantalla, si la hay, va justo detrás de esos tres
bytes y en el mismo bloque que el primer trozo, porque no le hace falta
memoria: entra directa en el chip de vídeo según se lee.

Y por esa misma BIOS van las partidas, en la misma cinta: un bloque sin
cabecera con la partida sola, de `vm_state` a `vm_state_end`, escrito y leído
con TAPOON/TAPOUT y TAPION/TAPIN. Es el mismo baile de devolver la BIOS y
volver a tomar la máquina, y lo hace `tape.asm`; el cargador de arriba vive
aparte, en `loader.asm`, y quien dice qué página ve qué ranura es `slots.asm`.

De ahí sale una regla que cuesta cara si se olvida: **nunca se vuelve a
nuestro mapa con las interrupciones puestas**. Las rutinas de cinta las dejan
puestas al parar el motor, y una interrupción con la máquina nuestra es un
salto a $0038, que para entonces es la base de datos. Por eso
[`tape.asm`](../z80/msx/tape.asm) hace `di` detrás de cada llamada a la BIOS y
`the_machine_back` otro dentro. Lo que no hace falta devolver es la pantalla:
estas rutinas dejan el chip de vídeo como estaba, que es una diferencia con el
firmware del Amstrad y está mirado en la máquina.

    python -m regac build partida.json game.rgac -m msx
    python -m regac release z80/msx/game.bin salida/ -m msx            --database z80/msx/game.rgac

La prueba lo hace como lo haría su dueño: mete la cinta, teclea la orden y
espera. Teclearla tiene su truco, porque de las teclas que el emulador manda
no llegan ni las comillas ni los dos puntos ni la coma; lo que se hace es
dejar la orden en el buffer del teclado del propio MSX, en $FBF0, y mover los
dos punteros de $F3F8 —que es lo que lee el BASIC—, con lo que la orden es la
de verdad y la carga también.

## La pantalla de carga

Cualquiera de los destinos puede llevar una, y lo que se le da es **un volcado
crudo de la pantalla de esa máquina**: 6912 bytes en el Spectrum, que es un
`.SCR` de toda la vida; dieciséis kilobytes en el Amstrad, que es su modo 1
entero; 23040 en el PCW, que son las treinta y dos filas de 720 bytes tal y
como las lee su vídeo; y 14336 en el MSX, que es la memoria del chip de vídeo
—patrones, nombres y colores— tal cual. No se convierte nada ni se dibuja
nada: lo que se entrega es exactamente lo que la máquina enseña. Del MSX se
admite además el `.SC2` que escribe cualquier programa de dibujo de esa
máquina, que es ese mismo volcado con siete bytes de cabecera de BSAVE
delante; la cabecera se quita y ya está.

Dónde entra en cada medio:

- **Cinta de Spectrum**: un bloque más, y el primero de todos, delante del
  intérprete. El cargador no se entera de que es especial: la tabla de bloques
  lo lleva como cualquier otro. Se pide al ensamblar, con `-DSCREEN` y el
  fichero `screen.bin` junto al fuente, porque en esta máquina el medio lo
  escribe el ensamblador y no `release`.
- **Disco de +3**: un fichero `SCREEN` que el BASIC pone antes de traerse el
  intérprete; y en la versión con bancos, el primer trozo del fichero que lee
  el cargador en código máquina.
- **Amstrad**: un `JUEGO.SCR` en el disco, o el fichero de delante en la cinta,
  que el cargador mete en $C000 antes de cargar nada más.
- **PCW**: el primer trozo del fichero, y antes de leerlo el sector de arranque
  enciende el vídeo, porque en esa máquina no hay nada encendido hasta que
  alguien monta la tabla de líneas. La mitad de arriba va donde el mapa ya la
  enseña; la de abajo vive en un banco propio y entra por la misma ventana que
  la base de datos.
- **MSX**: delante del primer trozo de la base de datos y en el mismo bloque,
  porque no necesita sitio en memoria: el chip de vídeo lleva su propia
  dirección y la va subiendo sola, así que cada byte leído sale por el puerto
  según entra y la lámina se va rellenando mientras la cinta corre. Lo único
  que hace falta antes es poner los ocho registros del modo 2, que es lo que
  `vdp_setup` hace sin tocar nada más —el resto del arranque de pantalla
  necesita la fuente, y la fuente todavía no ha llegado.

        python -m regac release z80/cpc/game.bin salida/ -m cpc                --screen pantalla.scr

  El tamaño se comprueba: si no es el de esa máquina, protesta y no escribe.

Un aviso de andar por casa: los medios de todas las máquinas se llaman igual
(`juego.dsk`, `juego.cdt`), así que cada una quiere su propia carpeta de
salida. Dos `release` seguidos en la misma se pisan.

## Los dos huecos de la cabecera, y por qué siguen ahí

Los bytes 7 y 8 y la sección 8 fueron de la música. Hubo un reproductor de
Arkos que sonaba de verdad en cinco máquinas, y se quitó: lo que contaba en
memoria y en mantenimiento no lo pagaba una aventura conversacional, y el GAC
de 1986 no tenía música. Está contado en [`pendiente.md`](pendiente.md).

Lo que queda son tres huecos a cero, y **se dejan a propósito**: quitarlos
correría los números de todo lo demás y obligaría a subir la versión del
formato, que es un precio mucho mayor que tres bytes. Una base de datos escrita
antes de esto se lee hoy tal cual.

El reparto de bancos que hay ahora lo decidió aquella previsión, y se queda
como está porque es bueno por sí mismo: una sección nunca se parte entre dos
bancos, de modo que traer una a memoria jamás necesita dos páginas mapeadas a
la vez.

## Verificarlo

El lector de [`regac/binary.py`](../regac/binary.py) recorre la imagen como lo
hará la rutina en Z80, y la batería de pruebas compara lo que saca con la base
de datos de partida: textos, condiciones, objetos, localidades, vocabulario y
gráficos. Es la misma disciplina que el formato fuente: si el viaje de ida y
vuelta no es exacto, el formato está mal.
