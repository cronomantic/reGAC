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

### Dónde estaba el tiempo de verdad

Después de rehacer el relleno con el modelo original quedaba una lámina que
tardaba doce segundos y medio, y todas las demás por debajo de dos. Medir en
lugar de suponer costó tres intentos fallidos: el salto por bytes en la
búsqueda de extremos, que es lo que hace el Amstrad, ganó medio segundo; y
colorear con un byte calculado una vez en vez de por celda, otro medio.

La lámina cara es la 28 de Bangkok2, y no dibuja nada raro: es un parpadeo de
borde montado por anidamiento. La 28 llama a la 27, que llama cuatro veces a la
26, que llama trece veces a la 25, que llama catorce veces a la 24, y la 24 son
diez cambios de borde. Salen 43.821 órdenes y 4.382 llamadas. Así que el gasto
no estaba en dibujar, estaba en el coste por orden del intérprete.

Dos cosas lo arreglan:

**Recordar la última lámina encontrada.** Buscar una recorría el índice desde
el principio, y una animación llama catorce veces seguidas a la misma. Doce
segundos y medio pasan a ocho.

**Llevar el puntero y la cuenta en registros.** El bucle los guardaba y los
volvía a leer de memoria en cada orden, y cada argumento repetía la operación
dentro de una subrutina. Ahora sólo bajan a memoria las órdenes que dibujan,
que son las que pisan todos los registros. Ocho segundos pasan a cuatro y
medio.

### Medir en ciclos, no en segundos

El emulador de este ordenador no corre a la velocidad de un Spectrum. Con un
bucle de duración conocida, en tres tamaños, sale recto en 2,03 MHz, el 58% de
los 3,5 de la máquina real. Todos los segundos que habíamos contado abultaban
un 72%.

Por eso la medición se hace ahora con el contador de ciclos del propio Z80, que
el emulador deja leer, dividido por tres millones y medio. Está en
[`tests/test_all_pictures.py`](../tests/test_all_pictures.py), que dibuja las
196 láminas, las compara con la referencia y comprueba que ninguna pase de
cinco segundos. Es lenta, media hora, así que sólo corre con `REGAC_SLOW=1`.

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

### Lo que hace con lo que se sale de la lámina

Una elipse puede salirse por arriba, y entonces sus puntos caen fuera de la
lámina. Qué hacía el original con ellos no se podía deducir, así que se le
preguntó: se carga la aventura en el emulador, se entra directamente en su
rutina de dibujo con el número de lámina en HL, y se deja un salto a sí mismo
justo donde la lámina termina, para que el juego no borre lo que acaba de
pintar. La respuesta está en $643C, y son dos reglas.

**Las coordenadas son de dieciséis bits con signo.** La elipse suma y resta el
radio al centro en HL, no en un byte, así que un punto por encima del borde
sigue estando por encima y no da la vuelta.

**Un punto que se sale no se tira, se lleva al borde.** La x se mete en 0 a
255 y la y en 48 a 175, y sólo después se sacan las dos diferencias que se le
pasan a la ROM. Por eso una curva que se escapa por arriba sale aplanada
contra el borde en lugar de volver como una raya que cruza la pantalla.

Nosotros hacíamos las dos cosas mal: enmascarábamos a un byte y no acotábamos.
Con las dos reglas puestas, las láminas 17, 18, 19 y 20 de quijote2, que eran
las que fallaban, salen idénticas a las del original, píxel a píxel.

### Una comparación que no valía

Intenté contrastar contra la pantalla que guardan las propias instantáneas, y
el resultado engañaba: salían coincidencias del cero por ciento de error. Al
mirar el mapa de diferencias se ve que esas pantallas no tienen lámina
dibujada, así que lo que coincidía eran dos imágenes casi vacías. Para
contrastar de verdad hay que ejecutar el juego hasta que dibuje.

## La versión de Amstrad CPC, leída entera

