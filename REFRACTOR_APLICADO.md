# Refactor aplicado

## Cambios
- Presets unificados en `app/presets.py`
- Conversión de spec simple -> spec legacy en `app/spec_builder.py`
- Fabricación unificada en `app/fabrication.py`
- `app/validator.py` acepta specs simples o legacy
- `app/cli.py` añade `build`
- Nuevos ejemplos simples en `examples/`
- Scripts `kerf_*` reescritos como wrappers finos

## Uso
```powershell
python -m app.cli validate examples/dvd.json
python -m app.cli build examples/dvd.json
python -m app.cli build examples/libros_4_4.json
python -m app.cli build examples/libros_5_3.json
```

Con Blender:
```powershell
python -m app.cli build examples/dvd.json --blender-exe "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```
