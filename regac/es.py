# ReGAC, tools for Graphic Adventure Creator adventures.
#
# Copyright (C) 2025 Cronomantic
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
#
# The interpreters in z80/ are not part of this program and are given under
# the MIT licence instead: see z80/LICENSE.
#
"""What the tools say, in Spanish: every message of i18n._, by its English.

The holes between braces are the same in both, and tests/test_i18n.py says
when one is missing, left over or different.  The words are the ones the
Spanish documentation uses: sala, lámina, orden, relleno, tinta,
tipografía, bandera, contador, fuente, base de datos."""

SAID = {
    # -- regac, the command ---------------------------------------------------
    "ERROR: {what}": "ERROR: {what}",
    "{name}: round trip exact": "{name}: la ida y vuelta sale exacta",
    "{name}: round trip differs in {parts}":
        "{name}: la ida y vuelta difiere en {parts}",
    "{name}: {faults} faults and {warnings} warnings":
        "{name}: {faults} fallos y {warnings} avisos",
    "{name}: nothing points anywhere it should not":
        "{name}: nada apunta a donde no debe",
    "ERROR: {output} must be a directory for more than one picture":
        "ERROR: {output} tiene que ser una carpeta para más de una lámina",
    "ERROR: there is no picture {picture}":
        "ERROR: no hay lámina {picture}",
    "picture {picture} -> {path}": "lámina {picture} -> {path}",
    "ERROR: there is nothing to draw {machine} with; try one of {machines}":
        "ERROR: no hay con qué dibujar para {machine}; las que hay: "
        "{machines}",
    "-- the orders ran out with the game still asking":
        "-- se acabaron las órdenes y el juego seguía pidiendo",
    "-- the game ended without saying {expected!r}":
        "-- el juego acabó sin decir {expected!r}",
    "-- the game ended": "-- el juego acabó",
    "nothing that nothing uses": "nada que no se use",
    "{name} was written on an Amstrad: its pictures are drawn with the "
    "Amstrad's rules and there is no Spectrum to compare them with":
        "{name} se escribió en un Amstrad: sus láminas se dibujan con las "
        "reglas del Amstrad y no hay Spectrum con el que compararlas",
    "  picture {picture}: the two runs filled a different number of times":
        "  lámina {picture}: las dos pasadas rellenaron un número distinto "
        "de veces",
    "  picture {picture}, fill {fill}: covers {there:.0%} of the screen on "
    "the spectrum but {here:.0%} on the {machine}":
        "  lámina {picture}, relleno {fill}: cubre el {there:.0%} de la "
        "pantalla en el spectrum pero el {here:.0%} en {machine}",
    "{name}: {fills} fills differ on the {machine}":
        "{name}: {fills} rellenos difieren en {machine}",
    "{name}: every fill covers the same ground on the {machine}":
        "{name}: cada relleno cubre lo mismo en {machine}",
    "  characters      {n}": "  caracteres      {n}",
    "  packed          {n}": "  empaquetado     {n}",
    "  pair table      {n} ({pairs} pairs)":
        "  tabla de pares  {n} ({pairs} pares)",
    "  total           {n}  ({ratio:.0%} of the original)":
        "  total           {n}  ({ratio:.0%} del original)",
    "  glyphs needed   {n}": "  glifos precisos {n}",
    "  spare codes     {n}": "  códigos libres  {n}",
    "  unpacking stack {n} bytes": "  pila (desemp.)  {n} bytes",
    "  noises      {n}": "  ruidos      {n}",
    "  machine     {machine}": "  máquina     {machine}",
    "  image       {n} bytes": "  imagen      {n} bytes",
    "  resident    {n} bytes": "  residente   {n} bytes",
    "  banks       {n}": "  bancos      {n}",
    "bank {bank}": "banco {bank}",
    "resident": "residente",
    "ERROR: a pcw release wants --boot and --database":
        "ERROR: una versión para pcw necesita --boot y --database",
    "nothing: the machine starts it, with {banks} banks behind it":
        "nada: la máquina lo arranca sola, con {banks} bancos detrás",
    'BLOAD"CAS:",R, with a screen and {n} bytes behind it':
        'BLOAD"CAS:",R, con una pantalla y {n} bytes detrás',
    'BLOAD"CAS:",R, with {n} bytes behind it':
        'BLOAD"CAS:",R, con {n} bytes detrás',
    "ERROR: a cpc6128 release wants --database":
        "ERROR: una versión para cpc6128 necesita --database",
    'RUN"{name}" on the disk, with {banks} banks behind it':
        'RUN"{name}" en el disco, con {banks} bancos detrás',
    'RUN"" on the tape, with the interpreter under the database':
        'RUN"" en la cinta, con el intérprete debajo de la base de datos',
    'RUN"" on the tape': 'RUN"" en la cinta',
    "the Loader entry of its menu, and {banks} banks":
        "la entrada Loader de su menú, y {banks} bancos",
    "the Loader entry of the machine's own menu":
        "la entrada Loader del menú de la propia máquina",
    "ERROR: a {machine} screen is {wanted} bytes and {screen} is {size}":
        "ERROR: una pantalla de {machine} son {wanted} bytes y {screen} "
        "tiene {size}",
    "  loads at    ${load:04X}, {n} bytes":
        "  carga en    ${load:04X}, {n} bytes",
    "  starts with {how}": "  arranca con {how}",
    "ERROR: the project says nothing about {machine}":
        "ERROR: el proyecto no dice nada de {machine}",
    "ERROR: {machine}: {what}": "ERROR: {machine}: {what}",
    "  {machine:12} does not fit the usual way round: the interpreter goes "
    "under the database":
        "  {machine:12} no cabe de la forma habitual: el intérprete va "
        "debajo de la base de datos",
    "ReGAC {version}": "ReGAC {version}",
    "JSON database -> .gac source": "base de datos JSON -> fuente .gac",
    "JSON database": "base de datos JSON",
    "source file to write": "fichero fuente que escribir",
    ".gac source -> JSON database": "fuente .gac -> base de datos JSON",
    "source file": "fichero fuente",
    "JSON database to write": "base de datos JSON que escribir",
    "which machine to read it for, for a source that keeps some lines for "
    "some of them":
        "para qué máquina leerla, en una fuente que guarda líneas para "
        "algunas de ellas",
    "draw the pictures of an adventure as PNG":
        "dibuja las láminas de una aventura en PNG",
    "PNG file, or a directory for several":
        "fichero PNG, o una carpeta para varias",
    "one picture id (default: all)": "el número de una lámina (si no, todas)",
    "pixel scale": "escala del píxel",
    "which machine to draw for (default: spectrum)":
        "para qué máquina dibujar (si no, spectrum)",
    "look at a picture in a window, drawn again whenever the source is saved":
        "mira una lámina en una ventana, que se vuelve a dibujar cada vez que "
        "se guarda la fuente",
    "source file, or JSON database": "fichero fuente, o base de datos JSON",
    "which picture (default: the first)": "qué lámina (si no, la primera)",
    "which machine to draw it as: spectrum, cpc, msx, pcw, next or cga, "
    "which is the PC's (default: the first the adventure can be drawn on)":
        "como qué máquina dibujarla: spectrum, cpc, msx, pcw, next o cga, "
        "que es la del PC (si no, la primera en la que la aventura se puede "
        "dibujar)",
    "an image to draw over, or a folder with one to each picture, named "
    "12.png":
        "una imagen sobre la que calcar, o una carpeta con una para cada "
        "lámina, llamada 12.png",
    "play a file of orders, and say whether the game ended":
        "juega un fichero de órdenes, y dice si el juego acabó",
    "a file of orders, one a line": "un fichero de órdenes, una por línea",
    "and it has to have said this": "y tiene que haber dicho esto",
    "which machine to read a source for": "para qué máquina leer una fuente",
    "what the adventure has that nothing uses: rooms, objects, words, "
    "messages":
        "lo que la aventura tiene y nada usa: salas, objetos, palabras, "
        "mensajes",
    "the map of an adventure, as SVG": "el mapa de una aventura, en SVG",
    "SVG file to write": "fichero SVG que escribir",
    "which machine to read a source for, for one that keeps some lines for "
    "some of them":
        "para qué máquina leer una fuente, en una que guarda líneas para "
        "algunas de ellas",
    "compare the pictures on a machine against the Spectrum":
        "compara las láminas en una máquina con las del Spectrum",
    "how much of the screen a fill may differ by (default: 0.05)":
        "cuánta pantalla puede diferir un relleno (si no, 0.05)",
    "write the binary database for a machine":
        "escribe la base de datos binaria para una máquina",
    "binary file to write": "fichero binario que escribir",
    "size of a memory bank, or none to keep everything resident":
        "tamaño de un banco de memoria, o none para que todo sea residente",
    "write the source that says what noises there are, for the assembler to "
    "include":
        "escribe la fuente que dice qué ruidos hay, para que la incluya el "
        "ensamblador",
    "write an assembler include saying where the banks start":
        "escribe un include para el ensamblador que dice dónde empiezan los "
        "bancos",
    "put an assembled interpreter on a disk and a tape":
        "pone un intérprete ensamblado en un disco y una cinta",
    "the binary the assembler wrote": "el binario que escribió el ensamblador",
    "where to write the disk and the tape": "dónde escribir el disco y la cinta",
    "what the files are called": "cómo se llaman los ficheros",
    "where the binary loads, if not where that machine has it":
        "dónde carga el binario, si no es donde lo tiene esa máquina",
    "where it starts, if not where it loads":
        "dónde arranca, si no es donde carga",
    "the assembled loader, for a +3 with banks":
        "el cargador ensamblado, para un +3 con bancos",
    "the built database the banks come from":
        "la base de datos construida de la que salen los bancos",
    "a dump of the machine's screen, to show while the rest loads":
        "un volcado de la pantalla de la máquina, para enseñarlo mientras "
        "carga el resto",
    "build an adventure for every machine a project file names":
        "construye una aventura para cada máquina que nombra un fichero de "
        "proyecto",
    "the project file": "el fichero de proyecto",
    "where the media go, if not where the project says":
        "dónde van los discos y cintas, si no es donde dice el proyecto",
    "only this machine, and again for more than one":
        "sólo esta máquina, y otra vez para más de una",
    "and everything it built in this zip file, a folder a machine":
        "y todo lo construido en este zip, una carpeta por máquina",
    "report what the text costs once packed":
        "dice cuánto ocupa el texto una vez empaquetado",
    "verify that an adventure survives a round trip and points nowhere it "
    "should not":
        "comprueba que una aventura sobrevive a la ida y vuelta y no apunta "
        "a donde no debe",
    "ERROR: {path} is not a JSON database ({why}); a source is made into one "
    "with regac compile":
        "ERROR: {path} no es una base de datos JSON ({why}); una fuente se "
        "convierte en una con regac compile",
    "ERROR: {path} is not a JSON database ({why})":
        "ERROR: {path} no es una base de datos JSON ({why})",

    # -- binary ---------------------------------------------------------------
    "constant {value} does not fit": "la constante {value} no cabe",
    "unknown opcode {name!r}": "código de operación desconocido {name!r}",
    "unknown machine {machine!r}": "máquina desconocida {machine!r}",
    "this adventure was written on an Amstrad, and its pictures are drawn "
    "with the Amstrad's rules; {machine} does not know them; {some} and "
    "{last} do":
        "esta aventura se escribió en un Amstrad, y sus láminas se dibujan "
        "con las reglas del Amstrad; {machine} no las conoce; {some} y "
        "{last} sí",
    "object {object} names an object in its name, which an object's name "
    "may not do":
        "el objeto {object} nombra un objeto en su nombre, y el nombre de "
        "un objeto no puede hacerlo",
    "picture {picture} has {inks} inks where an Amstrad picture has {wanted}":
        "la lámina {picture} tiene {inks} tintas donde una lámina de Amstrad "
        "tiene {wanted}",
    "picture {picture} has an ink that is not one of the Amstrad's, which "
    "go from 0 to 26":
        "la lámina {picture} tiene una tinta que no es del Amstrad, que van "
        "de 0 a 26",
    "{word!r} and {other!r} are the same word once the marks come off, and "
    "a player types them the same way":
        "{word!r} y {other!r} son la misma palabra sin las tildes, y un "
        "jugador las teclea igual",
    "unknown graphics command {name!r}":
        "orden de dibujo desconocida {name!r}",
    "the {section} section is {size} bytes and a PC reaches {most} of one":
        "la sección {section} ocupa {size} bytes y un PC alcanza {most} de "
        "una",
    "the {section} section is {size} bytes and a bank holds {page}":
        "la sección {section} ocupa {size} bytes y en un banco caben {page}",
    "not a reGAC database": "no es una base de datos de reGAC",

    # -- cautions -------------------------------------------------------------
    "{order}: fills nothing, its seed is on a pixel already set":
        "{order}: no rellena nada, su semilla está en un píxel ya puesto",
    "{order}: got out at y {y}, right to x {x}, by a gap a pixel high":
        "{order}: se escapó en y {y}, a la derecha hasta x {x}, por un "
        "hueco de un píxel de alto",
    "{order}: got out at y {y}, left to x {x}, by a gap a pixel high":
        "{order}: se escapó en y {y}, a la izquierda hasta x {x}, por un "
        "hueco de un píxel de alto",
    "#{picture} takes {bytes} bytes; all the pictures, {every}":
        "#{picture} ocupa {bytes} bytes; todas las láminas, {every}",

    # -- cdt ------------------------------------------------------------------
    "{name} is longer than a tape name can be":
        "{name} es más largo de lo que puede ser un nombre en la cinta",

    # -- check ----------------------------------------------------------------
    "to ask the player for an order": "para pedir una orden al jugador",
    "to say an order cannot be done":
        "para decir que una orden no se puede hacer",
    "to say an order was not understood":
        "para decir que una orden no se ha entendido",
    "to ask for a key": "para pedir una tecla",
    "to ask whether the player is sure":
        "para preguntar si el jugador está seguro",
    "to say the player has not got it": "para decir que el jugador no lo tiene",
    "to say there is nothing like that here":
        "para decir que no hay nada así aquí",
    "to say the player is carrying too much":
        "para decir que el jugador lleva demasiado",
    "to say it is dark": "para decir que está oscuro",
    "to introduce what can be seen": "para presentar lo que se ve",
    "to say it is done": "para decir que está hecho",
    "warning: {where}: {message}": "aviso: {where}: {message}",
    "{op} {value}, and there is no message {value}":
        "{op} {value}, y no hay mensaje {value}",
    "{op} {value}, and there is no room {value}":
        "{op} {value}, y no hay sala {value}",
    "{op} {value}, and there is no /PROC {value}":
        "{op} {value}, y no hay /PROC {value}",
    "{op} {value}, and there is no object {value}":
        "{op} {value}, y no hay objeto {value}",
    "{op} {value}, and there are {counters} counters, numbered 0 to {last}":
        "{op} {value}, y hay {counters} contadores, numerados de 0 a {last}",
    "{op} {value}, and there are 256 flags, numbered 0 to 255":
        "{op} {value}, y hay 256 banderas, numeradas de 0 a 255",
    "{op} {value}, and no word of the vocabulary has that number":
        "{op} {value}, y ninguna palabra del vocabulario tiene ese número",
    "SOUND 0, and effects are numbered from one":
        "SOUND 0, y los efectos se numeran desde uno",
    "SOUND {value}, and this adventure says what {noises} noises it has":
        "SOUND {value}, y esta aventura dice qué {noises} ruidos tiene",
    "message {n}": "mensaje {n}",
    "room {n}": "sala {n}",
    "object {n}": "objeto {n}",
    "\\obj {value} in the name of an object, which may not name one":
        "\\obj {value} en el nombre de un objeto, que no puede nombrar otro",
    "\\obj {value}, and there is no object {value}":
        "\\obj {value}, y no hay objeto {value}",
    "the high priority conditions": "las condiciones de alta prioridad",
    "the low priority conditions": "las condiciones de baja prioridad",
    "the local conditions of room {n}":
        "las condiciones locales de la sala {n}",
    "procedure {n}": "la tabla /PROC {n}",
    "the control section": "la sección de control",
    "the player starts in room {room}, which is not there":
        "el jugador empieza en la sala {room}, que no existe",
    "a way out goes to room {room}, which is not there":
        "una salida va a la sala {room}, que no existe",
    "it shows picture {picture}, which is not there":
        "enseña la lámina {picture}, que no existe",
    "it starts in room {room}, which is not there":
        "empieza en la sala {room}, que no existe",
    "it calls picture {picture}, which is not there":
        "llama a la lámina {picture}, que no existe",
    "picture {n}": "lámina {n}",
    "its order {number}, {order}, goes to y={y}, outside the frame "
    "({bottom} to {top}): this draws what fits, where the original would "
    "have stopped drawing the picture there":
        "su orden {number}, {order}, va a y={y}, fuera del marco ({bottom} "
        "a {top}): aquí se dibuja lo que cabe, donde el original habría "
        "dejado de dibujar la lámina ahí",
    "its order {number}, {order}, starts at y={y}, outside the frame "
    "({bottom} to {top}): this lays nothing, where the original filled "
    "from there upwards, into the text window as well":
        "su orden {number}, {order}, empieza en y={y}, fuera del marco "
        "({bottom} a {top}): aquí no pone nada, donde el original rellenaba "
        "de ahí hacia arriba, también en la ventana de texto",
    "its order {number}, {order}, starts at y={y}, outside the frame "
    "({bottom} to {top}): this lays nothing, where the original filled "
    "from the top of the picture down, or did nothing, or hung, depending "
    "on how far above":
        "su orden {number}, {order}, empieza en y={y}, fuera del marco "
        "({bottom} a {top}): aquí no pone nada, donde el original rellenaba "
        "desde lo alto de la lámina hacia abajo, o no hacía nada, o se "
        "colgaba, según lo arriba que estuviera",
    "message {number} is missing, and the interpreter needs it {what}":
        "falta el mensaje {number}, y el intérprete lo necesita {what}",
    "the messages": "los mensajes",
    "message {number} is missing, which the interpreter reaches for {what}":
        "falta el mensaje {number}, al que el intérprete acude {what}",
    "the font": "la tipografía",
    'there is not one: every letter would print blank.  A source says '
    '/FONT file="...", or draws the letters it wants one at a time':
        'no hay: todas las letras saldrían en blanco.  Una fuente dice '
        '/FONT file="...", o dibuja una a una las letras que quiere',
    "the nouns": "los nombres",
    "the verbs": "los verbos",
    "the adverbs": "los adverbios",
    "{word} ({number}) is the same word as {first} ({its}) once the marks "
    "come off, so only the first can ever be typed":
        "{word} ({number}) es la misma palabra que {first} ({its}) sin las "
        "tildes, así que sólo la primera se puede teclear",

    # -- conds ----------------------------------------------------------------
    "the condition stops in the middle": "la condición se corta a la mitad",
    "expected {wanted!r}, found {got!r}":
        "se esperaba {wanted!r} y hay {got!r}",
    "unknown word {word!r}": "palabra desconocida {word!r}",
    "{op} goes between two things, so it cannot start one":
        "{op} va entre dos cosas, así que no puede empezar una",
    "line {n}: {what}": "línea {n}: {what}",
    "stack underflow": "la pila se queda vacía",
    "unknown opcode name {name!r}":
        "nombre de código de operación desconocido {name!r}",

    # -- devices --------------------------------------------------------------
    "unknown machine {name}; try one of {known}":
        "máquina desconocida {name}; las que hay: {known}",

    # -- dsk ------------------------------------------------------------------
    "{name} does not fit in eight and three":
        "{name} no cabe en ocho y tres",
    "{name} is on the disk already": "{name} ya está en el disco",
    "the disk is full": "el disco está lleno",
    "{name} is not on the disk": "{name} no está en el disco",
    "the directory is full": "el directorio está lleno",
    "the boot code is {count} bytes and {spare} fit":
        "el código de arranque ocupa {count} bytes y caben {spare}",
    "a table has to be told where it goes":
        "a una tabla hay que decirle dónde va",
    "there is no track {track} sector {sector}":
        "no hay pista {track} sector {sector}",

    # -- fontfile -------------------------------------------------------------
    "there are no bytes in this at all": "aquí no hay ningún byte",
    "this has {value} in it, which is not a byte: it does not look like a "
    "font written out as source":
        "esto tiene un {value}, que no es un byte: no parece una tipografía "
        "escrita como fuente",
    "a font is eight bytes a letter and this listing has {count}, which is "
    "not a whole number of them":
        "una tipografía son ocho bytes por letra y este listado tiene "
        "{count}, que no es un número entero de ellas",
    "this console font is {rows} rows tall, not eight":
        "esta tipografía de consola tiene {rows} filas de alto, no ocho",
    "this says it is a BDF but there are no glyphs in it":
        "esto dice que es un BDF pero no tiene glifos",
    "this stops looking like VDU 23 commands part way in":
        "esto deja de parecer órdenes VDU 23 a medio camino",
    "this has SYMBOL in it but no character it redefines":
        "esto tiene SYMBOL pero ningún carácter que redefina",
    "a font is eight bytes a letter and this is {count} bytes, which is not "
    "a whole number of them":
        "una tipografía son ocho bytes por letra y esto son {count} bytes, "
        "que no es un número entero de ellas",
    "this sheet is {width} by {height}, which is no way to lay out {wanted} "
    "cells of eight by eight or a whole multiple of them":
        "esta hoja mide {width} por {height}, y así no se pueden colocar "
        "{wanted} celdas de ocho por ocho ni de un múltiplo entero de eso",
    "a sheet of letters is a whole number of cells and this one is {width} "
    "by {height}":
        "una hoja de letras es un número entero de celdas y esta mide "
        "{width} por {height}",
    "no font is kept in {order} order; try one of {known}":
        "ninguna tipografía se guarda en orden {order}; los que hay: {known}",
    "there is no {layout} layout; try one of {known}":
        "no hay disposición {layout}; las que hay: {known}",
    "{count} bytes is not a font this knows: say how it is laid out with "
    "layout=, or where its first letter stands with first=":
        "{count} bytes no es una tipografía conocida: hay que decir cómo "
        "está dispuesta con layout=, o dónde está su primera letra con "
        "first=",
    "a {layout} font is {wanted} bytes and this is {count}":
        "una tipografía {layout} son {wanted} bytes y esta tiene {count}",

    # -- gfxedit --------------------------------------------------------------
    "a JSON is only looked at: open the source to draw":
        "un JSON sólo se mira: hay que abrir la fuente para dibujar",
    "the source does not read: {error}": "la fuente no se lee: {error}",
    "there is no picture {n} in the source":
        "no hay lámina {n} en la fuente",
    "picture {n} is written in {file}: open that one to draw in it":
        "la lámina {n} está escrita en {file}: hay que abrir ese para "
        "dibujar en ella",
    "picture {n} keeps lines for some machines, with .if: draw in it by hand":
        "la lámina {n} guarda líneas para algunas máquinas, con .if: se "
        "dibuja a mano",

    # -- argparse, its own words ----------------------------------------------
    "usage: ": "uso: ",
    "positional arguments": "argumentos",
    "options": "opciones",
    "show this help message and exit": "enseña esta ayuda y termina",
    " (default: %(default)s)": " (si no, %(default)s)",
    "%(prog)s: error: %(message)s\n": "%(prog)s: error: %(message)s\n",
    "argument %(argument_name)s: %(message)s":
        "argumento %(argument_name)s: %(message)s",
    "the following arguments are required: %s": "faltan estos argumentos: %s",
    "one of the arguments %s is required":
        "hace falta uno de los argumentos %s",
    "unrecognized arguments: %s": "argumentos que no se conocen: %s",
    "not allowed with argument %s": "no se admite con el argumento %s",
    "ambiguous option: %(option)s could match %(matches)s":
        "opción ambigua: %(option)s puede ser %(matches)s",
    "expected one argument": "se esperaba un argumento",
    "expected at most one argument": "se esperaba un argumento como mucho",
    "expected at least one argument": "se esperaba un argumento al menos",
    "invalid %(type)s value: %(value)r": "valor %(type)s no válido: %(value)r",
    "invalid choice: %(value)r (choose from %(choices)s)":
        "%(value)r no vale (se puede elegir entre %(choices)s)",

    # -- lint -----------------------------------------------------------------
    "a {op} works its word out while the game plays, so no verb is said to "
    "be unused":
        "un {op} calcula su palabra mientras se juega, así que de ningún "
        "verbo se dice que sobre",
    "a {op} works its word out while the game plays, so no noun is said to "
    "be unused":
        "un {op} calcula su palabra mientras se juega, así que de ningún "
        "nombre se dice que sobre",
    "a {op} works its word out while the game plays, so no adverb is said "
    "to be unused":
        "un {op} calcula su palabra mientras se juega, así que de ningún "
        "adverbio se dice que sobre",
    "the verb {word} ({number}): no condition asks for it":
        "el verbo {word} ({number}): ninguna condición lo pregunta",
    "the noun {word} ({number}): no condition asks for it":
        "el nombre {word} ({number}): ninguna condición lo pregunta",
    "the adverb {word} ({number}): no condition asks for it":
        "el adverbio {word} ({number}): ninguna condición lo pregunta",
    "a GOTO works its room out while the game plays, so which rooms are "
    "reached is not looked at":
        "un GOTO calcula su sala mientras se juega, así que no se mira "
        "a qué salas se llega",
    "rooms": "salas",
    "room {room}: no way out leads here and no GOTO names it":
        "sala {room}: ninguna salida lleva aquí y ningún GOTO la nombra",
    "object {number} cannot be picked up: it does not start carried, and no "
    "noun has its number for a GET of what is typed":
        "el objeto {number} no se puede coger: no empieza llevado, y ningún "
        "nombre tiene su número para un GET de lo tecleado",
    "object {number} cannot be picked up: it does not start carried, and no "
    "GET names it":
        "el objeto {number} no se puede coger: no empieza llevado, y ningún "
        "GET lo nombra",
    "objects": "objetos",
    "words": "palabras",
    "a MESS works its message out while the game plays, so which are "
    "printed is not looked at":
        "un MESS calcula su mensaje mientras se juega, así que no se mira "
        "cuáles se escriben",
    "messages": "mensajes",
    "message {number}: nothing prints it":
        "mensaje {number}: nada lo escribe",
    "picture {number}: no room shows it and no picture calls it":
        "lámina {number}: ninguna sala la enseña y ninguna lámina la "
        "llama",
    "pictures": "láminas",
    "a DO works its table out while the game plays, so which run is not "
    "looked at":
        "un DO calcula su tabla mientras se juega, así que no se mira "
        "cuáles corren",
    "procedures": "tablas /PROC",
    "procedure {number}: no DO runs it":
        "tabla /PROC {number}: ningún DO la corre",

    # -- mapper, measure, media, play, png ------------------------------------
    "no room left on the map": "no queda sitio en el mapa",
    "the time is measured on spectrum, cpc and msx, which have a build that "
    "draws one picture, and not on {machine}":
        "el tiempo se mide en spectrum, cpc y msx, que tienen una versión "
        "que dibuja una lámina, y no en {machine}",
    "measuring needs sjasmplus and ZEsarUX in tools/":
        "para medir hacen falta sjasmplus y ZEsarUX en tools/",
    "the {machine} never got going": "el {machine} no llegó a arrancar",
    "too many pieces to fit in the boot sector's table":
        "demasiados trozos para la tabla del sector de arranque",
    "the database is {count} bytes and {room} fit under the island, even "
    "with the interpreter out of the way":
        "la base de datos ocupa {count} bytes y debajo de la isla caben "
        "{room}, incluso quitando de en medio el intérprete",
    "a 6128 has {given} banks to give and this wants {wanted}":
        "un 6128 tiene {given} bancos que dar y esto quiere {wanted}",
    "the 6128's interpreter should start by jumping over the three bytes "
    "that say where the saved game is, and this one does not":
        "el intérprete del 6128 debería empezar saltando los tres bytes que "
        "dicen dónde está la partida guardada, y este no lo hace",
    "a stack of {stack} bytes is not one DOS can set up":
        "una pila de {stack} bytes no es una que DOS pueda preparar",
    "the interpreter would not start this adventure":
        "el intérprete no quiso arrancar esta aventura",
    "a row of this image is filtered with {kind}":
        "una fila de esta imagen está filtrada con {kind}",
    "this is not a PNG": "esto no es un PNG",
    "this PNG is interlaced, and this reader is not":
        "este PNG es entrelazado, y este lector no",
    "this PNG is of a kind ({colour}) this cannot read":
        "este PNG es de una clase ({colour}) que no se puede leer aquí",

    # -- project --------------------------------------------------------------
    "{path}: {keys} means nothing here": "{path}: {keys} no significa nada aquí",
    "{path}: it does not say what {key} is": "{path}: no dice qué es {key}",
    "{path}: it does not say which machines to build for":
        "{path}: no dice para qué máquinas construir",
    "{path}: there is no {machine}; try one of {machines}":
        "{path}: no hay {machine}; las que hay: {machines}",
    "{path}: {machine} says {keys}, which means nothing":
        "{path}: {machine} dice {keys}, que no significa nada",
    "{path}: {machine} cannot draw at {across} by {down}; it draws at "
    "{scales} across and one down":
        "{path}: {machine} no puede dibujar a {across} por {down}; dibuja a "
        "{scales} de ancho y uno de alto",
    "a scale is one number or two, as scale = 2 or scale = [2, 1], not "
    "{scale!r}":
        "una escala es un número o dos, como scale = 2 o scale = [2, 1], no "
        "{scale!r}",
    "sjasmplus is not in tools/ and not on the path":
        "sjasmplus no está en tools/ ni en el PATH",
    "nasm is not in tools/ and not on the path":
        "nasm no está en tools/ ni en el PATH",
    "{source} did not assemble:": "{source} no se ensambló:",
    "{path} is {size} bytes and a {machine} screen is {wanted}":
        "{path} ocupa {size} bytes y una pantalla de {machine} son {wanted}",

    # -- srcparse -------------------------------------------------------------
    "expected a quoted string, found {found!r}":
        "se esperaba una cadena entre comillas y hay {found!r}",
    "unterminated string": "cadena sin cerrar",
    "{message} -- did you mean {meant}?": "{message} -- ¿quería decir {meant}?",
    ".def gives a name to a number: .def DOOR_OPEN 5":
        ".def da nombre a un número: .def DOOR_OPEN 5",
    "{name!r} is not a name: letters, digits and underscores, and not "
    "starting with a digit":
        "{name!r} no es un nombre: letras, cifras y guiones bajos, y sin "
        "empezar por una cifra",
    "{name!r} is a word of the language already":
        "{name!r} ya es una palabra del lenguaje",
    "{value!r} is neither a number nor a name given to one":
        "{value!r} no es un número ni un nombre dado a uno",
    '.include takes one file: .include "common.gac"':
        '.include lleva un fichero: .include "common.gac"',
    "{file} is being included from itself": "{file} se incluye a sí mismo",
    "{file} cannot be read: {why}": "{file} no se puede leer: {why}",
    "{file}:{line}: .if what?  Name a machine":
        "{file}:{line}: ¿.if qué?  Hay que nombrar una máquina",
    "there is no machine called {name!r}": "no hay máquina llamada {name!r}",
    "there is no machine called {name!r}; what there is: {machines}":
        "no hay máquina llamada {name!r}; las que hay: {machines}",
    "{file}:{line}: this source keeps some lines for some machines, so it "
    "has to be read for one of them: say which with -m":
        "{file}:{line}: esta fuente guarda líneas para algunas máquinas, así "
        "que hay que leerla para una de ellas: se dice cuál con -m",
    "{file}:{line}: .else without .if": "{file}:{line}: .else sin .if",
    "{file}:{line}: .end without .if": "{file}:{line}: .end sin .if",
    "{file}: a .if was never ended": "{file}: un .if no se cerró nunca",
    "{word!r} is not {what}, and no .def gives it one":
        "{word!r} no es {what}, y ningún .def le da uno",
    "expected a section marker, found {found!r}":
        "se esperaba una marca de sección y hay {found!r}",
    "there is no section called {tag}": "no hay sección llamada {tag}",
    "a verb": "un verbo",
    "location {room}: {word!r} is not a verb of the vocabulary":
        "sala {room}: {word!r} no es un verbo del vocabulario",
    "a room": "una sala",
    "a number": "un número",
    "{colour} is not an ink: they run from 1 to {last}, and nought would be "
    "the colour of the paper":
        "{colour} no es una tinta: van de 1 a {last}, y el cero sería el "
        "color del papel",
    "unknown /CTL setting {key!r}": "ajuste de /CTL desconocido {key!r}",
    "a vocabulary entry is: word id type":
        "una entrada del vocabulario es: palabra número tipo",
    "a number for a word": "un número para una palabra",
    "there is no word type called {kind!r}":
        "no hay tipo de palabra llamado {kind!r}",
    "expected an entry starting with #, found {found!r}":
        "se esperaba una entrada que empiece por # y hay {found!r}",
    "the number of an entry": "el número de una entrada",
    "a weight": "un peso",
    "a location header is: /LOC #id [gfx=n]":
        "la cabecera de una sala es: /LOC #número [gfx=n]",
    "the number of a room": "el número de una sala",
    "a picture": "una lámina",
    "a procedure header is: /PROC #id":
        "la cabecera de una tabla es: /PROC #número",
    "the number of a procedure": "el número de una tabla /PROC",
    "a procedure is numbered 0 to {most}":
        "una tabla /PROC se numera de 0 a {most}",
    "there is a /PROC #{number} already": "ya hay una /PROC #{number}",
    "a connection is: direction destination":
        "una salida es: dirección destino",
    "there is no drawing command called {order!r}":
        "no hay orden de dibujo llamada {order!r}",
    "{order} takes one number, and here it has {got}":
        "{order} lleva un número, y aquí tiene {got}",
    "{order} takes {wanted} numbers, and here it has {got}":
        "{order} lleva {wanted} números, y aquí tiene {got}",
    "a number for a drawing command": "un número para una orden de dibujo",
    "inks= is four pens, one to each comma, and here there are {pens}":
        "inks= son cuatro plumas, una por coma, y aquí hay {pens}",
    "a pen flashes between two colours, not {colours}: {pen!r}":
        "una pluma parpadea entre dos colores, no {colours}: {pen!r}",
    "an ink": "una tinta",
    "{ink} is not one of the Amstrad's inks, which go from 0 to 26":
        "{ink} no es una de las tintas del Amstrad, que van de 0 a 26",
    "a noise is: pitch steps step, and then tone, noise or both, which may "
    "be left off":
        "un ruido es: tono pasos paso, y luego tone, noise o both, que se "
        "puede omitir",
    "{word} is not what a noise comes out of: it is tone, noise or both":
        "{word} no es por donde sale un ruido: es tone, noise o both",
    "a pitch": "un tono",
    "a length": "una duración",
    "a step": "un paso",
    "{value} is not {what}: they run from {low} to {high}":
        "{value} no es {what}: van de {low} a {high}",
    "the font {file}: {trouble}": "la tipografía {file}: {trouble}",
    "a font entry is: #code followed by 8 hex bytes":
        "una entrada de la tipografía es: #código seguido de 8 bytes en "
        "hexadecimal",
    "character {code} needs 8 bytes, found {found}":
        "el carácter {code} necesita 8 bytes, y hay {found}",
    "{word} is not one character": "{word} no es un solo carácter",

    # -- text -----------------------------------------------------------------
    "character {char!r} is not in the character set":
        "el carácter {char!r} no está en el juego de caracteres",
    "\\ink {colour} asks for a colour there is not: they run from 0 to "
    "{last}":
        "\\ink {colour} pide un color que no hay: van de 0 a {last}",
    "\\ctr {value} asks for a counter there is not: they run from 0 to "
    "{last}":
        "\\ctr {value} pide un contador que no hay: van de 0 a {last}",
    "\\obj {value} asks for an object there cannot be: they run from 1 to "
    "{last}":
        "\\obj {value} pide un objeto que no puede haber: van de 1 a {last}",
    "\\{command} is not a text command":
        "\\{command} no es una orden del texto",
    "there is no place in the character set for {some} ({all} in all); "
    "what fits is ASCII and {specials!r}":
        "no hay sitio en el juego de caracteres para {some} ({all} en "
        "total); lo que cabe es ASCII y {specials!r}",

    # -- the viewer -----------------------------------------------------------
    "{words}    (#{picture}, order {number}, called {depth} deep)":
        "{words}    (#{picture}, orden {number}, llamada a {depth} de "
        "profundidad)",
    "the adventure has no pictures": "la aventura no tiene láminas",
    "there is no picture {n} any more": "ya no hay lámina {n}",
    "that order is the picture's it calls: take it out of that one":
        "esa orden es de la lámina a la que llama: se quita en esa",
    "the source was changed since: nothing taken back":
        "la fuente ha cambiado desde entonces: no se deshace nada",
    "it could not be measured: {error}": "no se pudo medir: {error}",
    "time: measuring #{picture} on {machine}...":
        "tiempo: midiendo #{picture} en {machine}...",
    "time: c measures it on the machine": "tiempo: c lo mide en la máquina",
    "time: #{picture} on {machine}: {said}":
        "tiempo: #{picture} en {machine}: {said}",
    "time: #{picture} on {machine} never finished":
        "tiempo: #{picture} en {machine} no terminó nunca",
    "  (before the last change)": "  (antes del último cambio)",
    "more than a player will wait": "más de lo que un jugador espera",
    "slow": "lento",
    "within the budget": "dentro de lo previsto",
    "time: #{picture} on {machine}, {seconds} s -- {verdict}{old}":
        "tiempo: #{picture} en {machine}, {seconds} s -- {verdict}{old}",
    "trace: hidden (t shows it)": "calco: oculto (t lo enseña)",
    "trace: nothing for #{picture} in {where}":
        "calco: nada para #{picture} en {where}",
    "trace: {image} at {percent}%  (t hides it, +/- more or less of it)":
        "calco: {image} al {percent}%  (t lo oculta, +/- más o menos)",
    "#{picture} on {machine}    order {count} of {orders}":
        "#{picture} en {machine}    orden {count} de {orders}",
    "last: {order}": "última: {order}",
    "last: nothing drawn yet": "última: aún no se ha dibujado nada",
    "next: {order}": "siguiente: {order}",
    "next: the picture is finished": "siguiente: la lámina está acabada",
    "left/right an order (shift ten, ctrl a hundred)  home/end  page up/down "
    "a picture  m machine  h light  q quit":
        "izq./der. una orden (mayús. diez, ctrl cien)  inicio/fin  re/av pág "
        "una lámina  m máquina  h resalta  q salir",
    "draw: l line  r rect  e ellipse  p plot  f fill  b bgfill  s shade  "
    "v move points":
        "dibujar: l línea  r rectángulo  e elipse  p punto  f fill  "
        "b bgfill  s shade  v mover puntos",
    "g snap to cells  del take out  enter write an order  ctrl-z undo  "
    "right button or esc: let go":
        "g ajustar a celdas  supr quitar  intro escribir una orden  ctrl-z "
        "deshacer  botón derecho o esc: soltar",
    "n the next caution  c time it on the machine  t trace  +/- more or "
    "less of it":
        "n el siguiente aviso  c medir en la máquina  t calco  +/- más o "
        "menos",
    "drag a point to move it": "arrastra un punto para moverlo",
    "click the two ends": "pulsa los dos extremos",
    "click two corners": "pulsa dos esquinas",
    "click the centre, then how far it reaches":
        "pulsa el centro, y luego hasta dónde llega",
    "click the point": "pulsa el punto",
    "click where it starts": "pulsa donde empieza",
    "click the other end": "pulsa el otro extremo",
    "click the other corner": "pulsa la otra esquina",
    "click how far it reaches": "pulsa hasta dónde llega",
    "{image} will not read: {error}": "{image} no se deja leer: {error}",
    "write an order: {typing}_": "escribe una orden: {typing}_",
    "  (snapping to cells)": "  (ajustando a celdas)",
    "cautions: {many}": "avisos: {many}",
    "  (n goes to the next)": "  (n va al siguiente)",

    # -- runGAC ---------------------------------------------------------------
    "Could not save: {why}": "No se pudo guardar: {why}",
    "not a game saved by this version":
        "no es una partida guardada por esta versión",
    "Could not load: {why}": "No se pudo cargar: {why}",
    "ERROR: Invalid python version": "ERROR: versión de Python no válida",
    "INPUT_FILE": "FICHERO_ENTRADA",
    "JSON database file": "fichero de base de datos JSON",
    "ERROR: File not found: {name}": "ERROR: no se encuentra el fichero: {name}",
    "ERROR: Not a valid path: {name}": "ERROR: no es una ruta válida: {name}",
    "Invalid Database": "Base de datos no válida",

    # -- deGAC ----------------------------------------------------------------
    "The {machine} tables at ${address} do not look like pointers; is this "
    "image laid where the machine would have it?":
        "Las tablas de {machine} en ${address} no parecen punteros; ¿está "
        "esta imagen puesta donde la tendría la máquina?",
    "No C64MEM block in that snapshot":
        "No hay bloque C64MEM en esa instantánea",
    "Say which machine that memory image is from, with -m":
        "Hay que decir de qué máquina es esa imagen de la memoria, con -m",
    "Invalid file size": "Tamaño de fichero no válido",
    "This adventure printed with its machine's own letters, which are not "
    "in it: it gets Modern DOS 8x8 instead":
        "Esta aventura escribía con las letras de su máquina, que no están "
        "en ella: se le pone Modern DOS 8x8 en su lugar",
    "font {n}": "tipografía {n}",
    "verbs {n}": "verbos {n}",
    "nouns {n}": "nombres {n}",
    "adverbs {n}": "adverbios {n}",
    "messages {n}": "mensajes {n}",
    "objects  {n}": "objetos  {n}",
    "locations {n}": "salas {n}",
    "hpcs {n}": "alta prioridad {n}",
    "lpcs {n}": "baja prioridad {n}",
    "lcs {n}": "condiciones locales {n}",
    "gfx {n}": "láminas {n}",
    "snapshot, or a plain image of the memory":
        "instantánea, o una imagen plana de la memoria",
    "which machine it came off; only needed for a plain image":
        "de qué máquina salió; sólo hace falta para una imagen plana",
    "OUTPUT PATHS": "RUTAS_SALIDA",
    "json database file": "fichero de base de datos json",
    "Processing file {name}...": "Procesando el fichero {name}...",
    "Reading it as {model}": "Leyéndolo como {model}",
    "Magic characters not found": "No están los caracteres mágicos",

    # -- disk -----------------------------------------------------------------
    "data": "data",
    "ibm": "ibm",
    "system": "system",
    "unknown": "desconocido",
    "not a CPC disk image": "no es una imagen de disco de CPC",
    "the file has no AMSDOS header, so where it goes is unknown":
        "el fichero no tiene cabecera AMSDOS, así que no se sabe dónde va",
    "Take a file off a CPC disk image, and put it where it belongs in "
    "memory.":
        "Saca un fichero de una imagen de disco de CPC, y lo pone en la "
        "memoria donde le corresponde.",
    "the disk image": "la imagen de disco",
    "the file to take off it": "el fichero que sacar",
    "where to write the memory image": "dónde escribir la imagen de la memoria",
    "lay it at this address instead of its own":
        "ponerlo en esta dirección en vez de en la suya",
    "which adventure to take off a disk with no directory":
        "qué aventura sacar de un disco sin directorio",
    "the disk has {n} of them": "el disco tiene {n}",
    "adventure {part} of {n} laid where it loads, from ${base} of the raw "
    "tracks, in {out}":
        "aventura {part} de {n} puesta donde carga, desde ${base} de las "
        "pistas en bruto, en {out}",
    "{n} files, {kind} format": "{n} ficheros, formato {kind}",
    "  no directory, but {n} adventures in the raw tracks: take them with "
    "--part":
        "  sin directorio, pero con {n} aventuras en las pistas en bruto: se "
        "sacan con --part",
    "loads at ${load}, ${length} bytes": "carga en ${load}, ${length} bytes",
    "no header": "sin cabecera",
    "  {name} {size} bytes  {where}": "  {name} {size} bytes  {where}",
    "no {name} on the disk": "no hay {name} en el disco",
    "{name} laid at ${at} after moving itself there in {out}":
        "{name} puesto en ${at} después de moverse allí, en {out}",
    "{name} laid at ${at} in {out}": "{name} puesto en ${at}, en {out}",

    # -- grab -----------------------------------------------------------------
    "Take a memory image out of an adventure that is loading from disk or "
    "tape.":
        "Saca una imagen de la memoria de una aventura que se carga de disco "
        "o de cinta.",
    "the disk, tape or snapshot to load":
        "el disco, la cinta o la instantánea que cargar",
    "which machine to load it on": "en qué máquina cargarlo",
    "seconds to let it load": "segundos que dejarle para cargar",
    "seconds to let the machine boot": "segundos que dejar arrancar a la máquina",
    "what to type once it has booted": "qué teclear una vez arrancada",
    "{n} bytes of {machine} memory in {output}":
        "{n} bytes de memoria de {machine} en {output}",
    "looks like GAC: {pointers}": "parece GAC: {pointers}",
    "no GAC tables at $4000; give it longer, or type something to start it":
        "no hay tablas de GAC en $4000; hay que darle más tiempo, o teclear "
        "algo para que empiece",
}
