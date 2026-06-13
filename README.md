# DELA Muebles

Generador paramétrico de estanterías DELA.

El programa permite definir una estantería a partir de:

- tipo de contenido: DVD o libros
- medidas exteriores máximas
- grosor del material
- modo constructivo del armazón
- número de columnas
- huecos y su distribución

A partir de esa entrada, el sistema:

- valida si el mueble es viable
- calcula la geometría interior útil
- genera una especificación visual normalizada
- genera una especificación de fabricación
- opcionalmente renderiza vistas en Blender

---

## Modelo de entrada v2

La entrada principal del sistema es un JSON con esta idea:

- `content_type`: tipo de contenido (`dvd` o `books`)
- `outer`: medidas exteriores máximas disponibles
- `material`: espesores de tablero y trasera
- `construction`: cómo se monta el armazón
- `layout`: huecos, columnas y distribución
- `visualization`: opciones de visualización

### Campos principales

- `outer.width`
- `outer.height`
- `outer.depth`

Estas medidas representan el **espacio exterior máximo del mueble**.

### Construcción

- `construction.shell_mode`
  - `sides_outside`
  - `top_bottom_outside`

- `construction.columns`
  - `1`
  - `2`

- `construction.back_panel`
  - `true`
  - `false`

### Huecos

Los huecos pueden definirse de dos formas:

- `layout.openings`: secuencia manual de huecos
- `layout.opening_groups`: grupos de huecos con cantidad

Además, la distribución puede controlarse con:

- `layout.distribution_mode`
  - `manual`
  - `symmetric`
  - `large_top`
  - `large_bottom`

---

## Ejemplos

El repositorio incluye estos ejemplos:

- `examples/dvd.json`
- `examples/libros_4_4.json`
- `examples/libros_5_3.json`

---

## Uso desde línea de comandos

### Validar un mueble

```bash
python -m app.cli validate examples/dvd.json