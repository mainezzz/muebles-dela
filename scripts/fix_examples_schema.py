from __future__ import annotations

import json
from pathlib import Path


EXAMPLES_DIR = Path("examples")

FILES = [
    "estanteria_dvds.json",
    "estanteria_dvds_con_dvds.json",
    "estanteria_libros_mixta_4_4_160.json",
    "estanteria_libros_mixta_4_4_160_con_libros.json",
    "estanteria_libros_mixta_5_3_160.json",
    "estanteria_libros_mixta_5_3_160_con_libros.json",
]


def fix_file(path: Path) -> None:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    changed = False

    if "type" not in data:
        data["type"] = "bookshelf"
        changed = True

    if "units" not in data:
        data["units"] = "mm"
        changed = True

    ordered: dict = {
        "project_name": data.get("project_name"),
        "type": data.get("type"),
        "units": data.get("units"),
    }

    for key, value in data.items():
        if key in {"project_name", "type", "units"}:
            continue
        ordered[key] = value

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            ordered,
            file,
            indent=2,
            ensure_ascii=False,
        )

    status = "UPDATED" if changed else "OK"
    print(f"{status} -> {path.name}")


def main() -> None:
    for filename in FILES:
        path = EXAMPLES_DIR / filename

        if not path.exists():
            print(f"NOT FOUND -> {filename}")
            continue

        fix_file(path)

    print("\nDONE")


if __name__ == "__main__":
    main()
