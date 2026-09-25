# Manual de reGAC

Esto y [`gac.md`](gac.md) son todo lo que hace falta. Entre los dos está el
camino entero: qué instalar, cómo se escribe una aventura, cómo se comprueba y
cómo se construye para nueve máquinas.

Lo demás que hay en `doc/` son **diarios de desarrollo** —lo que se midió, en
qué orden y por qué— y no sirven de referencia.

---

## 1. Qué es esto

Una aventura conversacional al estilo del **Graphic Adventure Creator** de
1986, escrita en un fichero de texto, que se publica con un solo comando en:

| máquina | lo que sale |
|---|---|
| Spectrum 48 | cinta `.tap` |
| Spectrum 128 | cinta `.tap` |
| Spectrum +3 | disco `.dsk` |
| Amstrad CPC 464 | cinta `.cdt` |
| Amstrad CPC 6128 | disco `.dsk` |
| Amstrad PCW | disco `.dsk` que arranca solo |
| MSX | cinta `.cas` |
| Spectrum Next | `.nex` |
| PC con CGA | `.EXE` de DOS |

Se puede empezar de cero o **partir de una aventura que ya existe**: hay un
decompilador que saca a fuente legible lo que hay dentro de una cinta, un
disco o una instantánea de 1986.

---

## 2. Lo que hace falta

- **Python 3.11 o más nuevo.** Desde el 3.11 la biblioteca estándar lee TOML,
  que es lo que usan los ficheros de proyecto.
- **`sjasmplus` en `tools/`**, que ensambla los intérpretes. Sin él se puede
  escribir y comprobar una aventura, pero no construirla.
- **NASM en `tools/` o en el PATH**, sólo para el PC, que es 8086 y no Z80.
  Es un zip de algo más de medio mega en nasm.us; basta con `nasm.exe`.
- **ZEsarUX en `tools/`**, sólo para correr el banco de pruebas, y
  **DOSBox-X** en el PATH para las del PC.

`tools/` es donde va **todo programa que no es de este proyecto**, y no
entra en el repositorio: además de esos dos están ahí los decompiladores
de referencia con los que se compara lo nuestro y los emuladores que se
usan a mano. Nada de la raíz del proyecto hace falta para trabajar salvo
lo que el repositorio ya trae.

Todo se llama con `python -m regac`, **desde la raíz del proyecto**. Desde otra
carpeta dirá `No module named regac`; los ficheros que le pases sí pueden
estar donde quieras.

O se instala como orden, **desde el propio repositorio**, y entonces vale
`regac` a secas desde cualquier carpeta:

    poetry install          # o bien: pip install -e .

Se instala apuntando al repositorio y no copiándolo, porque los intérpretes
con los que construye son las carpetas de al lado, `z80/` y `x86/`: por eso no
está en PyPI.

---

## 3. En cinco minutos

Hay una aventura de ejemplo, **El faro de Santa Bárbara**: cinco salas, cuatro
objetos y un enigma, comentada de arriba abajo para leerse como un tutorial.

    python -m regac make ejemplo/faro.toml

Construye las nueve máquinas y las deja en `ejemplo/salida/`, una carpeta por
destino. Cárgala en el emulador que tengas y ya está jugando. Con `--zip
faro.zip` las mete además en un zip, igual que en el disco, para repartirlas.

Y para verla sin emulador ninguno:

    python -m regac compile ejemplo/faro.gac faro.json
    python runGAC.py faro.json

---

## 4. Las dos mitades

Una aventura son **dos ficheros**:

- **`faro.gac`** es *lo que la aventura es*: salas, objetos, palabras,
  mensajes, condiciones y láminas. No dice nada de a qué máquina va.
- **`faro.toml`** es *a dónde va*: qué máquinas, con qué pantalla de carga, a
  qué tamaño las láminas, cómo se reparten los bancos.

**Lo que es de la aventura va en el fuente; lo que es de la máquina va en el
proyecto.** Un fuente se lleva a una máquina nueva sin tocarlo.

