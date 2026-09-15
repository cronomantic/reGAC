# Almacenamiento de textos

Cómo se guarda el texto de una aventura en reGAC. Aquí es donde se rompe la
compatibilidad con el formato original, a propósito, porque el intérprete es
nuestro. La implementación está en [`regac/text.py`](../regac/text.py).

Son dos capas que no se conocen entre sí: el juego de caracteres asigna un
código a cada carácter, y encima de eso el texto se comprime por parejas.

## Por qué no vale el formato de GAC

GAC mete cada carácter en siete bits y usa el octavo para marcar el final de
cada token. Además guarda los tokens en mayúsculas y los pasa a minúscula sobre
la marcha manipulando un bit, lo que da por supuesta la disposición del ASCII.

De los 128 valores posibles sólo usa del 32 al 127, así que quedan 32 huecos
libres. El juego castellano completo, vocales acentuadas en ambas cajas más eñe,
diéresis y signos de apertura, son dieciséis: cabría. Pero un carácter acentuado
metido en esos huecos no tiene el bit que el mecanismo de caja manipula, así que
necesitaría dos códigos, uno por caja, y para catalán, portugués o francés los
32 huecos se agotan enseguida.

Se puede estirar con un apaño para el castellano. No da para lo que queremos.

## El juego de caracteres

**Fijo, y el mismo en todas las aventuras.** El sitio que un carácter ocupa en
la tabla es su código:

| códigos | qué |
|---|---|
| 0 | el nulo, que no es ningún carácter y nunca lo será |
| 1 | reservado para un cambio de color, para cuando una palabra quiera otra tinta |
| 2-15 | `áéíóúüñ` y sus mayúsculas |
| 16-17 | `¿` `¡` |
| 18-19 | `ç` `Ç` |
| 20-28 | `àèòïãõâêô`, lo que ponen encima catalán, portugués e italiano |
| 29-31 | `ª` `º` `—` |
| 32-127 | ASCII tal cual, hasta el símbolo de copyright que estas máquinas ponen al final |
| 128-255 | del compresor: 128 parejas, siempre |

Antes se numeraban por frecuencia de uso, y eso tenía una consecuencia que no
se ve hasta que se mide: **al compresor le quedaban los códigos que el alfabeto
no se llevara**. Una aventura en castellano con acentos tenía menos parejas que
una en inglés, y una en catalán menos todavía. El idioma no debe ser un
handicap. Con la tabla fija todos tienen las mismas 128 parejas.

Y una fuente pasa a ser **una hoja de las mismas letras en los mismos sitios**,
que es algo que un artista puede dibujar una vez y reusar, en vez de una tabla
que depende de qué palabras salgan en la aventura.

Lo que cuesta, medido sobre las ocho aventuras: el texto empaquetado sube un 8%
—entre 280 y 575 bytes— y la base de datos entera **un 2,1%**, de 305 a 565
bytes por aventura. Parte de eso vuelve: como un código desde el espacio es su
propio ASCII, desaparecen del binario la tabla de 96 bytes que traducía tecla a
código y la de los diez dígitos, y con ellas una búsqueda por cada tecla
pulsada. Un dígito es ahora `add a, 48` y el espacio es 32.

Lo que no está en la tabla no se puede usar, y la construcción lo dice con el
carácter en la mano en lugar de imprimir un hueco. Caben el castellano entero,
las minúsculas acentuadas de catalán, portugués e italiano, y los signos; el
francés no, y ahí es donde la directiva `charset` tendría por fin trabajo:
elegir el perfil de los treinta que van debajo del espacio.

## De dónde salen los glifos que la aventura no trae

Un código no dibuja nada. La fuente que una aventura hereda de 1986 no tiene ni
una letra acentuada, así que hasta ahora la á recibía código y salía en blanco.

No están dibujados a mano. **Una letra acentuada es la letra de la propia
aventura con una marca encima**, para que se parezca a la tipografía en la que
está sea cual sea; lo único guardado son las cinco marcas —agudo, grave,
circunflejo, tilde, diéresis— y la cedilla. Unicode dice qué letra y qué marca:
NFD parte la á en a y acento y la ñ en n y tilde, y cualquier idioma que
quisiéramos son esas mismas marcas otra vez.