Las aventuras de CPC vienen en disco, y de ahí salen los ficheros sin encender
nada: el directorio de AMSDOS dice dónde está cada uno y su cabecera dice a qué
dirección se carga. `CARVALHO.FAC`, que es Los pájaros de Bangkok, se carga en
$0040 y ocupa hasta $A2F4, y trae dentro el intérprete y la aventura. En $4000
están los punteros en fila, tal como decía el decompilador de referencia, y en
$4012 el de las láminas. Con eso se lee el intérprete del CPC igual que se leyó
el del Spectrum, pero sin emulador de por medio.

### Las órdenes y sus argumentos

El repertorio es más corto que el del Spectrum: 1 recta, 2 elipse, 3 relleno,
8 rectángulo, 9 color, A llamada, B punto, y el 0 termina. Cualquier otro byte
cae en el caso por defecto, que fija la pluma con la que se dibuja. No hay
relleno de fondo ni media tinta aparte, porque aquí no hacen falta.

Los argumentos van en parejas, y **el segundo byte de cada pareja lleva siempre
el bit 7 puesto**; el intérprete lo quita al leerlo, con un `RES 7,E`. Por eso
la y de una lámina va de 0 a 127: la lámina del CPC mide 256 por 128, los
mismos números que la del Spectrum. El que escribe las láminas hace lo propio
al revés, con un `OR $80` sobre el byte alto.

### Sí escalaba, con una sola perilla

Cada coordenada pasa por lo mismo antes de dibujarse: se multiplica por un
factor de un byte, se divide por 64 y se le suma un origen, uno para la x y
otro para la y. El factor que trae el fichero es 128, que en las coordenadas
del firmware del CPC, que van de 0 a 639 por 0 a 399 sea cual sea el modo, deja
la lámina a tamaño natural, un píxel por punto.

Así que la lámina no se estira, pero **la perilla para estirarla está puesta**:
un byte de escala y dos orígenes colocan los mismos datos en cualquier
pantalla. Eso es exactamente lo que le hace falta al PCW, y no hay que
inventarlo.

### Se apoya en el firmware, como el Spectrum en su ROM

Mover, trazar la recta, poner el punto, preguntar por un punto, elegir pluma,
fijar el origen, la ventana y borrarla: todo eso lo pide a la máquina. El
Spectrum hacía lo mismo con su ROM. Lo que ninguna de las dos delega es el
relleno.

### El relleno, y el atajo que nos faltaba

El modelo es el mismo que en el Spectrum: recorrer la columna de la semilla
hacia arriba y hacia abajo tendiendo un tramo horizontal en cada fila. Lo que
cambia es cómo busca los extremos del tramo, y aquí está lo que llevábamos
buscando.

Antes de empezar pregunta por el punto de la semilla, y con el número de pluma
que le devuelven monta un byte en el que los cuatro píxeles son esa pluma. Ese
byte es la referencia. Para buscar el extremo hace un `XOR` de la referencia
contra el byte de pantalla: si la parte que toca al píxel no sale cero, ahí se
acaba el tramo. Y cuando el recorrido entra en un byte nuevo, compara el byte
entero: **si todo el byte coincide con la referencia, se lleva sus cuatro
píxeles de una vez** y salta al siguiente.

Es la optimización por bytes que intenté y deshice. El original la tiene, hecha
así: comparar primero el byte completo, y sólo bajar a máscara de bit en los
dos extremos.

### El color es una trama de dos plumas

La orden 9 lleva dos números de pluma. El intérprete convierte cada uno en su
byte de cuatro píxeles, se queda con las columnas pares del primero y las
impares del segundo, y los junta. Eso da un damero de las dos plumas. Después
guarda el mismo byte con las dos plumas intercambiadas, para las filas
alternas.

