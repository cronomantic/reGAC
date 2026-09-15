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
empiece por `#`, `/`, `;` o `|` se escribe precedida de `|`, que el compilador
descarta.

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

**Entera**: un volcado normal, ocho bytes por carácter desde `first` hacia
arriba, que es lo que escribe cualquier editor de fuentes de estas máquinas y
la forma que tiene la ROM de una. `file` dice dónde está, relativo al fuente.

    /FONT chars=128 file="letras.bin" first=32

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

## Extensiones previstas

Estas dos no están implementadas. Se listan aquí para que el diseño actual no
las bloquee.

**Nombres simbólicos.** `.def PUERTA_ABIERTA 5` permitirá escribir
`SET? PUERTA_ABIERTA`. El decompilador seguirá emitiendo números.

**Inclusión de ficheros.** `.include "comun.gac"` para compartir vocabulario y
condiciones de baja prioridad entre aventuras, el equivalente al fichero de
comienzo rápido `QS.ADV` de GAC.
