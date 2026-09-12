# Gráficos vectoriales de GAC

Notas sobre cómo se dibujan las láminas, deducidas de los datos de las
aventuras. Ni el decompilador de referencia en C ni grackle llegan a dibujar
nada en Spectrum, así que la semántica de abajo es reconstruida y verificada
mirando el resultado. Quien escriba la capa de dibujo para cada máquina
necesita esto.

La implementación está en [`regac/gfx.py`](../regac/gfx.py).

## Sistema de coordenadas

Como en el BASIC del Spectrum: `x` de 0 a 255 de izquierda a derecha, `y` de 0
abajo a 175 arriba. La lámina ocupa las dieciséis filas de caracteres de
arriba, o sea 128 filas de píxeles, y las ocho de abajo quedan para el texto.

Medido sobre las 196 láminas de las ocho aventuras, `x` va de 0 a 255 e `y` de
48 a 175, que es exactamente ese área. La conversión a fila de pantalla es
`fila = 175 - y`.

## Color

Los valores siguen la convención del BASIC. Del 0 al 7 son los colores, el 8
significa dejar el color que ya hubiera y el 9 elige negro o blanco según
convenga para que se lea. El color se guarda por celda de ocho por ocho, con la
limitación de atributos del Spectrum.

## Comandos

| Comando | Efecto |
|---|---|
| `BORDER c` | Color del borde |
| `INK c`, `PAPER c`, `BRIGHT b`, `FLASH f` | Color en curso |
| `PLOT x y` | Enciende un píxel |
| `LINE x1 y1 x2 y2` | Recta entre dos puntos absolutos |
| `RECT x1 y1 x2 y2` | Contorno de un rectángulo |
| `ELLIPSE x1 y1 x2 y2` | Elipse inscrita en ese rectángulo |
| `FILL x y` | Colorea la región, sin tocar los píxeles |
| `BGFILL x y` | Colorea la región y además apaga sus píxeles |
| `SHADE x y` | Rellena la región con una trama de medio tono |
| `CALL n` | Ejecuta otra lámina, para partes repetidas como los marcos |

Las tres órdenes de relleno se propagan desde un punto y las frenan los píxeles
ya encendidos y los bordes del área de imagen.

## Lo que costó acertar

El relleno es lo que más costó, y lo acabé resolviendo leyendo el intérprete
original dentro de las instantáneas. No es un relleno por inundación.

**Recorre una sola columna.** Sube y baja por la columna del punto de partida
pintando un tramo horizontal en cada fila, y se detiene en cuanto el punto justo
encima o debajo está ocupado. Nunca dobla una esquina. Por eso una lámina lleva
decenas de órdenes de relleno donde una inundación necesitaría una, y por eso
rellenar macizo no sepulta el dibujo. Está en $6374 del original.

**Lo que deposita son dos bytes.** El bajo en las filas pares y el alto aplicado
con o exclusivo en las impares, contando en la y de las órdenes. Macizo es
`00FF`, borrar es `0000` y el medio tono es `FFAA`, que da AA y 55 alternando.
Está en $6364.

De ahí salen dos correcciones a lo que yo había deducido de los datos. El
relleno de tinta sí enciende píxeles, es macizo; yo había concluido que sólo
cambiaba el color, porque con una inundación se desbordaba y se comía la lámina.
Y el medio tono resultó ser exactamente el damero que había supuesto.

## Reparto de la pantalla y desplazamiento

La lámina ocupa las dieciséis filas de arriba y el texto las ocho de abajo.
Cuando el texto llena su zona, se desplaza sólo esa zona: la lámina no se va
hacia arriba.

Esto no es una suposición. GAC lo consigue con el mecanismo de pantalla
inferior del Spectrum, y las instantáneas conservan las variables de sistema
que lo demuestran. La que reserva filas para la pantalla inferior vale ocho en
las partidas guardadas con lámina a la vista, cuando su valor normal es dos. El
ROM desplaza esa zona por su cuenta sin tocar la de arriba.