Es la pareja de patrones del Spectrum, generalizada: con las dos plumas iguales
sale un color sólido, y con dos distintas sale una mezcla que en modo 1 da
muchos más colores de los cuatro que hay. En una máquina de un bit por píxel
las dos plumas sólo pueden ser negro y blanco, y de ahí salen exactamente los
tres rellenos del Spectrum: lleno, vacío y damero. El PCW no necesita un modelo
de color propio, le basta esta orden.

### La elipse es la misma, byte por byte

En $22B0 está la tabla de dieciséis valores, la misma que el Spectrum guarda en
$A1ED, sin una cifra distinta. El primer par de la orden es el centro y el
segundo da los radios, como allí. Queda demostrado que la geometría de las
láminas no depende de la máquina.

### El dibujo, en cambio, no se reaprovechó

Las láminas no son las mismas. La versión de CPC de Bangkok trae 44 y la de
Spectrum 32, y no coincide ninguna, ni siquiera corrigiendo el origen de la y.
Se volvieron a dibujar para la máquina.

### Leer una aventura de Amstrad

`deGAC` las lee, con `-m cpc` cuando lo que se le da es una imagen plana de
memoria como la que saca `disk.py`. Las coordenadas salen ya en las del
Spectrum: la y se le quita el bit 7, que allí siempre está puesto, y se le
suman 48, porque la lámina mide 128 filas en las dos máquinas y lo único que
cambia es desde dónde se cuentan.

Las órdenes de color no tienen equivalente exacto. La que lleva dos plumas se
parte en tinta y papel, y la que fija una sola pluma queda como tinta. Los ocho
bytes de cabecera de cada lámina no caben entre las órdenes, así que se guardan
aparte, en `gfx_inks`, para no perder lo único que dice de qué color iba.

### Las mismas escenas, dibujadas otra vez

Con eso se pueden poner las dos versiones de Los pájaros de Bangkok una al
lado de la otra. Los cuartos llevan el mismo número en las dos, así que se
emparejan solas, y de cuarenta que tienen lámina en ambas salen veintiséis
parejas distintas.

Son las mismas escenas y ninguna es la misma lámina. El autobús con la cara
del hombre, la calle con sus dos edificios, el corro de gente, la mujer: se
reconocen todas, pero están vueltas a dibujar, con más color en pantalla y más
detalle, y sin el marco que el Spectrum pinta alrededor. No coincide ni una
sola orden, ni corrigiendo el origen de la y.

Para verlas hizo falta un dispositivo que dibuje como el Amstrad, porque con
el modelo del Spectrum salen manchas planas: un relleno que allí se para al
cambiar de pluma aquí se lo lleva todo por delante. Está en
[`AmstradDevice`](../regac/devices.py).

### Contrastarlo contra la máquina

Lo anterior no bastaba: las láminas seguían saliendo con fallos, y sólo se
podía saber preguntándole a un Amstrad. El cargador del disco quiere una
comilla tecleada en BASIC que el emulador no manda, así que la aventura entra
en memoria a mano, en la dirección que dice su propia cabecera, y la arranca un
`CALL` en decimal. Desde ahí se lee la pantalla y se convierte en números de
pluma, que es una comparación que no depende de los colores. Y escribiendo un
cero en medio de las órdenes de una lámina se la corta donde se quiera, que es
lo que permite ir acorralando un fallo.

Con eso salieron cuatro cosas:

**La lámina se dibuja en el 32,1 de la pantalla**, no pegada a la esquina.

**Empieza con la pluma 1**, y eso no lo dice el dato en ninguna parte: el marco
que pinta cada cuarto no lleva ni una orden de color y sale amarillo.

**Los ocho bytes de cabecera no son órdenes.** Merecía la pena probarlo porque
habría explicado el marco: cambiando el último en la máquina, lo que dibuja no
se mueve.

**El damero elige pluma por la y de las órdenes, no por la fila de pantalla.**
Es un bit de diferencia y volvía del revés todas las tramas. Esto solo llevó
una lámina entera del 89 al 99 por ciento.

