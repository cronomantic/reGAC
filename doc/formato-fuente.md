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
    charset  ascii
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

La cabecera declara cuántos caracteres cubre la tabla. Luego, ocho bytes por
carácter en hexadecimal, con el glifo como comentario. Los caracteres en blanco
se omiten.

    /FONT chars=128
    #65   00 3C 42 42 7E 42 42 00   ; A

## Extensiones previstas

Ninguna está implementada todavía. Se listan aquí para que el diseño actual no
las bloquee.

**Caracteres latinos.** El fuente ya es UTF-8. La directiva `charset` elegirá
la tabla de caracteres del destino (`ascii`, `latin1`, `spectrum`, `msx`...) y
el compilador traducirá cada carácter al índice de glifo correspondiente. El
formato de texto original de GAC no lo permite: usa el bit 7 como marca de fin
de token y los dos bits altos de cada palabra para mayúsculas y minúsculas, así
que no queda espacio para acentos. Esto obliga a una codificación de texto
nueva en el intérprete, que es también donde entra la compresión.

**Compresión de textos.** Decisión del fichero de proyecto, no del fuente. La
sección `/TOK` (tabla de tokens) será siempre generada, nunca escrita a mano.

**Nombres simbólicos.** `.def PUERTA_ABIERTA 5` permitirá escribir
`SET? PUERTA_ABIERTA`. El decompilador seguirá emitiendo números.

**Inclusión de ficheros.** `.include "comun.gac"` para compartir vocabulario y
condiciones de baja prioridad entre aventuras, el equivalente al fichero de
comienzo rápido `QS.ADV` de GAC.
