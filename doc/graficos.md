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

## Lo que queda por confirmar

La diferencia exacta entre `FILL` y `BGFILL` se ha deducido, no verificado
contra la máquina real. Igual que la trama concreta que pinta `SHADE`, que aquí
es un damero de un píxel. Ambas cosas se pueden comprobar comparando una lámina
con la que saca un emulador ejecutando la aventura original.