Cómo queda, midiendo contra la pantalla de la máquina:

| lo que se dibuja | coincide |
|---|---|
| sólo el marco | 100,00% |
| el marco y la lámina 3 | 99,36% |
| el cuarto del aeropuerto entero | 99,15% |

### La recta del Amstrad da igual por qué punta se empiece

Se midió dibujando rectas de extremos conocidos en la máquina y anotando qué
puntos encendía. Siete rectas bastaron, y dicen dos cosas.

La primera: **ir de A a B enciende exactamente los mismos puntos que ir de B a
A**. La ROM del Spectrum no hace eso; dónde caen los pasos diagonales depende
de por qué punta se empiece.

La segunda: en cuanto se ponen las dos puntas en orden a lo largo del lado
mayor, el resto es el mismo Bresenham que ya teníamos, error a la mitad del
lado mayor, subiendo por el menor, y paso diagonal al alcanzarlo. Con eso las
siete rectas salen exactas.

### La elipse trabaja en medios píxeles

Aquí estaba lo que faltaba, y no era ni el redondeo ni el trazado: es que las
coordenadas del Amstrad no son píxeles.

El firmware tiene una pantalla de 640 por 400 sea cual sea el modo, así que el
intérprete multiplica por dos antes de dibujar. La elipse saca sus distancias
en esas unidades, o sea en medios píxeles, y sólo al final se bajan a píxel. Y
como lo que se baja es una posición y no una distancia, siempre se redondea
hacia abajo: eso aleja el punto del centro por el lado del que se resta y lo
acerca por el otro. De ahí que el cuarto en el que las dos coordenadas se suman
saliera perfecto y los otros tres no.

Con una distancia de 55 medios píxeles, sumar da 27 y restar da 28. Ese píxel
era toda la diferencia.

Se midió doblándole al Amstrad su propia tabla de senos en memoria: poniendo
las dieciséis entradas iguales, cada cuarto de la elipse dibuja un solo tramo
con el largo que uno quiera, y se lee dónde cae exactamente.

Cómo queda ahora, contra la pantalla de la máquina:

| lo que se dibuja | antes | ahora |
|---|---|---|
| sólo el marco | 100,00% | 100,00% |
| la lámina 3 | 99,38% | 99,85% |
| la 15 | 99,44% | 99,83% |
| la 23 | 99,75% | 99,94% |
| la 36 | 99,57% | 99,70% |
| el cuarto entero | 99,23% | 99,77% |

De paso quedó descartada la otra sospecha: **el firmware no encadena las rectas
de otra forma**. Con la tabla amañada se le hace dibujar el mismo tramo
encadenado detrás de otro y suelto como una orden, y salen los mismos once
puntos.

Antes de dar con ello se probó trazar también en medios píxeles, y **no es
eso**: llevar el dispositivo entero a medios, con la recta recorriendo unidades
y bajando cada punto a píxel al ponerlo, empeora mucho. El firmware baja los
extremos a píxel y traza en píxeles.

### Y una recta empinada empieza por abajo

Lo que faltaba era un detalle de las rectas, y costó verlo porque las que se
habían medido no lo distinguían. Al poner las dos puntas en orden por el lado
mayor, cuando ese lado es el vertical hay que empezar por la de abajo en las
coordenadas de las órdenes, que en filas de pantalla es la de abajo del todo.
Nosotros empezábamos por la contraria.

Se midió con una recta que sí las distingue, y de sus sesenta y un puntos el
orden bueno acierta los sesenta y uno y el otro cincuenta y uno.

Con eso, todo lo medido contra la máquina sale exacto:

| lo que se dibuja | coincide |
|---|---|
| sólo el marco | 100% |
| las láminas 3, 15, 23 y 36 sueltas | 100% |
| el cuarto del aeropuerto entero | 100% |
| una elipse de radio 30 | 168 de 168 |
| una de radio 60 | 336 de 336 |