El proyecto del faro entero:

    name   = "faro"
    source = "faro.gac"
    output = "salida"

    [targets.spectrum48]
    [targets.spectrum128]
    [targets.plus3]
    [targets.cpc464]
    [targets.cpc6128]
    [targets.msx]
    [targets.next]
    [targets.pcw]
    [targets.pc]

Cada destino puede llevar lo suyo:

    [targets.spectrum128]
    screen = "carga.scr"        # pantalla de carga
    scale  = "2x"               # a qué tamaño se dibujan las láminas

---

## 5. El ciclo de trabajo

Escribir, comprobar, construir. Las comprobaciones son rápidas y no piden
ensamblador:

    python -m regac compile  faro.gac faro.json     # ¿está bien escrito?
    python -m regac check    faro.json              # ¿apunta a algo que no existe?
    python -m regac checkgfx faro.json -m cpc       # ¿se sale alguna lámina?
    python -m regac text     faro.json              # ¿cuánto ocupan los textos?
    python -m regac render   faro.json laminas/     # las láminas como PNG
    python -m regac draw     faro.gac 1             # una lámina, en vivo
    python -m regac lint     faro.gac               # ¿sobra algo?
    python -m regac map      faro.gac mapa.svg      # el mapa
    python -m regac play     faro.gac solucion.txt  # ¿se puede ganar?
    python -m regac make     faro.toml              # construir

**`compile`** convierte el fuente en la base de datos y se queja de lo que no
entienda, diciendo fichero, línea y columna. **`check`** comprueba que la base
de datos sobrevive a una vuelta entera —decompilar lo compilado y volver a
compilarlo da lo mismo— y que nada apunta a una sala, un objeto o un mensaje
que no exista. **`text`** dice lo que ocupan los textos empaquetados, que es
lo que decide si una aventura cabe en un 464.

**`lint`** mira lo contrario que `check`: lo que está y nada usa. Una sala a
la que no lleva ninguna salida ni ningún `GOTO`, un objeto que nada puede
coger, una palabra por la que no pregunta ninguna condición, un mensaje que
nadie imprime, una lámina que no enseña ninguna sala, una tabla `/PROC` que no
corre ningún `DO`. No impide construir, y algo puede ser a propósito —un
decorado que no se coge—: son avisos. Si un número se calcula al jugar
(`MESS ( RAND 3 + 10 )`), no se puede seguir, y en vez de avisar en falso lo
dice.

**`map`** dibuja el mapa en SVG, que abre cualquier navegador: las salas en
una rejilla según la brújula —NORTE, SUR, ESTE, OESTE y las cuatro de en medio,
leídas en el vocabulario—, una línea donde se puede ir y volver, una flecha
donde sólo se puede ir, y lo que no es brújula —SUBE, ENTRA— como una flecha
curva con su palabra. La sala de salida va con el borde grueso.

**`play`** juega un fichero de órdenes, una por línea, con el intérprete de
Python, escribe lo que dice la aventura y acaba con 0 si la partida termina
—y, con `--expect`, si ha dicho eso— y con 1 si las órdenes se acaban con la
aventura aún preguntando. Guardar la solución junto a la aventura y jugarla
después de cada cambio es una prueba que no pide máquina ninguna. La del faro
está en `ejemplo/solucion.txt`:

    python -m regac play ejemplo/faro.gac ejemplo/solucion.txt --expect "Fin de la aventura"

Para escribir, **`editors/vscode/`** es una extensión de VS Code que colorea
el fuente: secciones, directivas, condiciones, órdenes de dibujo y los
comandos del texto. Se instala copiando la carpeta a `.vscode/extensions/`, en
la carpeta del usuario, y reiniciando VS Code.

Para probar sin arrancar una máquina:

    python runGAC.py faro.json          # en el terminal
    python runGAC_pygame.py faro.json   # con una pantalla como la del Spectrum

Los dos juegan la aventura entera, `SAVE` y `LOAD` incluidos. Una máquina
guarda en la cinta o en el disco y no pregunta nada; aquí un fichero necesita
nombre, así que se pide uno, y lo que se escribe es un JSON que se puede
abrir y mirar. **No es el mismo fichero que guarda una máquina**, ni podría
serlo: el bloque del Z80 lleva dentro direcciones de su propia memoria.

