# Crear estructura
mkdir app -ea 0
mkdir blender -ea 0
mkdir schemas -ea 0
mkdir examples -ea 0
mkdir outputs -ea 0
mkdir tests -ea 0
mkdir docs -ea 0

# Crear archivos vacíos
ni app\cli.py -ea 0
ni app\validator.py -ea 0
ni blender\generate_bookshelf.py -ea 0
ni schemas\shelf_v1.schema.json -ea 0
ni examples\estanteria.json -ea 0

Write-Host "Estructura creada"