### Una comparación que no valía

Intenté contrastar contra la pantalla que guardan las propias instantáneas, y
el resultado engañaba: salían coincidencias del cero por ciento de error. Al
mirar el mapa de diferencias se ve que esas pantallas no tienen lámina
dibujada, así que lo que coincidía eran dos imágenes casi vacías. Para
contrastar de verdad hay que ejecutar el juego hasta que dibuje.

## La versión de Amstrad CPC, leída entera

Las aventuras de CPC vienen en disco, y de ahí salen los ficheros sin encender
nada: el directorio de AMSDOS dice dónde está cada uno y su cabecera dice a qué
dirección se carga. `CARVALHO.FAC`, que es Los pájaros de Bangkok, se carga en
$0040 y ocupa hasta $A2F4, y trae dentro el intérprete y la aventura. En $4000
están los punteros en fila, tal como decía el decompilador de referencia, y en
$4012 el de las láminas. Con eso se lee el intérprete del CPC igual que se leyó
el del Spectrum, pero sin emulador de por medio.

### Las órdenes y sus argumentos

El repertorio es más corto que el del Spectrum: 1 recta, 2 elipse, 3 relleno,
8 rectángulo, 9 color, A llamada, B punto, y el 0 termina. Cualquier otro byte
cae en el caso por defecto, que fija la pluma con la que se dibuja. No hay
relleno de fondo ni media tinta aparte, porque aquí no hacen falta.

Los argumentos van en parejas, y **el segundo byte de cada pareja lleva siempre
el bit 7 puesto**; el intérprete lo quita al leerlo, con un `RES 7,E`. Por eso
la y de una lámina va de 0 a 127: la lámina del CPC mide 256 por 128, los
mismos números que la del Spectrum. El que escribe las láminas hace lo propio
al revés, con un `OR $80` sobre el byte alto.

### Sí escalaba, con una sola perilla

Cada coordenada pasa por lo mismo antes de dibujarse: se multiplica por un
factor de un byte, se divide por 64 y se le suma un origen, uno para la x y
otro para la y. El factor que trae el fichero es 128, que en las coordenadas
del firmware del CPC, que van de 0 a 639 por 0 a 399 sea cual sea el modo, deja
la lámina a tamaño natural, un píxel por punto.

Así que la lámina no se estira, pero **la perilla para estirarla está puesta**:
un byte de escala y dos orígenes colocan los mismos datos en cualquier
pantalla. Eso es exactamente lo que le hace falta al PCW, y no hay que
inventarlo.

### Se apoya en el firmware, como el Spectrum en su ROM

Mover, trazar la recta, poner el punto, preguntar por un punto, elegir pluma,
fijar el origen, la ventana y borrarla: todo eso lo pide a la máquina. El
Spectrum hacía lo mismo con su ROM. Lo que ninguna de las dos delega es el
relleno.

### El relleno, y el atajo que nos faltaba

El modelo es el mismo que en el Spectrum: recorrer la columna de la semilla
hacia arriba y hacia abajo tendiendo un tramo horizontal en cada fila. Lo que
cambia es cómo busca los extremos del tramo, y aquí está lo que llevábamos
buscando.

Antes de empezar pregunta por el punto de la semilla, y con el número de pluma
que le devuelven monta un byte en el que los cuatro píxeles son esa pluma. Ese
byte es la referencia. Para buscar el extremo hace un `XOR` de la referencia
contra el byte de pantalla: si la parte que toca al píxel no sale cero, ahí se
acaba el tramo. Y cuando el recorrido entra en un byte nuevo, compara el byte
entero: **si todo el byte coincide con la referencia, se lleva sus cuatro
píxeles de una vez** y salta al siguiente.

Es la optimización por bytes que intenté y deshice. El original la tiene, hecha
así: comparar primero el byte completo, y sólo bajar a máscara de bit en los
dos extremos.