---

## 6. El fuente, bloque por bloque

Fichero de texto **UTF-8**. Las secciones empiezan por `/` en la primera
columna. `;` abre un comentario hasta el fin de línea, salvo dentro de un
texto de la aventura, donde todo es literal.

### Los textos

Los mensajes, los nombres de objeto y las descripciones son texto literal.
Varias líneas se unen con un espacio; una barra invertida al final las une sin
separación. Una línea de texto que empiece por `#`, `/`, `;` o `|`, o que
parezca una directiva, se escribe precedida de `|`, que el compilador
descarta.

Dentro del texto hay comandos, con barra invertida:

| | |
|---|---|
| `\ink n` | lo que sigue **de este mensaje** se imprime en el color n |
| `\\` | una barra invertida de verdad |

    #14
    El dragón es \ink 2 rojo \ink 7 y está dormido.

El comando **se come los espacios que lo siguen**, para que no salgan dobles.
Los colores son los dieciséis del Spectrum; cada máquina los entiende a su
manera y el PCW, que no tiene color, lee el comando y sigue.

**El cambio dura hasta el final del mensaje** y no más: el siguiente empieza
otra vez en blanco. Así no hace falta devolver la tinta antes de acabar, y un
mensaje no puede teñir la descripción de la sala que venga detrás.

Y hay **huecos**: algo que sólo se sabe al escribirlo, y se escribe donde
está.

| | |
|---|---|
| `\ctr n` | lo que vale el contador n |
| `\obj n` | el nombre del objeto n |
| `\turns` | los turnos jugados |

    #15
    Llevas \ctr 0 puntos y \turns turnos, y en la mano \obj 3.

Un hueco es texto: forma parte de la palabra en la que está, así que `\obj 3.`
no se separa de su punto al partir la línea, y **los espacios que lo siguen se
quedan**, al revés que con `\ink`. Valen en los mensajes, en las salas y en
los nombres de objeto; un nombre puede llevar un contador pero no otro nombre,
que podría ser el suyo, y eso no se construye. El número va escrito, no con un
nombre de `.def`.

### `/CTL` — la configuración

    /CTL
    model    SPECTRUM
    start    5000
    width    32
    ink      4
    punct    "\0" " " "." "," "-" "!" "?" ":"
    sep      "THEN" "AND"
    nothing  "Nada"

`punct` son los ocho terminadores de palabra que GAC codifica en tres bits
dentro de cada palabra de texto; el primero, el nulo, marca fin de cadena.

`sep` son las palabras que parten una línea en dos órdenes, y son **todas** las
que hay: el intérprete no sabe ninguna por su cuenta. Se comparan como palabra
entera —`ANDAR` no es `AND` con cola—. Sin `sep`, sólo parten los signos de
`punct`.

`nothing` es la palabra para «nada», que es lo que escribe `LIST` cuando no
encuentra ningún objeto.

`ink` es **el color de todo el texto de la aventura**, uno de los dieciséis
del Spectrum. Cada mensaje empieza en él y vuelve a él al acabar, de modo que
un `\ink` dentro de un mensaje tiñe una palabra y no el resto de la partida.
Si no se dice, cada máquina usa el suyo —blanco en Spectrum, Next y MSX; la
pluma dos en el Amstrad— y el PCW, que no tiene color, lo ignora. El cero no
vale: en todas estas máquinas es el papel, y texto del color del papel no se
ve.

### `/VOC` — el vocabulario

Una palabra por línea: palabra, número y tipo. Los sinónimos comparten número.
El tipo es `verb`, `noun` o `adverb`.

    /VOC
    NORTE   1  verb
    N       1  verb
    LLAVE   2  noun

### `/MSG` — los mensajes

`#n` abre el mensaje y el texto va en las líneas siguientes.

    /MSG
    #14
    La serpiente te muerde y mueres.

### `/OBJ` — los objetos

    /OBJ
    #1  weight=1  start=nowhere
    un disco metálico

