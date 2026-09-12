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

## Lo que queda

El compilador todavía guarda el texto en claro en la base de datos JSON, que es
la que usa el intérprete de PC. Esta pieza entra cuando exista el formato
binario para las máquinas de ocho bits, que es donde el tamaño importa.