### El color es una trama de dos plumas

La orden 9 lleva dos números de pluma. El intérprete convierte cada uno en su
byte de cuatro píxeles, se queda con las columnas pares del primero y las
impares del segundo, y los junta. Eso da un damero de las dos plumas. Después
guarda el mismo byte con las dos plumas intercambiadas, para las filas
alternas.

Es la pareja de patrones del Spectrum, generalizada: con las dos plumas iguales
sale un color sólido, y con dos distintas sale una mezcla que en modo 1 da
muchos más colores de los cuatro que hay. En una máquina de un bit por píxel
las dos plumas sólo pueden ser negro y blanco, y de ahí salen exactamente los
tres rellenos del Spectrum: lleno, vacío y damero. El PCW no necesita un modelo
de color propio, le basta esta orden.

### La elipse es la misma, byte por byte

En $22B0 está la tabla de dieciséis valores, la misma que el Spectrum guarda en
$A1ED, sin una cifra distinta. El primer par de la orden es el centro y el
segundo da los radios, como allí. Queda demostrado que la geometría de las
láminas no depende de la máquina.

### El dibujo, en cambio, no se reaprovechó

Las láminas no son las mismas. La versión de CPC de Bangkok trae 44 y la de
Spectrum 32, y no coincide ninguna, ni siquiera corrigiendo el origen de la y.
Se volvieron a dibujar para la máquina.

### Leer una aventura de Amstrad

`deGAC` las lee, con `-m cpc` cuando lo que se le da es una imagen plana de
memoria como la que saca `disk.py`. Las coordenadas salen ya en las del
Spectrum: la y se le quita el bit 7, que allí siempre está puesto, y se le
suman 48, porque la lámina mide 128 filas en las dos máquinas y lo único que
cambia es desde dónde se cuentan.

Las órdenes de color no tienen equivalente exacto. La que lleva dos plumas se
parte en tinta y papel, y la que fija una sola pluma queda como tinta. Los ocho
bytes de cabecera de cada lámina no caben entre las órdenes, así que se guardan
aparte, en `gfx_inks`, para no perder lo único que dice de qué color iba.

### Las mismas escenas, dibujadas otra vez

Con eso se pueden poner las dos versiones de Los pájaros de Bangkok una al
lado de la otra. Los cuartos llevan el mismo número en las dos, así que se
emparejan solas, y de cuarenta que tienen lámina en ambas salen veintiséis
parejas distintas.

Son las mismas escenas y ninguna es la misma lámina. El autobús con la cara
del hombre, la calle con sus dos edificios, el corro de gente, la mujer: se
reconocen todas, pero están vueltas a dibujar, con más color en pantalla y más
detalle, y sin el marco que el Spectrum pinta alrededor. No coincide ni una
sola orden, ni corrigiendo el origen de la y.

Para verlas hizo falta un dispositivo que dibuje como el Amstrad, porque con
el modelo del Spectrum salen manchas planas: un relleno que allí se para al
cambiar de pluma aquí se lo lleva todo por delante. Está en
[`AmstradDevice`](../regac/devices.py).

### Contrastarlo contra la máquina

Lo anterior no bastaba: las láminas seguían saliendo con fallos, y sólo se
podía saber preguntándole a un Amstrad. El cargador del disco quiere una
comilla tecleada en BASIC que el emulador no manda, así que la aventura entra
en memoria a mano, en la dirección que dice su propia cabecera, y la arranca un
`CALL` en decimal. Desde ahí se lee la pantalla y se convierte en números de
pluma, que es una comparación que no depende de los colores. Y escribiendo un
cero en medio de las órdenes de una lámina se la corta donde se quiera, que es
lo que permite ir acorralando un fallo.

Con eso salieron cuatro cosas:

**La lámina se dibuja en el 32,1 de la pantalla**, no pegada a la esquina.

