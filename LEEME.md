# reGAC

*[Read in English](README.md)*

Escribe una aventura de Graphic Adventure Creator como un fichero de texto y
publícala en nueve máquinas de los ochenta con una sola orden, o rescata una
de una cinta de 1986 y léela como fuente.

Las nueve: el Spectrum 48, 128 y +3, el Amstrad CPC 464 y 6128, el Amstrad
PCW, el MSX, el Spectrum Next y un PC con CGA, desde un XT a 4,77 MHz.

## Instalación

Lo que hace falta:

* **Python 3.11** o más nuevo.
* **sjasmplus**, que ensambla los intérpretes de las máquinas Z80: en la
  carpeta `tools/` de reGAC o en cualquier sitio del PATH.
* **NASM**, sólo para el PC, en `tools/` o en el PATH.
* **ZEsarUX** en `tools/` y **DOSBox-X** en el PATH, sólo para pasar las
  pruebas, para sacar una aventura de una máquina con `grab.py` o para medir
  una lámina en `regac draw`.

Desde una release, descarga `regac-<versión>.zip`, descomprímelo y, en su
carpeta:

    pip install -e .

que hace de `regac` una orden propia; `python -m regac` hace lo mismo desde
dentro de la carpeta sin instalar nada. Se instala apuntando a la carpeta y
no copiándola, porque los intérpretes con los que construye son las carpetas
de al lado, `z80/` y `x86/`. Desde una copia del repositorio es igual, o
`poetry install`.

La release trae además `example-faro-<versión>.zip`: la aventura de ejemplo
ya construida para las nueve máquinas, para cargarla en un emulador sin más.

Las herramientas hablan en español o en inglés, según esté el sistema; la
variable `REGAC_LANG`, `es` o `en`, elige una diga lo que diga el sistema.

## En cinco minutos

    regac make ejemplo/faro.toml

construye *El faro de Santa Bárbara*, el ejemplo, para las nueve máquinas, en
`ejemplo/salida/`. Para jugarlo sin máquina ninguna:

    regac play ejemplo/faro.gac ejemplo/solucion.txt --expect "Fin de la aventura"

o, para teclear uno mismo las órdenes:

    regac compile ejemplo/faro.gac faro.json
    python runGAC.py faro.json

## Documentación

* **[doc/manual.md](doc/manual.md)**: el manual: qué instalar, cómo se escribe
  una aventura bloque a bloque, cómo se comprueba, se dibuja y se construye
  para cada máquina.
* **[doc/gac.md](doc/gac.md)**: el lenguaje GAC entero: el turno, todos los
  opcodes, el analizador, los marcadores y mensajes reservados y todas las
  órdenes de dibujo.
* **[doc/formato-fuente.md](doc/formato-fuente.md)**: el formato del fuente,
  sección a sección.

Las tres, en inglés, están en [doc/en/](doc/en/manual.md). El resto de
`doc/` es el diario del desarrollo y las notas de cómo se hizo cada pieza: qué
se midió, en qué orden y por qué.

## Las órdenes

| | |
|---|---|
| `regac compile juego.gac juego.json` | el fuente en base de datos, o dice dónde está mal |
| `regac decompile juego.json juego.gac` | y al revés |
| `regac check juego.json` | que nada apunte a algo que no existe |
| `regac lint juego.gac` | lo que está y nada usa |
| `regac map juego.gac mapa.svg` | el mapa de las salas |
| `regac play juego.gac solucion.txt` | juega un fichero de órdenes y dice si la partida acaba |
| `regac draw juego.gac 12 -m cpc` | una lámina en una ventana: se mira, se dibuja, se calca, se mide |
| `regac render juego.json laminas/` | las láminas como PNG |
| `regac text juego.json` | lo que ocupa el texto empaquetado |
| `regac make juego.toml --zip juego.zip` | todas las máquinas que nombra un proyecto |
| `regac build`, `regac release` | una máquina, a mano |

## Las piezas

* **regac**: el compilador y el decompilador del fuente, el dibujante de las
  láminas, la base de datos que leen los intérpretes, los medios en los que se
  entregan, y las utilidades de arriba.
* **z80**: los intérpretes de las máquinas Z80: Spectrum, Amstrad CPC, Amstrad
  PCW, MSX y Spectrum Next.
* **x86**: el intérprete del PC, en ensamblador 8086 para NASM.
* **runGAC.py**, **runGAC_pygame.py**: el intérprete en Python, en un terminal
  o detrás de una pantalla como la del Spectrum.
* **deGAC.py**: una aventura sacada de una instantánea de Spectrum o de un
  disco de Amstrad, en JSON.
* **disk.py**: un fichero de una imagen de disco de Amstrad, o una aventura
  entera de uno hecho para que no se pudiera copiar.
* **grab.py**: un disco, una cinta o una instantánea cargados en su máquina, y
  lo que dejaron en memoria escrito para que lo lea el decompilador.
* **editors/vscode**: los colores de un fuente `.gac` en VS Code.

## Licencias

Dos, a propósito.

Las herramientas, todo lo que está en Python, son **GNU General Public License
v3**, cuyo texto está en [LICENSE](LICENSE).

Los intérpretes de [z80/](z80) y [x86/](x86), que es lo que acaba dentro de la
aventura de alguien, son **licencia MIT**: ver [z80/LICENSE](z80/LICENSE) y
[x86/LICENSE](x86/LICENSE). Una aventura construida con estas herramientas no
lleva ninguna obligación por ellas.

Las letras que recibe una aventura que no trae las suyas,
[regac/moderndos8x8.bin](regac/moderndos8x8.bin), son **Modern DOS 8x8**, de
Jayvee Enaguas, de dominio público bajo CC0 1.0: ver
[regac/moderndos.py](regac/moderndos.py).
