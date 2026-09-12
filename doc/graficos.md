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

El error de bulto fue suponer que rellenar encendía los píxeles. Con eso, un
relleno del fondo de una habitación la dejaba en negro entera y se comía el
dibujo. En el Spectrum una zona de color plano se consigue dejando los píxeles
apagados y poniendo el color de fondo de esas celdas, que además respeta el
trazado ya dibujado.

La prueba de que `BGFILL` trabaja sobre el color de fondo está en los propios
datos. Contando qué comando sigue a cada cambio de color en las ocho
aventuras, `PAPER` va seguido de `BGFILL` algo más de la mitad de las veces y
de `FILL` sólo el tres por ciento. `INK`, en cambio, va seguido de trazado y de
`FILL`.

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

## Lo que queda por confirmar

La diferencia exacta entre `FILL` y `BGFILL` se ha deducido, no verificado
contra la máquina real. Igual que la trama concreta que pinta `SHADE`, que aquí
es un damero de un píxel. Ambas cosas se pueden comprobar comparando una lámina
con la que saca un emulador ejecutando la aventura original.