**Empieza con la pluma 1**, y eso no lo dice el dato en ninguna parte: el marco
que pinta cada cuarto no lleva ni una orden de color y sale amarillo.

**Los ocho bytes de cabecera no son órdenes.** Merecía la pena probarlo porque
habría explicado el marco: cambiando el último en la máquina, lo que dibuja no
se mueve.

**El damero elige pluma por la y de las órdenes, no por la fila de pantalla.**
Es un bit de diferencia y volvía del revés todas las tramas. Esto solo llevó
una lámina entera del 89 al 99 por ciento.

Cómo queda, midiendo contra la pantalla de la máquina:

| lo que se dibuja | coincide |
|---|---|
| sólo el marco | 100,00% |
| el marco y la lámina 3 | 99,36% |
| el cuarto del aeropuerto entero | 99,15% |

### La recta del Amstrad da igual por qué punta se empiece

Se midió dibujando rectas de extremos conocidos en la máquina y anotando qué
puntos encendía. Siete rectas bastaron, y dicen dos cosas.

La primera: **ir de A a B enciende exactamente los mismos puntos que ir de B a
A**. La ROM del Spectrum no hace eso; dónde caen los pasos diagonales depende
de por qué punta se empiece.

La segunda: en cuanto se ponen las dos puntas en orden a lo largo del lado
mayor, el resto es el mismo Bresenham que ya teníamos, error a la mitad del
lado mayor, subiendo por el menor, y paso diagonal al alcanzarlo. Con eso las
siete rectas salen exactas.

### La elipse, que sigue sin cuadrar

Es lo único que queda, y no está resuelto. Lo medido, para quien lo retome:

Una elipse de radio 30 da 168 puntos en la máquina y 168 en el nuestro, y
sesenta y cuatro caen corridos un píxel. De los treinta y dos vértices que
calculamos, doce no están en la curva que dibuja la máquina, y los doce son de
los cuartos en los que el radio se **resta** del centro; el cuarto en el que
las dos coordenadas se suman sale entero.

Lo que dice el código del Amstrad es que no debería haber diferencia. La rutina
de $22C0 saca las dos distancias como el byte alto de radio por tabla, y cada
cuarto las suma o las resta con `ADD HL,BC` o `SBC HL,BC`, sin más. Leído así,
sumar y restar tendrían que ser simétricos.

Probado y descartado: redondear hacia afuera al restar (queda mucho peor, 60
puntos de 168), redondear al más cercano, y ordenar las puntas de las rectas
empinadas al revés. Y una comprobación que desconcierta: el tramo que va del
lado izquierdo hacia abajo, dibujado suelto como una orden de recta, sale en la
máquina exactamente igual que en el nuestro, con los mismos seis puntos; dentro
de la elipse, en cambio, la máquina pone uno de ellos una columna más a la
izquierda. O los vértices no son los que creemos, o la recta del firmware no
hace lo mismo cuando encadena que cuando empieza con un movimiento.

Con todo lo demás puesto, un cuarto entero se queda en el 99,2 por ciento.

### Lo que no está claro todavía

Cada lámina empieza con ocho bytes que no son órdenes. Van en cuatro parejas y
las dos mitades de cada pareja son siempre iguales. Los valores son un color de
0 a 26, que es justo la gama del CPC, más tres bits sueltos por encima. Leído
así son las cuatro tintas de la lámina, con la pareja repetida porque una tinta
del CPC admite dos colores y parpadea si difieren. Para qué son los tres bits
de arriba no lo sé todavía.

## Lo que queda por confirmar

La diferencia exacta entre `FILL` y `BGFILL` se ha deducido, no verificado
contra la máquina real. Igual que la trama concreta que pinta `SHADE`, que aquí
es un damero de un píxel. Ambas cosas se pueden comprobar comparando una lámina
con la que saca un emulador ejecutando la aventura original.