`start` admite un número de sala, `nowhere` (0) o `carried` (255).

### `/LOC` — las salas

    /LOC #1  gfx=1
    Una ancha calle de la Ciudad.
      /CONN
        NORTE        6
        ESTE         2
      /LOCAL
        IF ( VERB 2 ) MESS 63 WAIT END

En `/CONN` la dirección es **un verbo**, escrito con la palabra en lugar del
número. `/LOCAL` lleva las condiciones de esa sala.

### `/HIGH` y `/LOW` — las condiciones

Una condición por línea, terminada en `END`. Los opcodes, todos, están en
[`gac.md`](gac.md).

    /HIGH
    IF ( CTR 126 = 0 ) MESS 1 SET 5 END

Lo que se repite en varias salas se escribe una vez, en una tabla con
número, y se llama con `DO`:

    /LOW
    IF ( VERB VERBO_MIRA ) DO DESCRIBE_EL_MAR END

    /PROC #DESCRIBE_EL_MAR
    IF ( AT SENDERO ) MESS EL_MAR END
    IF ( AT ESCALERA ) MESS NADA_QUE_VER END

Corre como si estuviera escrita donde está el `DO`: si dentro hay un `WAIT`,
el turno se acaba ahí. El detalle, en [`gac.md`](gac.md).

GAC **no tiene precedencia**: evalúa estrictamente de izquierda a derecha. Por
eso el operando de un operador prefijo no es voraz, y `NOT VERB 1 AND NOUN 2`
niega sólo la comprobación del verbo. Cuando el operando derecho de un
operador infijo es a su vez infijo, va entre paréntesis.

### `/GFX` — las láminas

`#n` abre una lámina y las órdenes van debajo. Los comandos de dibujo, todos,
están en [`gac.md`](gac.md).

    /GFX
    #1
      PAPER 5
      LINE 128 159 128 79
      CALL 1000

Para dibujar, **`regac draw`** abre la lámina en una ventana y la vuelve a
pintar cada vez que se guarda el fuente, así que se escribe en el editor y se
mira al lado:

    python -m regac draw faro.gac 1 -m cpc

Sale como la enseña esa máquina —`spectrum`, `cpc`, `msx`, `pcw`, `next` o
`cga`, que es la del PC—, y la `m` pasa a la siguiente. Las flechas la
recorren orden a orden (con mayúsculas de diez en diez, con control de cien
en cien), y lo que acaba de poner la última orden sale en magenta: un relleno
que se escapa por un hueco dice por dónde. Lo que llama `CALL` se recorre
dentro, en su sitio. Abajo pone la orden de antes y la de después, y **dónde
está el ratón en las coordenadas de las órdenes**, `x` desde la izquierda e
`y` desde abajo, que es lo que hay que escribir. Re Pág y Av Pág cambian de
lámina. Si el fuente guardado tiene un error, lo dice y deja la última lámina
buena.

Y **se dibuja en ella**, con el ratón, y lo dibujado se escribe en el fuente
en el acto, como una línea más de la lámina:

| tecla | qué hace un clic |
|---|---|
| `l`, `r`, `e` | una recta, un rectángulo o una elipse: dos clics |
| `p`, `f`, `b`, `s` | un punto, `FILL`, `BGFILL` o `SHADE`: un clic |
| `v` | mover: se arrastra un punto de una orden, marcado con un cuadrito |

Una orden nueva va **detrás de la orden en la que está el cursor**, y no al
final: con las flechas se vuelve atrás y se mete una recta antes de un relleno,
que es lo que decide hasta dónde llega. Enter deja escribir una orden a mano
(`INK 3`, `CALL 10`), Supr quita la orden del cursor, Ctrl+Z deshace, `g`
ajusta los clics a las esquinas de las celdas de ocho, y el botón derecho o Esc
sueltan lo que se estaba dibujando.

