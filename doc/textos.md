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

Cada carácter que la aventura usa recibe un código, que es también su posición
en la fuente. Los códigos se reparten por frecuencia, de modo que una máquina
apurada de memoria puede quedarse con los glifos útiles y soltar la cola.

Lo importante es que no se reserva nada para alfabetos que la aventura no usa.
Un acento cuesta exactamente lo que cuesta una letra, y castellano, catalán o
portugués no necesitan ningún caso especial. Medido sobre MegaCorp, acentuar el
texto como el autor habría querido añade cinco glifos y un 1,4% de tamaño.

Las ocho aventuras necesitan entre 42 y 71 glifos, con lo que sobran entre 185 y
214 códigos para el compresor.

El techo son 256 códigos contando los del compresor, y una aventura que se pase
lo oye al construir, con la lista de los caracteres de los que mejor podría
prescindir.

Conviene saber que **el compresor se los gasta todos**: en las ocho aventuras
usa exactamente tantas parejas como códigos le sobran, 185 a 214. O sea que no
está limitado por el texto sino por el byte, y cada glifo de más es una pareja
de menos. Acentuar una aventura entera cuesta cinco glifos.

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
