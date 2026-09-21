# El lenguaje GAC: referencia completa

El **Graphic Adventure Creator** lo publicó Incentive en 1986. Su manual
explicaba cómo se tecleaba una aventura dentro de la máquina; esto explica
**el lenguaje**, entero, para escribir una hoy.

Esta página se basta sola. No hace falta el manual original ni ningún otro
documento de `doc/`: los demás son diarios de desarrollo —lo que se midió, en
qué orden y por qué— y no sirven de referencia.

Todo lo que se afirma aquí está o bien implementado en los intérpretes de este
proyecto o bien **medido en el intérprete de 1986**, corriendo, sobre las
aventuras de verdad.

---

## 1. Las piezas

Una aventura son siete cosas y ninguna más:

| | |
|---|---|
| **salas** | descripción, salidas y lámina |
| **objetos** | peso y sala donde empiezan |
| **vocabulario** | verbos, nombres, adverbios y pronombres, cada palabra con su número |
| **mensajes** | los textos que no son descripciones |
| **marcadores** | 256 banderas de sí o no |
| **contadores** | 128 números de un byte |
| **condiciones** | lo que hace que pase algo |

No hay variables con nombre, ni funciones, ni bucles. Una aventura es una
lista de condiciones que se miran en un orden fijo, y ese orden es lo primero
que hay que entender.

---

## 2. Un turno, de principio a fin

Hay **tres tablas de condiciones** y se miran así:

```
  ┌─ cada turno, antes de nada ────────────────┐
  │  1. la tabla de ALTA prioridad             │
  └────────────────────────────────────────────┘
                     │
           se cuenta el turno
                     │
  ┌─ se pide una orden y se toma una ──────────┐
  │  2. ¿nombra una salida de esta sala?       │
  │     si sí: se anda, y el turno ACABA       │
  │  3. la tabla LOCAL de esta sala            │
  │  4. la tabla de BAJA prioridad             │
  └────────────────────────────────────────────┘
                     │
     si nadie la atendió: "no puedes hacer eso"
                  o "¿cómo dices?"
```

Cuatro cosas de ahí son más sutiles de lo que parecen, y las cuatro están
medidas en el original:

**El turno se cuenta después de la tabla alta, no antes.** MegaCorp monta la
partida entera en una condición guardada por «el contador de turnos sigue a
cero»; contando primero, esa condición no corre nunca y la aventura mata al
jugador en la primera jugada.

**Una orden que nombra una salida acaba el turno ahí.** `NORTE` en una sala
con salida al norte anda, y **no se mira ni la tabla local ni la baja**.

**La tabla local va entre las dos**, y si atiende la orden la baja no llega a
mirarse.

**Una línea puede llevar varias órdenes**, partidas por los caracteres y las
palabras que la aventura declare. Se atienden una a una, cada una con su paso
completo por las tablas.

---

## 3. Cómo se escribe una condición

Una condición es una pregunta y lo que se hace si la respuesta es sí:

    IF ( VERB 7 AND NOUN 2 ) GET 2 MESS 14 WAIT END

Por dentro es una pila: los valores se empujan, los opcodes los toman y
algunos dejan un resultado. Al escribirla no se nota, porque los operandos se
ponen donde se leen mejor: `VERB 7` delante, `2 < 5` en medio.

Entre `IF (` y `)` va la pregunta; del `)` al `END`, lo que se hace. Una
condición sin `IF` se hace siempre.

**Los paréntesis no agrupan.** `AND`, `OR`, `XOR` y `NOT` toman lo que haya en
la pila en el orden en que se escribió. Con preguntas encadenadas, escribe en
el orden en que quieres que se evalúen.

---

## 4. Los opcodes, todos

Sesenta y siete. Agrupados por lo que hacen, con lo que toman y lo que dejan.

### Estructura de una línea

| | |
|---|---|
| `IF ( … )` | empieza la pregunta; lo que sigue al `)` se hace si salió que sí |
| `END` | cierra la condición |

### Lógica