Se escribe como lo escribiría una persona: una línea que entra, sale o cambia,
con la sangría de las de al lado, y el comentario del final de una línea se
queda. Un punto arrastrado reescribe los números de su línea, y **un nombre de
`.def` que hubiera ahí pasa a ser número**. El fuente puede estar abierto a la
vez en el editor de texto. No escribe en una lámina que está en otro fichero
—traído con `.include`: se abre ése— ni en una que guarda líneas para algunas
máquinas con `.if`, que se retoca a mano; y lo que se dibuja pertenece a la
lámina que se está mirando, aunque el cursor esté dentro de otra que ella
llama.

Para **calcar**, una imagen encima de la lámina, vista a medias:

    python -m regac draw faro.gac 1 --trace boceto.png
    python -m regac draw faro.gac 1 --trace bocetos/

Un fichero va encima de todas las láminas; una carpeta, la que se llame como
el número de la lámina (`12.png`, `12.jpg`), que cambia sola al pasar de
lámina. La imagen se hace tan grande como quepa **sin deformarse**, y se
centra. `t` la esconde y la enseña, y `+` y `-` dejan ver más o menos de ella.

### `/FONT` — la tipografía

Entera, con `file`, o letra a letra.

### `/SOUND` — los ruidos

Uno por línea, en el orden en que `SOUND` los cuenta **desde uno**:

    /SOUND
    ; tono  pasos  paso  de dónde
       200    150     -1          ; cogido
       250    100      0  both    ; una puerta
        30    110      2  noise   ; una caída

El **tono** es lo que dura medio ciclo —más grande, nota más grave—, los
**pasos** son cuántas veces se repite y el **paso** lo que se suma al tono en
cada uno.

La cuarta columna es **de dónde sale**, y se puede dejar en blanco: `tone` es
una nota, `noise` el silbido que hace el chip sin nota ninguna, y `both` las
dos cosas a la vez. Una puerta, una caída o un aviso no son notas, y un chip
tiene con qué decirlo. **El Spectrum 48 no**, y allí la palabra se lee y se
toca el tono —que es lo más parecido que hay—, así que usarla no deja ninguna
máquina fuera: sólo suena mejor donde hay con qué.

**Suenan por el chip de sonido en las seis máquinas que lo tienen** —128, +3,
Amstrad, MSX y Next— y por el altavoz de un bit en el Spectrum 48 y en el PC,
que no tienen chip. Son dos motores y **una sola tabla**: un tono es medio ciclo
del altavoz y la mitad de eso como periodo del chip, así que `SOUND 2` dura lo
mismo y suena a lo mismo en las ocho —en el PC, contado en el reloj del
sistema y no en el procesador, que puede ir a cualquier velocidad—. Donde hay chip se gana una nota más
limpia y que no se toque lo que comparte puerto con el altavoz —el borde en el
Spectrum, el motor del casete y el led de mayúsculas en el MSX—.

Una aventura que no diga nada aquí se queda con los cinco que trae el
intérprete, y el PCW, que no tiene con qué sonar, lee la orden y sigue.

---

## 7. Tres cosas que ahorran trabajo

### Nombres para los números

    .def PUERTA_ABIERTA   5
    .def BIENVENIDA      14

A partir de ahí el nombre vale **donde valdría el número**: en una condición,
en una conexión, como número de mensaje o de sala (`#BIENVENIDA`, `/LOC
#CALLE`), en `start`, en los atributos de un objeto y en los argumentos de una
orden de dibujo. El valor puede ser decimal, hexadecimal (`0x0A`) u otro
nombre ya definido.

### Incluir ficheros

    .include "comun.gac"

Para compartir entre las dos partes de una aventura, o entre dos aventuras, lo
que no cambia. La ruta se cuenta desde el fichero que incluye, y un error
dentro de un incluido dice **ese** fichero y su propia línea.

### Líneas que sólo son de algunas máquinas

Con `.if`, `.else` y `.end` una parte del fuente existe sólo para los destinos
que se digan, que es como se ajusta lo que no cabe igual en todas.

---

## 8. Partir de una aventura que ya existe

    python deGAC.py juego.sna juego.json        # de una instantánea
    python disk.py  juego.dsk                   # de un disco de Amstrad
    python grab.py  ...                         # cargándola en su máquina