En las instantáneas guardadas en modo texto esa misma variable vale
veintitrés, o sea casi la pantalla entera. Eso es justo la diferencia entre los
opcodes de imagen y de texto, y confirma que en modo texto el texto dispone de
todo.

La otra variable que lo corrobora es el puntero de fuente del ROM, que en las
ocho aventuras apunta a memoria y no a la ROM. Redefinir ahí la fuente sólo
sirve de algo si se imprime con las rutinas del ROM, que son las que
implementan ese reparto de pantalla.

## Cómo se hace multiplataforma

El motor se parte en dos. Un intérprete de órdenes común, que en el Z80 se
escribirá una sola vez porque las cinco máquinas lo son, y debajo un dispositivo
por máquina que aporta seis primitivas: fijar el borde, fijar los colores en
curso, poner un punto, decir si una posición corta un relleno, pintar un píxel
dentro de un relleno y volcar el resultado. El rectángulo y la elipse se
construyen sobre la recta y viven en el código común.

En el PC eso es [`regac/gfx.py`](../regac/gfx.py) para el intérprete y
[`regac/devices.py`](../regac/devices.py) para las máquinas. Sirve de referencia
contra la que validar cada capa en ensamblador.

### Las dos familias de color

Spectrum y MSX1 llevan color por bloque de píxeles, con un matiz importante: el
Spectrum lo lleva por celda de ocho por ocho y el MSX1 en modo 2 por franja de
ocho de ancho y una de alto, así que su limitación es la misma en horizontal y
mucho más suave en vertical. Además el MSX1 no tiene brillo ni parpadeo, y sus
quince colores no son los del Spectrum, de modo que cada color se traduce al más
parecido que esa máquina tenga.

Amstrad, Sam Coupé, Next y el MSX2 en modo 5 llevan color por píxel y no tienen
limitación ninguna, pero entonces un píxel encendido ya no marca el borde de una
figura y el relleno no sabe dónde parar. Ésas necesitan un plano de máscara de
un bit, que cuesta 4 KB.

Y esa máscara tiene que seguir exactamente las mismas reglas que el mapa de bits
del Spectrum. Ahí me equivoqué al principio: el medio tono enciende píxeles de
verdad, que luego frenan a los rellenos siguientes, y el relleno de fondo los
apaga, que les abre paso. Los dibujantes trabajaron contra ese comportamiento.
Con la máscara sin actualizar, ciento un rellenos del Quijote que en el original
se quedaban parados inundaban la pantalla en el Sam.

### No escalar

El área de dibujo original es de 256 por 128, y las cinco máquinas pueden
mostrar 256 píxeles de ancho. El Amstrad en modo 1 tiene 320, así que invita a
estirar. No hay que hacerlo.

Estirar obliga a volver a trazar las rectas en la resolución destino, y dos
segmentos que en el original se tocaban pueden dejar de tocarse. El relleno se
cuela por esa rendija. Medido sobre los 7760 rellenos de las ocho aventuras:

| Variante del Amstrad | Rellenos que discrepan | De ellos, graves |
|---|---|---|
| 256 centrado en los 320 | 0 | 0 |
| Estirado a 320 | 776 | 236 |

Grave quiere decir que el relleno cubre más de media pantalla de diferencia, o
sea que la lámina queda destrozada. Centrar la imagen y dejar un margen de 32
píxeles a cada lado no cuesta nada a la vista y evita la clase entera de
problema.

### La paleta del Amstrad

El hardware puede hacer 27 colores, tres niveles de rojo, verde y azul
combinados. Están en [`regac/devices.py`](../regac/devices.py) en el orden de
numeración del firmware, del 0 negro al 26 blanco brillante, con los valores
tomados de la tabla de paletas de hardware del proyecto gimp-palettes y
contrastados con la documentación de CPCWiki.