| | |
|---|---|
| `a AND b` | las dos |
| `a OR b` | alguna |
| `a XOR b` | una y no la otra |
| `NOT a` | la contraria |

### Dónde está el jugador y qué hay

| | |
|---|---|
| `AT n` | ¿está el jugador en la sala n? |
| `ROOM` | deja el número de la sala en la que está |
| `HERE n` | ¿está el objeto n aquí, en el suelo? |
| `CARR n` | ¿lo lleva encima? |
| `AVAI n` | ¿lo lleva **o** está aquí? |
| `n IN m` | ¿está el objeto n en la sala m? |
| `WEIG n` | deja el peso del objeto n |
| `WITH` | deja «lo que se lleva encima», para dárselo a `LIST` |
| `CONN v` | ¿hay salida de aquí por el verbo v? Deja la sala a la que va, o nada |

### Qué se ha tecleado

| | |
|---|---|
| `VERB v` | ¿el verbo de la orden es v? |
| `NOUN n` | ¿**alguno** de los dos nombres es n? |
| `ADVE a` | ¿el adverbio es a? |
| `VBNO` | deja el número del verbo tecleado |
| `NO1`, `NO2` | dejan el primer y el segundo nombre |

`NOUN` responde por los dos nombres y no sólo por el primero: `COGE DISCO
AGUJA` responde a `NOUN` de la aguja. Medido en el original.

### Marcadores

| | |
|---|---|
| `SET f` | poner el marcador f |
| `RESE f` | quitarlo |
| `SET? f` | ¿está puesto? |
| `RES? f` | ¿está quitado? |

### Contadores y números

| | |
|---|---|
| `n CSET c` | poner el contador c a n |
| `CTR c` | deja lo que vale |
| `INCR c`, `DECR c` | sube o baja uno |
| `n EQU? c` | ¿vale n el contador c? |
| `TURN` | deja el número de turno |
| `a + b`, `a - b` | suma y resta |
| `a < b`, `a > b`, `a = b` | comparaciones |
| `RAND n` | deja un número al azar de 0 a n-1 |

`<` y `>` miran **el signo de la resta**, que es lo que hace el original: una
diferencia que se ha ido por debajo de cero cuenta como menor.

### Moverse y describir

| | |
|---|---|
| `GOTO n` | lleva al jugador a la sala n **y la describe ahí mismo** |
| `DESC n` | describe la sala n |
| `LOOK` | describe donde está el jugador |

`GOTO` describe en el acto, no al turno siguiente: `GOTO 20` seguido de un
mensaje imprime la sala 20 primero. Y una sala descrita por `LOOK` en la tabla
alta ya no se describe otra vez: así es como una aventura abre en la sala que
quiere.

### Objetos

| | |
|---|---|
| `GET n` | coger el objeto n |
| `DROP n` | dejarlo |
| `n SWAP m` | cada uno va donde estaba el otro |
| `n TO m` | poner el objeto n en la sala m |
| `BRIN n` | traerlo a donde está el jugador |
| `FIND n` | ir a donde está el objeto, describiendo al llegar |
| `OBJ n` | escribe el nombre del objeto n |
| `LIST n` | escribe lo que hay en la sala n, o la palabra de «nada» |
| `STRE n` | pone en n lo que el jugador puede cargar; empieza en 250 |

`GET` mira en la mano, luego alrededor, y por último el peso, y **cualquiera
de las tres negativas acaba el turno**: las condiciones que vengan debajo en
la misma tabla no se miran. `BRIN` dice 245 si ya se lleva y 252 si no está en
ninguna parte, y también acaba el turno. `FIND` no dice nada de lo que ya se
lleva, y de lo que no está en ninguna parte dice 252.

### Texto y pantalla

| | |
|---|---|
| `MESS n` | escribe el mensaje n |
| `PRIN n` | escribe el número n |
| `LF` | salta de línea |
| `TEXT` | el texto se queda con la pantalla entera y dejan de dibujarse láminas |
| `PICT` | vuelve a permitir las láminas |