**`deGAC.py`** reconoce por sí solo una instantánea de Spectrum, una de CPCEMU
y una de VICE; a una imagen plana de memoria hay que decirle de qué máquina
viene con `-m`. De ahí a fuente legible:

    python -m regac decompile juego.json juego.gac

**`disk.py`** lee un fichero de una imagen de disco de Amstrad, o una aventura
entera de una hecha para no poder copiarse. **`grab.py`** carga un medio en su
máquina y escribe lo que dejó en memoria.

Una aventura de **Amstrad** no guarda su letra: el GAC de Amstrad escribía con
la del firmware, que está en la ROM de la máquina y no es nuestra. `deGAC.py`
le pone **Modern DOS 8x8**, la letra de la CGA de Jayvee Enaguas, que es de
dominio público (CC0), y lo dice. Lo mismo a una de Spectrum que escribiera
con la letra de la ROM. Sin eso, imprimirían en blanco en todas las máquinas.

---

## 9. Las máquinas, y lo que cada una tiene de suyo

- **Spectrum 48 y 128.** El 128 reparte el texto y las láminas en páginas
  propias, y así le caben aventuras que no caben en el 48; y tiene chip de
  sonido, así que los ruidos y el clic de tecla salen por él. El 48 es la
  única máquina que los hace con el altavoz.
- **Spectrum +3.** Disco, con el cargador en el menú de la máquina.
- **Amstrad CPC 464.** El más justo: sin bancos, y la base de datos en un
  trozo seguido. Si una aventura no cabe de la manera normal, `regac` **la
  construye sola del revés** —el intérprete debajo de `$4000` y la base de
  datos encima— y lo dice al construir. Es también la única donde la tabla de
  ruidos sólo viaja si la aventura pide alguno: son ciento cuatro bytes en la
  máquina que los cuenta uno a uno. El clic de tecla viaja siempre.
- **Amstrad CPC 6128.** Disco y bancos: aquí caben las grandes.
- **Amstrad PCW.** Disco que arranca solo, sin CP/M. Monocromo, 64 columnas.
- **MSX.** Cinta, y la máquina entera en RAM.
- **Spectrum Next.** `.nex`, en layer 2 y con color por píxel. `SAVE` y
  `LOAD` usan un fichero en la tarjeta, junto al `.nex`, con el nombre del
  proyecto y `.SAV`: `faro.nex` guarda en `FARO.SAV`.
- **PC con CGA.** Un `.EXE` de DOS con el nombre del proyecto, que corre en
  cualquier PC desde un XT a 4,77 MHz con una CGA o algo que haga su modo de
  320 por 200. Cuatro colores **elegidos para cada lámina** entre los que la
  CGA permite; el texto, como en el Amstrad, cuarenta columnas bajo la lámina.
  Una aventura de Amstrad se dibuja con las reglas del Amstrad y parpadea lo
  que la CGA deja: el fondo, o el trío entero cuando no mueve nada más. `SAVE`
  y `LOAD` usan un fichero junto al programa, con su nombre y `.SAV`; al
  acabar la partida, una tecla vuelve a DOS. La tecla que se pulsa es la de la
  distribución que tenga DOS (`KEYB SP` y las demás).

El **ancho de pantalla** no es el mismo en todas —32 columnas en Spectrum, MSX
y Next; 40 en Amstrad y PC; 64 en PCW— y eso cambia dónde parten las líneas. Un
texto que quede bien en una puede quedar distinto en otra.

---

## 10. Las dos licencias, que son a propósito

Las herramientas —todo lo que es Python— están bajo la **GPL v3**. Los
intérpretes de [`z80/`](../z80) y [`x86/`](../x86), que son lo que acaba
dentro de la aventura de otro, están bajo la **licencia MIT**: una aventura construida con esto **no
arrastra ninguna obligación** de las herramientas que la construyeron.

---

## Dónde seguir

| si buscas | mira |
|---|---|
| el lenguaje entero: opcodes, dibujo, el turno, el parser | [`gac.md`](gac.md) |
| una aventura escrita para leerse | [`../ejemplo/faro.gac`](../ejemplo/faro.gac) |
