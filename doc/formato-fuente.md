# Formato fuente ReGAC (`.gac`)

Formato de texto intermedio del proyecto. Es el punto en el que una aventura
deja de ser un volcado binario y pasa a ser algo editable, versionable y
recompilable para cualquiera de las máquinas destino.

    SNA/VSF  --deGAC-->  JSON  --regac decompile-->  fuente .gac
    fuente .gac  --regac compile-->  base de datos (JSON PC, o binario Z80)

## Principios

1. **Compatible con GAC de origen.** Las condiciones se escriben con la
   sintaxis exacta del manual de Incentive: `IF ( VERB 7 AND NOUN 5 ) MESS 14
   HOLD 200 EXIT END`. Quien conozca GAC no aprende nada nuevo.
2. **Ida y vuelta exacta.** Decompilar y recompilar debe reproducir la base de
   datos original. Es la prueba de aceptación del compilador y la red de
   seguridad de todo lo demás.
3. **Extensible sin romper.** Toda característica nueva entra como directiva
   opcional. Un fuente sin directivas nuevas compila como GAC clásico.
4. **Lo que es de la aventura va en el fuente; lo que es de la máquina va en
   el fichero de proyecto.** Compresión, bancos de memoria y destino no
   ensucian el texto de la aventura. El fichero de proyecto ya existe y está
   contado en [`proyecto.md`](proyecto.md).

## Herramienta

    python -m regac decompile partida.json partida.gac
    python -m regac compile   partida.gac  partida.json
    python -m regac check     partida.json      ; verifica la ida y vuelta

## Estructura general

Fichero de texto UTF-8. Las secciones empiezan por `/` en la primera columna.
`;` inicia comentario hasta fin de línea, salvo dentro de un bloque de texto de
la aventura, donde todo es literal. Las líneas en blanco se ignoran fuera de los
bloques de texto.

### Bloques de texto

Los mensajes, los nombres de objeto y las descripciones de localidad son texto
literal. Si ocupan varias líneas se unen con un espacio; una barra invertida al
final de una línea las une sin separación ninguna. Una línea de texto que
empiece por `#`, `/`, `;` o `|`, o que sea una directiva —`.if`, `.else`,
`.end`—, se escribe precedida de `|`, que el compilador descarta.

Dentro del texto hay **comandos**, que empiezan por barra invertida:

| Comando | Qué hace |
|---|---|
| `\ink n` | lo que sigue se imprime en el color n |
| `\\` | una barra invertida de verdad |

    #14
    El dragón es \ink 2 rojo \ink 7 y está dormido.

El comando **se come los espacios que lo siguen**, como en cualquier otro
lenguaje con comandos dentro del texto, para que `rojo \ink 2 y negro` salga
con un espacio entre las palabras y no con dos.

Los colores son los dieciséis del Spectrum, los mismos que en las láminas: del
8 en adelante es el mismo color brillante. Cada máquina los entiende a su
manera —el MSX se queda con el más parecido de los suyos, el Amstrad toma el
número como una de sus cuatro plumas, y el PCW, que no tiene color, lee el
comando y sigue—, que es exactamente lo que ya hacen con los colores de una
lámina. El cambio dura hasta el siguiente, no hasta el final del mensaje.

| Sección  | Contenido                                                   |
|----------|-------------------------------------------------------------|
| `/CTL`   | Configuración de la aventura                                |
| `/VOC`   | Vocabulario: verbos, nombres, adverbios                     |
| `/MSG`   | Mensajes                                                    |
| `/OBJ`   | Objetos                                                     |
| `/LOC`   | Una por localidad, con conexiones y condiciones locales      |
| `/HIGH`  | Condiciones de alta prioridad                               |
| `/LOW`   | Condiciones de baja prioridad                               |
| `/GFX`   | Gráficos vectoriales                                        |
| `/FONT`  | Fuente redefinida                                           |
| `/MUSIC` | Las melodías que tiene la aventura                          |

### `/CTL`

    /CTL
    model    SPECTRUM
    start    5000
    width    32
    punct    "\0" " " "." "," "-" "!" "?" ":"
    sep      "then" "and"
    nothing  "Nada"

`punct` es la tabla de ocho terminadores de frase que GAC codifica en tres bits
dentro de cada palabra de texto. El primero, el nulo, marca fin de cadena.

### `/VOC`

Una palabra por línea: palabra, identificador y tipo. Los sinónimos comparten
identificador. El tipo es `verb`, `noun` o `adverb`.

    NORTE                      1  verb
    N                          1  verb

### `/MSG`