El modo 1 carga cuatro a la vez. El modo 0 carga dieciséis, pero sólo tiene 160
píxeles de ancho, lo que obligaría a reducir la imagen y eso rompe los rellenos
por lo dicho arriba. Así que modo 1, con cuatro colores.

Cuatro se queda corto para estas aventuras. Contando los colores que cada lámina
enseña de verdad, descartando los testimoniales que ocupan menos de una milésima
de la pantalla:

| Colores que usa la lámina | Láminas |
|---|---|
| 1 a 4 | 126 |
| 5 | 49 |
| 6 | 17 |
| 7 | 4 |

La salida es que el Amstrad puede recargar sus tintas en cada pantalla, así que
la elección es por lámina y no por aventura. `choose_inks` mira cuánta pantalla
cubre cada color del original y escoge las cuatro del hardware que minimizan el
error ponderado por área, de modo que el color de una pared pesa más que el del
pomo de una puerta.

Con eso, 125 de las 196 láminas no pierden ningún color. De las otras, 50
pierden uno, 17 pierden dos y 4 pierden tres.

### Verificarlo

La orden `checkgfx` dibuja cada lámina en el Spectrum y en la máquina destino y
compara cuánta pantalla cubre cada relleno. Es la prueba que encontró las dos
cosas de arriba, y la que conviene pasar cada vez que se toque un dispositivo o
se añada una máquina.

    python -m regac checkgfx partida.json -m cpc

## El dibujo en el Z80

El Spectrum ya dibuja, en [`z80/spectrum`](../z80/spectrum): punto, recta,
rectángulo, elipse y los tres rellenos, con el intérprete de órdenes en
[`z80/common/picture.asm`](../z80/common/picture.asm), que no sabe nada de
pantallas. Las pruebas dibujan cada primitiva en el emulador y la comparan byte
a byte con la referencia de Python, píxeles y colores. Las once coinciden
exactas.

Para que eso fuese posible los dos lados tienen que trazar igual, así que la
elipse se recorre en sesenta y cuatro pasos con una tabla de senos y aritmética
entera, y la recta usa la forma de Bresenham que mantiene el error dentro de un
byte. Cambié la referencia para que hiciera lo mismo.

Dos cosas que costaron. La primera es que rellenar con tinta no cambia ningún
píxel, así que la región sigue siendo transitable y la propagación no termina
nunca. Se resuelve encendiendo los píxeles mientras se propaga, que además no
cuesta nada porque dentro de una región estaban apagados, anotando cada tramo
pintado y recorriendo la lista después para poner el color y las marcas de
verdad. Ningún relleno de las 196 láminas pasó de 513 tramos.

La segunda es que el valor 128 de la tabla de senos no cabe en un byte con
signo. Dos de los sesenta y cuatro puntos salían reflejados y sus segmentos
cruzaban la elipse. La tabla va acotada a 127 en ambos lados.

### Velocidad: cómo se hacía entonces

La primera versión tardaba 31 segundos en rellenar la pantalla, porque
calculaba la dirección de cada píxel una y otra vez. Las rutinas de la época no
hacían eso, y aplicarlo baja a 7 segundos:

**La dirección se calcula una vez por fila.** Los treinta y dos bytes de una
fila tienen la columna en los cinco bits bajos del byte bajo, así que moverse a
lo largo de ella es `inc l` y `dec l`, sin tocar la parte alta.

**De píxel a píxel se rota una máscara.** Buscar dónde acaba un tramo es girar
un bit y mirar; cuando la máscara da la vuelta, se pasa al byte de al lado.

**Ocho píxeles de golpe.** Encender un tramo, apagarlo o ponerle trama se hace
por bytes enteros, con máscaras sólo en los dos extremos parciales. Un byte a
cero son ocho píxeles libres y un byte a 255 son ocho bordes, lo que también
acelera el rastreo de las filas vecinas.

