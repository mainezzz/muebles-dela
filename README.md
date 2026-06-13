# DELA Muebles

Sistema paramétrico para diseño, visualización y preparación de fabricación de muebles modulares.

Incluye:

- generación de modelos desde JSON
- renders de producto con Blender
- generación de piezas para fabricación
- kerf real
- layouts técnicos tipo póster
- exportación de `.png`, `.blend` y `.glb`

---

# 🧠 Concepto

El proyecto separa claramente dos capas:

1. **Visualización de producto**
   - genera la estantería final
   - renderiza vistas limpias
   - exporta modelo 3D

2. **Fabricación / kerf**
   - genera piezas, tableros y cortes
   - aplica kerf real
   - compone layouts técnicos y ensamblado

---

# ⚙️ Pipeline real

## A. Pipeline visual

```text
examples/*.json
→ app.cli generate
→ Blender (generate_bookshelf.py)
→ outputs/<modelo>/
→ render_front.png + render_angle.png + .blend + .glb + JSON auxiliares
````

## B. Pipeline fabricación / kerf

```text
scripts/kerf_*.py
→ outputs/kerf_<modelo>/<modelo>.json
→ Blender (generate_kerf_layout.py)
→ 01_board_layout.png
→ 02_cut_parts.png
→ 03_exploded_assembly.png
→ 04_final_assembly.png
→ 05_overview.png
→ 06_final_assembly.blend
→ 06_final_assembly.glb
```

---

# 📁 Estructura del proyecto

```text
examples/
  *.json
  # inputs paramétricos de los modelos

app/
  cli.py
  validator.py
  # entrada principal y validación

scripts/
  kerf_estanteria_dvds.py
  kerf_estanteria_libros_4_4.py
  kerf_estanteria_libros_5_3.py
  # generación de piezas y fabrication JSON para kerf

blender/
  generate_bookshelf.py
  # render visual del mueble final

  generate_kerf_layout.py
  # layouts técnicos, exploded assembly, final assembly y exports

schemas/
  bookshelf.schema.json

outputs/
  <modelo>/
  kerf_<modelo>/
  # resultados generados
```

---

# 🧱 Inputs

## Inputs visuales

Se definen en:

```text
examples/*.json
```

Ejemplos actuales:

* `estanteria_dvds.json`
* `estanteria_dvds_con_dvds.json`
* `estanteria_libros_mixta_4_4_160.json`
* `estanteria_libros_mixta_4_4_160_con_libros.json`
* `estanteria_libros_mixta_5_3_160.json`
* `estanteria_libros_mixta_5_3_160_con_libros.json`

## Inputs de fabricación

Se generan con los scripts `kerf_*` y se guardan como:

```text
outputs/kerf_<modelo>/<modelo>.json
```

Ese JSON contiene:

* cabina / dimensiones generales
* piezas
* tableros
* cortes
* kerf aplicado
* layout industrial

👉 Es la entrada directa de `blender/generate_kerf_layout.py`.

---

# ✂️ Kerf

El sistema usa kerf real en la fase de fabricación.

Valor actual:

```text
3 mm
```

Referencia conceptual:

```python
(total_piezas - 1) * kerf
```

Se aplica en la separación efectiva entre piezas sobre tablero.

---

# 🪵 Materiales

## Estructura

* tablero de pino / acabado pino
* grosor estructural: **18 mm**

## Traseras

* panel trasero / MDF
* grosor trasera: **5 mm**

---

# 🖼 Outputs

## Outputs del pipeline visual

Por cada modelo generado con `app.cli generate`:

```text
outputs/<modelo>/
  render_front.png
  render_angle.png
  <modelo>.blend
  <modelo>.glb
  validated.json
  layout_report.json
```

## Outputs del pipeline kerf

Por cada modelo generado con `generate_kerf_layout.py`:

```text
outputs/kerf_<modelo>/
  01_board_layout.png
  02_cut_parts.png
  03_exploded_assembly.png
  04_final_assembly.png
  05_overview.png
  06_final_assembly.blend
  06_final_assembly.glb
  <modelo>.json
```

---

# ▶️ Uso

## 1. Activar entorno

```powershell
cd C:\ruta\al\proyecto
.\.venv\Scripts\Activate.ps1
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
```

## 2. Generar modelo visual

Ejemplo DVDs:

```powershell
python -m app.cli generate examples\estanteria_dvds.json --blender-exe $blender
```

Ejemplo libros 4x4:

```powershell
python -m app.cli generate examples\estanteria_libros_mixta_4_4_160.json --blender-exe $blender
```

Ejemplo libros 5x3:

```powershell
python -m app.cli generate examples\estanteria_libros_mixta_5_3_160.json --blender-exe $blender
```

## 3. Generar fabrication JSON para kerf

```powershell
python .\scripts\kerf_estanteria_dvds.py
python .\scripts\kerf_estanteria_libros_4_4.py
python .\scripts\kerf_estanteria_libros_5_3.py
```

## 4. Generar layouts kerf en Blender

```powershell
& $blender -b --python .\blender\generate_kerf_layout.py -- `
.\outputs\kerf_estanteria_dvds\kerf_estanteria_dvds.json `
.\outputs\kerf_estanteria_dvds
```

```powershell
& $blender -b --python .\blender\generate_kerf_layout.py -- `
.\outputs\kerf_estanteria_libros_4_4_160\kerf_estanteria_libros_4_4_160.json `
.\outputs\kerf_estanteria_libros_4_4_160
```

```powershell
& $blender -b --python .\blender\generate_kerf_layout.py -- `
.\outputs\kerf_estanteria_libros_5_3_160\kerf_estanteria_libros_5_3_160.json `
.\outputs\kerf_estanteria_libros_5_3_160
```

---

# 📦 Modelos actuales

## DVDs

* dimensiones exteriores: **2036 × 2000 × 200 mm**
* pipeline visual operativo
* pipeline kerf operativo
* layouts técnicos generados

## Libros 4×4

* dimensiones exteriores: **1636 × 2000 × 300 mm**
* pipeline visual operativo
* pipeline kerf operativo
* ajustes visuales menores

## Libros 5×3

* dimensiones exteriores: **1636 × 2000 × 300 mm**
* pipeline visual operativo
* pipeline kerf operativo
* ajustes visuales menores

---

# 🎯 Objetivo visual

* estilo IKEA
* renders limpios de catálogo
* exploded assembly
* cámaras ortográficas
* posters técnicos de fabricación
* colores semánticos por tipo de pieza

---

# 🛠 Requisitos

```text
Python 3.11+
Blender 4.5+
```

---

# 🚧 Estado actual

El proyecto ya permite:

* generar estanterías desde JSON
* exportar `.blend` y `.glb`
* renderizar vistas visuales
* generar JSON de fabricación
* producir layouts de kerf completos
* crear exploded assembly y final assembly

Pendiente / mejorable:

* optimización adicional de composición visual
* BOM automático
* export CNC
* optimización avanzada de corte

---

# 📄 Licencia

MIT

````