Dónde cabe la marca sale de la letra. En una fuente de este tipo una minúscula
se apoya en las filas dos a seis, así que le sobran dos arriba y cabe la marca
entera; una mayúscula ocupa de la cero a la seis, así que se baja una fila —la
de abajo siempre está libre— y arriba va sólo el cuerpo de la marca. Por eso
cada marca son dos filas con la segunda como la que importa: la segunda es la
que le toca a una mayúscula. La cedilla es al revés y no baja nada: cuelga de la
fila siete, que está libre en los dos casos.

La ¿ y la ¡ no son letra y marca, son la ? y la ! dadas media vuelta, que es
exactamente lo que son. Al girarlas se corren una columna a la izquierda,
porque una fuente así deja libre la columna cero y usa la siete, y se devuelven
a su sitio.

Lo que no se puede construir —una letra que no está debajo, una marca que no
conocemos— sale en blanco antes que salir mal. Está en
[`glyphs.py`](../regac/glyphs.py).

Y esto es sólo para lo que la aventura no trae. **Lo que el autor dibuja se usa
tal cual**: la tabla de la fuente va indexada por el carácter, así que quien
quiera su propia Ñ la pone en el 241 y se respeta; encima de un glifo dibujado
no se compone nada. Cómo se le da una fuente propia —entera en un fichero o
letra a letra— está en [`formato-fuente.md`](formato-fuente.md).

## Al vocabulario se le caen las marcas

Ningún teclado de estas máquinas tiene tecla de acento, así que un vocabulario
que dijera ARAÑA no lo podría escribir nadie. En el binario se guarda ARANA y el
jugador escribe ARANA; el fuente puede seguir diciendo ARAÑA, que es como se
escribe. Sólo se le caen a las palabras que el parser compara: el texto conserva
todas sus marcas, porque el texto se imprime y no se teclea.

Si dos palabras se quedan en la misma —PEÑA y PENA—, son la misma palabra para
el jugador y la segunda no se alcanzaría nunca, así que la construcción lo dice
en lugar de dejarlo pasar. El intérprete de PC hace la misma cuenta al buscar
una palabra, para que las dos máquinas entiendan lo mismo.

## La compresión

Se sustituye la pareja de códigos más repetida por un código libre, una y otra
vez. Como los códigos nuevos también entran en parejas posteriores, uno solo
acaba representando una tirada larga de caracteres.

Sobre los 71577 caracteres de texto de las ocho aventuras, comparando esquemas:

| Esquema | Tamaño |
|---|---|
| Tabla de abreviaturas al estilo PAW | 84% |
| Huffman por bytes | 57% |
| Parejas más Huffman | 52% |
| **Parejas** | **49%** |

Ese 49% era con todos los códigos que sobraran; con las 128 parejas fijas sale
un 8% más, entre el 50% y el 55% según la aventura. Es lo que cuesta que el
idioma no cuente, y sigue ganando a todo lo demás de la tabla.

Que las parejas ganen a Huffman llama la atención, pero con corpus de siete a
catorce kilobytes la tabla de Huffman se come la ventaja, y además Huffman sólo
mira caracteres sueltos mientras que las parejas capturan tiradas enteras.

Dos cosas más la recomiendan en una máquina de ocho bits, y pesan tanto como el
ratio. Desempaquetar es mirar una tabla y usar una pila pequeña, sin manejo de
bits: la pila nunca pasó de diez bytes en las ocho aventuras. Y cada mensaje se
desempaqueta solo, sin tocar los anteriores, que es justo lo que el intérprete
necesita para imprimir el mensaje 137 y nada más.

Las parejas no se cuentan nunca a caballo entre dos mensajes, que es lo que
mantiene esa independencia.

## Consultarlo

    python -m regac text partida.json

Da el tamaño empaquetado, la tabla de parejas, los glifos que hacen falta, los
códigos que sobran y la profundidad de pila que necesitará la rutina en Z80.

## Dónde está puesto

En la base de datos JSON, que es la que usa el intérprete de PC, el texto sigue
en claro: allí no hay nada que ahorrar. Empaquetado va en el binario de las
máquinas de ocho bits, que es donde el tamaño importa, y lo desempaqueta
[`unpack.asm`](../z80/common/unpack.asm) mensaje a mensaje.
