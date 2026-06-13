from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.fabrication import build_and_write
from app.spec_builder import extract_fabrication_request


OUTPUT_DIR = Path("outputs/kerf_estanteria_libros_4_4_160")


def main() -> None:
    request = extract_fabrication_request(
        {
            "project_name": "estanteria_libros_mixta_4_4_160",
            "preset": "libros",
            "pattern": "4_4",
            "width": 1636,
            "height": 2000,
            "depth": 300,
            "board_thickness": 18,
            "back_panel": True,
            "back_thickness": 5,
        }
    )
    output_path = build_and_write(request, OUTPUT_DIR, "kerf_estanteria_libros_4_4_160.json")
    print(f"DONE -> {output_path}")


if __name__ == "__main__":
    main()