**El relleno con trama es un patrón de ocho filas**, un byte por fila, en
[`shade_pattern`](../z80/spectrum/fill.asm). Por eso cuesta lo mismo que un
relleno liso: se escribe un byte y cubre ocho píxeles igual. Cambiar la trama es
cambiar la tabla.

Quedan 7 segundos para una pantalla entera, que sigue siendo mucho. El resto se
va en el rastreo de las filas de arriba y abajo, que todavía recalcula la
dirección en cada píxel en lugar de arrastrarla. Lo siguiente es leer las
rutinas originales, que están dentro de las propias instantáneas, para
contrastar el método antes de seguir optimizando a ciegas.

## Cómo lo hacía GAC, leído de las propias aventuras

Las instantáneas llevan dentro el intérprete original, y sus rutinas están en
las mismas direcciones en las ocho, porque es el mismo programa. Buscando la
firma del cálculo de dirección de pantalla y las llamadas a la ROM aparece
esto:

| Dirección | Qué hay |
|---|---|
| $6484 | `CALL $24BA`, o sea DRAW de la ROM |
| $64A5 | `JP $22E5`, o sea PLOT de la ROM |
| $64A8 y $64B4 | guardar y restaurar los 512 atributos de la imagen |
| $95FF, $9604, $9620 | `CALL $0E9E`, la rutina de dirección de la ROM, para borrar |

O sea que GAC no escribió ni el punto ni la recta: llamaba a la ROM. Los
colores los pasa copiando los atributos permanentes a los temporales, que es
como la ROM espera recibirlos.

### Que use la ROM no nos ata a ella

Nosotros no la llamamos. Lo que tomamos de ahí es la regla con la que rompe los
empates, no el código: el error arranca en la mitad del lado mayor, sube por el
menor, y cuando alcanza al mayor se lo resta y ese paso va en diagonal. Contarlo
al revés es un Bresenham igual de válido, pero coloca los pasos diagonales un
sitio más allá y eso se ve en las rectas cortas inclinadas.

Implementarlo por nuestra cuenta da las dos cosas a la vez. Portabilidad,
porque el Amstrad, el MSX, el Sam y el Next trazan igual sin necesitar ninguna
ROM de Spectrum. Y fidelidad, porque el dibujo original se hizo con esa regla y
queremos reproducir esas láminas, no unas parecidas.

### La elipse

Sí es código propio de GAC, en $88FE, y trae dos sorpresas.

Los dos pares de coordenadas **no son una caja envolvente**. El primero es el
centro y el segundo da los radios, medidos como la distancia de uno a otro. Yo
los había tomado por una caja, con lo que todas mis elipses salían a la mitad de
tamaño y descentradas.

Y la recorre en ocho pasos por cuadrante, con una tabla de senos que la propia
aventura lleva en $A1ED: ocho cosenos y ocho senos escalados a 256 y acotados a
255 para que quepan en un byte, que es el mismo apaño que tuve que hacer yo. Los
radios se multiplican por la entrada y se toma el byte alto. Cada cuadrante se
traza por separado empezando por el punto del costado, y de ahí que la curva
sean treinta y dos segmentos rectos.

### Una comparación que no valía

Intenté contrastar contra la pantalla que guardan las propias instantáneas, y
el resultado engañaba: salían coincidencias del cero por ciento de error. Al
mirar el mapa de diferencias se ve que esas pantallas no tienen lámina
dibujada, así que lo que coincidía eran dos imágenes casi vacías. Para
contrastar de verdad hay que ejecutar el juego hasta que dibuje.

## Lo que queda por confirmar

La diferencia exacta entre `FILL` y `BGFILL` se ha deducido, no verificado
contra la máquina real. Igual que la trama concreta que pinta `SHADE`, que aquí
es un damero de un píxel. Ambas cosas se pueden comprobar comparando una lámina
con la que saca un emulador ejecutando la aventura original.