`#n` abre el mensaje; el texto va en las líneas siguientes, literal.

    #14
    La serpiente te muerde y mueres.

### `/OBJ`

    #1  weight=1  start=nowhere
    un disco metálico

`start` admite un número de localidad, `nowhere` (0) o `carried` (255).

### `/LOC`

    /LOC #1  gfx=1
    Una ancha calle de la Ciudad.
      /CONN
        NORTE        6
        ESTE         2
      /LOCAL
        IF ( VERB 2 ) MESS 63 WAIT END

En `/CONN` la dirección es un verbo, igual que en GAC, y se escribe con la
palabra en lugar del número.

### `/MUSIC`

Una melodía por línea, en el orden en que `MUSIC` las cuenta desde cero: el
fichero que exportó el tracker y qué subcanción tocar de él, que es la cero si
no se dice otra cosa.

    /MUSIC
    menu.akm.asm     0
    menu.akm.asm     1
    cueva.akm.asm

El fichero es relativo al fuente y no se lee aquí: es ensamblador, y quien lo
lee es el ensamblador. También vale nombrar el `.aks` del propio tracker, y
entonces la construcción lo exporta antes —con el exportador de Arkos Tracker,
que se busca en `tools/` o se dice en el proyecto con `music-tool`—; si no está,
la construcción lo dice y explica qué hacer en vez de pasarle al ensamblador un
fichero que no sabe leer. `regac build --music-defs music/tunes.asm` escribe el
fuentecillo que los incluye a todos con la forma que cada máquina necesita —la
lista por un lado y las melodías por otro, cada una en su `MODULE` y ensamblada
para el buffer—, y un fichero nombrado dos veces se incluye una sola vez y se
apunta dos: para eso son las subcanciones.

### `/HIGH`, `/LOW`, `/LOCAL`

Una condición por línea, terminada en `END`. La sintaxis es la del manual. El
bytecode es una máquina de pila postfija, pero el fuente se escribe en la forma
prefija e infija original y el compilador reordena. Los 64 opcodes, su forma y
el tipo de sus operandos están en [`regac/opcodes.py`](../regac/opcodes.py),
que es la única fuente de verdad del lenguaje.

GAC no tiene precedencia de operadores: evalúa estrictamente de izquierda a
derecha. Por eso el operando de un operador prefijo no es voraz, y `NOT VERB 1
AND NOUN 2` niega sólo la comprobación del verbo. Cuando el operando derecho de
un operador infijo es a su vez una expresión infija, va entre paréntesis.

Alguna aventura original deja valores apilados que nunca consume. El
decompilador los escribe como un número suelto en el lugar en que se apilaron,
para no alterar el código al recompilar.

### `/GFX`

    #1
      PAPER 5
      LINE 128 159 128 79
      CALL 1000

### `/FONT`

La tipografía de la aventura, entera o letra a letra.

**Entera**: `file` dice dónde está, relativo al fuente, y qué es se averigua
mirándola.

    /FONT file="letras.bin"
    /FONT file="hoja.png" layout=latin1
    /FONT file="charset.64c" order=c64

Lo que sabe reconocer:

| | |
|---|---|
| volcado normal | ocho bytes por carácter; 768 son los noventa y seis desde el espacio —la forma en que viene la fuente de un Spectrum—, 1024 y 2048 son ciento veintiocho y doscientos cincuenta y seis desde el cero |
| con dirección de carga | dos bytes delante, que es como viaja un charset de C64 |
| con cabecera de AMSDOS o +3DOS | los 128 bytes que esos sistemas ponen a todo |
| fuente de consola | las dos cabeceras de PSF |
| PNG | las letras en una rejilla de celdas de ocho por ocho, leídas como se lee una página; es tinta todo lo que sea más oscuro que la mitad, así que da igual en qué dos colores esté dibujada |
| escrita como fuente | una cabecera de C o un listado de ensamblador —Z80, 6502, x86, 68000—, que es como se publican las mismas fuentes para que las use un programa |
| BDF | el formato estándar de fuentes de mapa de bits, y el único que dice por sí mismo qué carácter es cada glifo |
| VDU 23 | la ristra de órdenes con que se redefine un carácter en un BBC Micro: el 23, el carácter y sus ocho filas |
| BASIC con `SYMBOL` | lo mismo en un Amstrad CPC, que es como viene su fichero en estas colecciones |
| fuente de consola | las dos cabeceras de PSF, tomando los glifos y no la tabla de significados que va detrás |
| RS-DOS | el envoltorio de cinco bytes delante y cinco detrás de un CoCo |

