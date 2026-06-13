# DELA Muebles

Sistema paramétrico para generar estanterías desde una entrada simple, validarlas y preparar el payload de fabricación.

## Flujo recomendado

El flujo actual del proyecto parte de una **spec simple** y de una única CLI:

- `dvd`
- `libros` con patrón `4_4`
- `libros` con patrón `5_3`

La entrada recomendada está en:

- `examples/dvd.json`
- `examples/libros_4_4.json`
- `examples/libros_5_3.json`

## Instalación

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

### 1) Validar una spec

```powershell
python -m app.cli validate examples/dvd.json
python -m app.cli validate examples/libros_4_4.json
python -m app.cli validate examples/libros_5_3.json
```

### 2) Construir outputs sin Blender

Genera como mínimo:

- `validated.json`
- `fabrication.json`

```powershell
python -m app.cli build examples/dvd.json
python -m app.cli build examples/libros_4_4.json
python -m app.cli build examples/libros_5_3.json
```

### 3) Construir outputs con Blender

Además de los JSON, genera el render visual y el layout de fabricación.

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"

python -m app.cli build examples/dvd.json --blender-exe $blender
python -m app.cli build examples/libros_4_4.json --blender-exe $blender
python -m app.cli build examples/libros_5_3.json --blender-exe $blender
```

### 4) Render visual solamente

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
python -m app.cli generate examples/dvd.json --blender-exe $blender
```

## Specs simples

### DVD

```json
{
  "project_name": "dvd",
  "preset": "dvd",
  "render_contents": true
}
```

### Libros 4_4

```json
{
  "project_name": "libros_4_4",
  "preset": "libros",
  "pattern": "4_4",
  "render_contents": true
}
```

### Libros 5_3

```json
{
  "project_name": "libros_5_3",
  "preset": "libros",
  "pattern": "5_3",
  "render_contents": true
}
```

## Salida esperada

Por defecto, los archivos se escriben en:

```text
outputs/<project_name>/
```

Archivos mínimos generados por `build`:

```text
outputs/<project_name>/
  validated.json
  fabrication.json
```

Si usas Blender, en esa misma carpeta aparecerán también renders y exports adicionales.

## Estructura relevante

```text
app/
  cli.py
  presets.py
  spec_builder.py
  fabrication.py
  validator.py

blender/
  generate_bookshelf.py
  generate_kerf_layout.py

examples/
  dvd.json
  libros_4_4.json
  libros_5_3.json

tests/
  test_cli_smoke.py
```

## Qué hace cada módulo

- `app/presets.py`: catálogo de presets y patrones.
- `app/spec_builder.py`: transforma la spec simple en la spec visual y en la request de fabricación.
- `app/validator.py`: valida la spec resultante.
- `app/fabrication.py`: genera `fabrication.json`.
- `app/cli.py`: entrada única de terminal.
- `blender/generate_bookshelf.py`: render visual del mueble.
- `blender/generate_kerf_layout.py`: layout de fabricación.

## Tests

Los tests mínimos de humo están en `tests/test_cli_smoke.py`.

Ejecución:

```powershell
python -m unittest discover -s tests -v
```

## Notas

- La ruta recomendada es la de los ejemplos simples y la CLI unificada.
- Si el repositorio contiene ejemplos o scripts legacy, no son la entrada principal documentada aquí.