`TEXT` no borra nada ni mueve el cursor: lo único que cambia es hasta dónde
llega el desplazamiento. `PICT` tampoco redibuja nada; la ventana vuelve a su
sitio **cuando se dibuja la lámina siguiente**. Medido en el original.

### Sonido

| | |
|---|---|
| `SOUND n` | hace el ruido n |
| `QUIET` | silencio |

Estos dos son añadidos de este proyecto, no de GAC. Los hace el chip de sonido
donde lo hay —128, +3, Amstrad, MSX y Next— y el altavoz de un bit en el
Spectrum 48; los dos motores leen la misma tabla y duran lo mismo. Una máquina
que no tenga con qué sonar —el PCW— los lee y no hace nada, de modo que **la
misma aventura vale para todas las máquinas**.

### Fin del turno y de la partida

| | |
|---|---|
| `WAIT` | acaba el turno aquí |
| `OKAY` | dice «de acuerdo» y acaba el turno |
| `EXIT` | se acabó la partida |
| `QUIT` | pregunta antes, y se acaba si dicen que sí |
| `HOLD n` | espera n cincuentavos de segundo, o hasta que toquen una tecla |
| `SAVE`, `LOAD` | guardar y recuperar la partida |

`WAIT` y `OKAY` acaban también la tabla: lo que venga debajo **en esa misma
tabla** no se mira siquiera. `QUIT` lee una sola tecla: `N` lo cancela y
cualquier otra cosa —una letra, un espacio, el enter— sigue adelante.

### Sin uso

`NOP` y `NOP29` no hacen nada. Están porque el original los tenía.

Y uno más que no se escribe nunca: `ENDTABLE` es la marca de fin de tabla que
pone el compilador. Con él, sesenta y siete.

---

## 5. Marcadores y contadores que no son tuyos

Éste es el que más cuesta descubrir solo. **Algunos marcadores y contadores
son del intérprete**, y escribirlos por encima rompe cosas que parecen no
tener relación:

| | |
|---|---|
| marcador 0 | una sala acaba de describirse |
| marcador 1 | este sitio tiene luz |
| marcador 2 | el jugador lleva algo que alumbra |
| marcador 3 | no decir la puntuación al acabar |
| contador 0 | la puntuación |
| contador 126 | los turnos, byte **bajo** |
| contador 127 | los turnos, byte **alto** |

Los turnos van en ese orden —el 126 es el bajo— y sube de uno en uno con cada
orden.

**A oscuras** —marcadores 1 y 2 a cero— no se describe nada: se borra la
ventana de la lámina, se dice el mensaje 251 y **no se pone el marcador 0**,
porque no se ha descrito.

---

## 6. Los mensajes que usa el intérprete

Del 240 al 255 los dice el intérprete por su cuenta. Escríbelos todos:

| | | | |
|---|---|---|---|
| 240 | con qué pregunta | 248 | pesa demasiado |
| 241 | no puedes hacer eso | 249 | tu puntuación es |
| 242 | ¿cómo dices? | 250 | y has tardado |
| 243 | ¿otra partida? | 251 | está oscuro |
| 244 | ¿seguro? | 252 | no lo encuentro |
| 245 | ya lo llevas | 253 | también puedo ver |
| 246 | no lo llevas | 254 | de acuerdo |
| 247 | no lo veo | 255 | turnos |

---

## 7. Cómo entiende lo que se teclea

- **Se casan los principios de palabra.** Con `EXAMINAR` en el vocabulario
  valen `EX`, `EXA` y `EXAMINAR`; **no** vale `EXAMINARLO`, que es más larga
  que la guardada. El precio es que `LA` se la come `LAMPARA`, y el original
  lo paga igual.
- De las que empiezan igual, **gana la más corta**.
- Una orden es **verbo, nombre, segundo nombre y adverbio**, y todos pueden
  faltar.
- Un **pronombre** se refiere al nombre de la orden anterior.
- Una palabra conocida con la que no hay nada que hacer da «no puedes hacer
  eso»; una línea sin verbo **ni** nombre reconocibles da «¿cómo dices?».

---

## 8. Las láminas