De un listado se coge lo que va en las líneas con una directiva de bytes —`db`,
`defb`, `.byte`, `dc.b`— y, si no hay ninguna, lo que está entre llaves; entre
las dos cosas queda fuera el tamaño de `font[768]` y la dirección de un `org`.
Los comentarios se quitan **antes** de buscar las llaves, y no es un detalle:
estos listados ponen en un comentario la letra que dibuja cada fila, así que la
línea de la llave abierta tiene una llave abierta.

**Probado con una fuente de verdad.** De un ZIP de
[ZX Origins](https://damieng.com/typography/zx-origins/) entran, dando todos la
misma letra: el `.ch8` de Spectrum, el `.fnt` de Atari con `order=atascii`, el
`.64c` de C64, el `.psf`, los cinco listados de `Source`, el `.bbc`, el `.bas`
del Amstrad, el `.bdf`, la hoja del GameBoy con `first=32` y hasta la imagen de
muestra con `layout=ascii`. Quedan fuera el `.bin` de C64 —que son dos fuentes
en un fichero, y hay que decir con `first=` cuál— el `.CHR` del CoCo, cuyo
orden no conozco, y el `.fzx`, que es proporcional.

**Cada letra se identifica por su casilla**, y para eso está `layout`, que dice
de una vez por dónde empieza la hoja y cuántas casillas tiene:

| `layout` | casillas |
|---|---|
| `ascii` | 96, del espacio al símbolo de copyright |
| `latin1` | 256, Latin-1 entero |
| `latin1-high` | 96, sólo la mitad de arriba de Latin-1, que es donde están los acentos |

**Dibuja la hoja en Latin-1.** Todas las letras que esto imprime están ahí, en
el sitio donde las pone cualquier editor de fuentes, así que el artista no
tiene que oír hablar jamás de los códigos de reGAC: dibuja la `á` donde Latin-1
guarda la `á` y cae donde le toca. Una hoja de Latin-1 son 16 por 16 casillas,
y las casillas en blanco no son ninguna letra: se componen o se quedan como
estaban.

Saber cuántas casillas hay tiene una segunda ventaja, y es la que hace que esto
sirva de verdad: **una hoja dibujada en grande se lee igual**. Nadie dibuja a
ocho píxeles por letra; si la hoja está al doble o al triple, el número de
casillas dice cuál de las dos cosas es, en vez de leerla como cuatro o nueve
veces más letras.

`first` dice qué carácter es la primera casilla cuando no hay `layout`, y
`order` en qué orden están, para las máquinas que no usan el del ASCII: `c64`
guarda `@ABC...` en el cero y `atascii` pone la puntuación delante. Sin
`order`, tal cual.

**Letra a letra**: ocho bytes en hexadecimal por carácter, con el glifo como
comentario. Ganan sobre el fichero, así que se puede cambiar una letra sin
volver a dibujar el resto, y los caracteres en blanco se omiten. Un carácter se
nombra por su número o por sí mismo:

    /FONT chars=128
    #65    00 3C 42 42 7E 42 42 00   ; A
    #"Ñ"   18 00 7E 63 63 63 63 00

La tabla crece sola hasta donde llegue el carácter más alto que se dibuje, así
que para poner una Ñ propia no hay que declarar nada aparte. Y lo que el autor
dibuja se usa tal cual: encima de un glifo dibujado no se compone nada.

## Caracteres latinos, que ya están

El fuente es UTF-8 y se puede escribir en él lo que se escribe en español: «La
señora Muñoz te miró con desdén», «¿Qué año es?». No hace falta declarar nada.

Cómo funciona, que es lo que hace que no haga falta declarar nada: **el juego
de caracteres es fijo y el mismo en todas las aventuras**. Debajo del espacio
van las letras que el ASCII no tiene —las acentuadas, la ñ, la ç, los signos de
apertura— y del 32 al 127 va el ASCII tal cual, con lo que el código de una
letra corriente es su propio ASCII. Del 128 para arriba es del compresor,
siempre. Una ñ cuesta lo que cuesta una n y no le quita nada a nadie: el reparto
está en [`textos.md`](textos.md). Aquí es donde se rompe con el original, que
empaquetaba los caracteres en siete bits y usaba el octavo para marcar fin de
palabra: ahí no cabía ni un acento.

**Los glifos no están dibujados a mano.** Una letra acentuada es la letra de la
propia aventura con una marca encima, para que se parezca a la tipografía en la
que está; lo único que hay guardado son las cinco marcas. Unicode dice qué
letra y qué marca —NFD parte la á en a y acento, la ñ en n y tilde—, y dónde
cabe la marca sale de la letra: una minúscula ocupa las filas dos a seis y le
sobran dos arriba, una mayúscula ocupa de la cero a la seis y se baja una fila,
que la de abajo siempre está libre. La ¿ y la ¡ son la ? y la ! del revés, que
es exactamente lo que son. Está en [`regac/glyphs.py`](../regac/glyphs.py).

**Al vocabulario se le caen las marcas.** Ningún teclado de estas máquinas
tiene tecla de acento, así que un vocabulario que dijera ARAÑA no lo podría
escribir nadie: en el binario se guarda ARANA, y el jugador escribe ARANA. Sólo
a las palabras que el parser compara; el texto conserva todas sus marcas,
porque el texto se imprime y no se teclea. Si dos palabras se quedan en la
misma —PEÑA y PENA—, la construcción lo dice en vez de dejar que la segunda no
se alcance nunca.

Lo que no está en la tabla no se puede usar, y la construcción lo dice con el
carácter en la mano en lugar de imprimir un hueco. Caben el castellano entero,
las minúsculas acentuadas de catalán, portugués e italiano, y los signos.

La directiva `charset` se sigue aceptando para que los fuentes escritos antes
compilen, y hoy no elige nada; el día que haga falta un alfabeto que no cabe
—el francés, por ejemplo— será ella la que elija cuáles son los treinta que van
debajo del espacio.

## Compresión de textos, que también

Siempre. No es decisión de nadie: el texto se comprime por pares —el par de
códigos más frecuente se sustituye por un código libre, una y otra vez— y la
tabla se genera, nunca se escribe a mano. En Megacorp el texto queda en el 46%
de lo que ocupaba. Desempaquetar es una búsqueda en tabla y una pila pequeña, y
cada mensaje se desempaqueta solo, sin tocar los de antes, que es lo que el
intérprete necesita para imprimir el 137 y nada más. Está contado en
[`regac/text.py`](../regac/text.py).

## Lo que es sólo para algunas máquinas

Una aventura es un fuente y cinco máquinas, y de vez en cuando las cinco no
quieren lo mismo. Un Spectrum de 48K puede tener que quedarse sin lo que en las
demás cabe, las plumas del Amstrad no son los colores del Spectrum, y a una
máquina sin chip de sonido no le hace falta la línea que arranca una melodía.
Para eso el fuente puede **guardarse líneas**:

    #14
    El mando hace un ruido seco    .if cpc msx
     y ya esta.
    .else
     y la pantalla parpadea.
    .end

Se resuelve **al leer el fuente**, no al jugar: lo que una máquina no va a
tener no llega nunca a su base de datos, que es justo la gracia en las máquinas
donde lo que se acaba es el sitio. Vale en cualquier sitio —una sección entera,
una entrada, una línea de la tabla de condiciones, una palabra del
vocabulario—, porque trabaja sobre líneas antes de que nada más las mire, y se
puede anidar.

Se puede nombrar la máquina y la familia a la que pertenece:

| familia | máquinas |
|---|---|
| `spectrum` | `spectrum48`, `spectrum128`, `plus3` |
| `amstrad` | `cpc`, `pcw` |
| `msx` | `msx`, `msx2` |

y sueltas quedan `next` y `sam`. Un nombre que no exista es un error y se dice:
una errata que se lleve por delante media aventura en silencio es lo peor que
podría pasar aquí. Lo mismo un `.if` sin cerrar, un `.else` suelto o un `.if`
sin máquinas.

Un fuente con condicionales **hay que leerlo para una máquina**: `regac compile
partida.gac partida.json -m cpc`. `regac make` lo hace solo, una vez por cada
máquina que construye. Un fuente sin condicionales es el mismo para todos y no
hace falta decir nada.

Las líneas que se quedan fuera no se borran: se vacían, para que cualquier
error que venga después siga contando las líneas como las escribió el autor.
Y una línea vacía dentro de un bloque de texto no es un espacio —sí lo es una
línea con un espacio, que alguna aventura de las ocho tiene—.

## Extensiones previstas

Estas dos no están implementadas. Se listan aquí para que el diseño actual no
las bloquee.

**Nombres simbólicos.** `.def PUERTA_ABIERTA 5` permitirá escribir
`SET? PUERTA_ABIERTA`. El decompilador seguirá emitiendo números.

**Inclusión de ficheros.** `.include "comun.gac"` para compartir vocabulario y
condiciones de baja prioridad entre aventuras, el equivalente al fichero de
comienzo rápido `QS.ADV` de GAC.
