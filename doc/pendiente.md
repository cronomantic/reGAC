# Pendiente

Estado a 13 de septiembre de 2026, para retomarlo sin tener que reconstruir el
contexto.

## Lo inmediato, en orden

**Buscar los extremos de un tramo por bytes.** Es lo que falta para la
velocidad. Hoy la búsqueda va píxel a píxel rotando una máscara; el original
mira el byte entero cuando entra en uno nuevo y, si vale cero, se lleva los
ocho píxeles de una vez. Lo escribí, ensambla, y rompe tres de las once
comprobaciones de primitivas, así que está revertido. El fallo estará en el
cruce de byte, en el momento de pasar de la máscara al byte completo y volver.

**Volver a pasar las 196 láminas.** La última pasada completa dio 192 de 196, y
las cuatro que fallaban ya están arregladas, así que debería dar 196. Son unos
quince minutos de máquina sin intervención con el guion que hay en el
directorio temporal de la sesión; conviene meterlo en `tests/` como prueba
lenta marcada aparte. Importante: no reensamblar mientras corre, que es lo que
me tumbó la última.

**Objetivo de velocidad: cuatro o cinco segundos en el peor caso.** Ahora el
peor caso son 23 segundos y la mayoría están por debajo de doce. La búsqueda
por bytes debería dar el factor que falta; si no llega, lo siguiente que
miraría es el trazado de rectas, que en las láminas con muchas rectas cortas
pesa más que el relleno.

## Del intérprete

Cuatro opcodes siguen sin hacer nada, y los cuatro necesitaban el bucle
principal para tener dónde engancharse: la espera de tecla, la cinta, el disco
y la confirmación que pide salir.

Falta partir la línea tecleada en varias órdenes separadas por conectores. El
vocabulario de las aventuras españolas no trae los separadores en inglés que
deGAC pone por defecto, así que hay que decidir de dónde salen.

## Las máquinas

En Python están modeladas Spectrum, Sam Coupé, Next, MSX1, MSX2 y Amstrad, y
las seis dibujan las láminas igual que el Spectrum. En Z80 sólo existe el
Spectrum.

### Amstrad PCW, target nuevo

Merece la pena porque es Z80 y porque no se parece a ninguna de las otras, así
que obliga a que la separación entre intérprete y máquina sea real.

**Monocromo.** 720 por 256 píxeles y ni un color. Todo el modelo de tinta,
papel, brillo y parpadeo se queda sin sitio donde ir, y la única manera de
mostrar tonos es la trama. Es la máquina que pone a prueba de verdad que el
intérprete de láminas no sepa nada de color: hoy pide al dispositivo que fije
los colores en curso, y el del PCW tendrá que traducirlos a tramas o a nada.

**El ancho no obliga a escalar.** Con 720 de ancho cabe la lámina de 256
centrada, que es la regla que ya establecimos y que evita que los rellenos se
escapen. Si se quisiera aprovechar la pantalla, el doble exacto son 512 y sí
sería seguro, pero **doblando los píxeles del resultado, no volviendo a trazar
al doble de tamaño**: doblar píxeles conserva la lámina exactamente, volver a
trazar reabre el problema que medimos con el Amstrad.

**Memoria de sobra**, 256K o más en bloques de 16K, que encaja con el reparto
por bancos que ya tiene el formato binario.

**No hay AY.** Sólo un zumbador, así que toda la previsión de música que
condiciona el reparto de bancos no aplica aquí. La sección de música del
formato seguirá estando, vacía, y este destino no necesitará ni buffer
residente ni ranura propia.

**Por confirmar antes de escribir nada**: la disposición exacta de la memoria
de pantalla, que no es lineal ni como la del Spectrum, y cómo se lee el
teclado.

### Mirar las versiones de CPC, que es la lección para el PCW

Sergio puede conseguir las mismas aventuras en su versión de Amstrad CPC. Es la
mejor fuente que hay para el PCW, porque es el único sitio donde se ve qué hizo
el original al llevar las láminas a una máquina que no es el Spectrum. Hacen
falta instantáneas de CPCEMU, que empiezan por `MV - SNA`; el decompilador de
referencia ya las lee y sitúa la base de datos en $210C.

Leyendo ese decompilador ya se sacan cuatro cosas, antes incluso de tener las
instantáneas:

**La geometría es la misma y el color no.** Recta, elipse, rectángulo, punto,
relleno, trama y llamada existen en las dos máquinas con los mismos argumentos.
Lo que cambia por completo es el color: el Spectrum tiene tinta, papel, brillo,
parpadeo y borde, cada uno con su argumento, y el CPC tiene cuatro tintas
metidas en el propio opcode y nada más. La numeración de los opcodes tampoco
coincide en nada. Es justo la separación que ya hicimos entre el intérprete de
láminas y el dispositivo, confirmada por el original.

**Nadie reescaló las coordenadas.** Son los mismos bytes en las dos máquinas,
así que el ajuste a la pantalla lo hace la máquina y no el dato. Eso respalda
centrar la lámina de 256 en los 720 del PCW.

**El CPC guarda una paleta por lámina**, ocho bytes a la cabeza de cada
registro, antes de las órdenes. Es la respuesta del original a la pregunta que
nuestro `choose_inks` resuelve adivinando: las tintas no se deducían del uso,
se guardaban. En el PCW ese mismo hueco es el que diría qué trama representa a
cada tinta.

**El lenguaje de láminas se amplió por máquina.** El CPC tiene cuatro órdenes
de espejo y volteo que el Spectrum no tiene, y no tiene relleno de fondo.
Añadir órdenes propias de una máquina no rompe nada, es lo que ya se hacía.

Y lo que hay que sacar de las instantáneas cuando estén:

- Las tramas del relleno. Con cuatro colores por píxel, dos bits cada uno, los
  bytes $FF, $00 y $AA no pueden significar lo mismo. Cómo expresaron ahí el
  sólido, el borrado y la media tinta es el molde para las tramas del PCW.
- La prueba de bloqueo. En el Spectrum un punto detiene el relleno si está
  encendido; con dos bits por píxel hay que decidir contra qué se compara, y
  esa decisión es la que hace falta entender.
- Si la tabla de la elipse y el trazado de rectas son los mismos. Si lo son,
  queda demostrado que sólo cambian las seis primitivas.
- Qué hace la paleta de ocho bytes con las tintas del Spectrum.

## Cosas menores

`deGAC` sólo lee instantáneas de Spectrum. El decompilador de referencia en C
también entiende las de Amstrad y Commodore 64, lo que ampliaría el catálogo de
aventuras recuperables.

El intérprete de Python casa palabras por prefijo, y el original y el nuestro
casan la palabra entera. Conviene alinearlo o dejar dicho por qué no.