No son mapas de bits: son **listas de órdenes de dibujo**. Por eso una
aventura entera cabe en una cinta y por eso la misma lámina sale en ocho
máquinas distintas.

### El lienzo

Como en el BASIC del Spectrum: **`x` de 0 a 255** de izquierda a derecha,
**`y` de 0 abajo a 175 arriba**. La lámina ocupa las dieciséis filas de
caracteres de arriba —128 filas de píxeles, o sea `y` de 48 a 175— y las ocho
de abajo son del texto. La fila de pantalla es `175 - y`.

### El color

Los valores son los del BASIC: **0 a 7** los colores, **8** deja el que
hubiera, **9** elige negro o blanco según cuál se lea mejor. El color va por
celda de ocho por ocho, con la limitación de atributos del Spectrum.

### Los comandos

| | |
|---|---|
| `BORDER c` | color del borde |
| `INK c` | tinta en curso |
| `PAPER c` | papel en curso |
| `BRIGHT b` | brillo en curso |
| `FLASH f` | parpadeo en curso |
| `PLOT x y` | enciende un píxel |
| `LINE x1 y1 x2 y2` | recta entre dos puntos |
| `RECT x1 y1 x2 y2` | contorno de un rectángulo |
| `ELLIPSE x1 y1 x2 y2` | elipse inscrita en ese rectángulo |
| `FILL x y` | colorea la región, sin tocar los píxeles |
| `BGFILL x y` | colorea la región y además apaga sus píxeles |
| `SHADE x y` | rellena la región con una trama de medio tono |
| `CALL n` | ejecuta otra lámina, para lo repetido como los marcos |
| `PENS a b` | las dos plumas que teje un relleno (sólo Amstrad) |

Los tres rellenos se propagan desde un punto y los frenan **los píxeles ya
encendidos** y los bordes del área de imagen.

Tres cosas que conviene saber al dibujar, medidas en el original:

- **Un hueco de un píxel en una pared deja escapar el relleno**, pero sólo por
  esa fila: sale un rayo de un píxel de alto hasta el borde de la lámina y no
  se ensancha. Si una pared tuya tiene un agujero, se va a notar como una
  raya, no como una mancha.
- **Un pasillo de un píxel de ancho sí se rellena.**
- **Una diagonal por pared no deja pasar**: el relleno se para en la escalera.
- Y si la semilla cae **encima de un píxel encendido**, no pasa nada en
  absoluto.

`CALL` es como se comparten los fondos: una lámina de marco, y las demás la
llaman.

---

## 9. Lo que limita una aventura

No el formato: **dónde va a caber**. El sitio se lo reparten el intérprete y
la base de datos, y cada máquina tiene el suyo. El más justo es el **CPC
464**: sin bancos, y la base de datos en un trozo seguido.

Dos comandos lo dicen antes de construir nada:

    python -m regac text  aventura.json      # lo que ocupan los textos
    python -m regac check aventura.json      # y que nada apunte a la nada

---

## 10. Qué tiene esto de distinto del GAC de 1986

El principio del proyecto es que **los intérpretes hagan lo mismo que el
original**, hasta en lo que parece un defecto: dónde parte una línea, qué
contesta a una palabra que no conoce, en qué orden mira las tablas. Lo añadido
está encima y no cambia lo de debajo:

- **acentos y eñes**, que el original no tenía;
- **ruidos**, con `SOUND` y `QUIET`, que son los dos opcodes nuevos;
- **ocho máquinas**;
- **un fuente de texto** que se guarda en un control de versiones, en lugar de
  teclear la aventura dentro de la máquina.

Y una cosa que el original hace y **no se copia**, dicha para que no
sorprenda: al decidir dónde parte una línea, mira un carácter más allá del
final del mensaje y sigue contando lo que quedara en el buffer del mensaje
anterior. Eso no es una conducta, es un accidente de su memoria.

---

## Dónde seguir

| si buscas | mira |
|---|---|
| construir tu primera aventura | [`manual.md`](manual.md) |
| una aventura entera escrita para leerse | [`../ejemplo/faro.gac`](../ejemplo/faro.gac) |
