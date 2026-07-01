@echo off
setlocal

set "PYEXE=C:\Users\Mateo Martinez\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "SELF=%~f0"
set "DESKTOP=C:\Users\Mateo Martinez\Desktop"
set "TMPPY=%TEMP%\pdf_pagina6_a_json_%RANDOM%%RANDOM%.py"

if not exist "%PYEXE%" (
  echo No se encontro el Python del runtime:
  echo %PYEXE%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$self = $env:SELF; $tmp = $env:TMPPY; $lines = Get-Content -LiteralPath $self; $marker = '###PYTHON###'; $idx = [Array]::IndexOf($lines, $marker); if ($idx -lt 0) { throw 'No se encontro el bloque Python.' }; $script = $lines[($idx + 1)..($lines.Length - 1)] -join [Environment]::NewLine; Set-Content -LiteralPath $tmp -Value $script -Encoding UTF8"

if errorlevel 1 (
  echo No se pudo preparar el script interno.
  del "%TMPPY%" >nul 2>nul
  pause
  exit /b 1
)

echo ========================================
echo   Extraer pagina 6 de PDF a JSON
echo ========================================
echo.
echo 1. Si abris este .bat solo, te va a pedir elegir un PDF.
echo 2. Si arrastras un PDF encima, lo procesa directo.
echo.

"%PYEXE%" "%TMPPY%" %*
set "RC=%ERRORLEVEL%"

del "%TMPPY%" >nul 2>nul

if not "%RC%"=="0" (
  echo.
  echo Hubo un error al procesar el PDF.
  pause
)

exit /b %RC%

###PYTHON###
import argparse
import json
from pathlib import Path
import os

from pypdf import PdfReader


def fix_mojibake(value: str) -> str:
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def pick_file() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise SystemExit(f"No se pudo abrir el selector de archivos: {exc}")

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Seleccionar PDF",
        filetypes=[
            ("PDF", "*.pdf"),
            ("Todos los archivos", "*.*"),
        ],
    )
    root.destroy()

    if not path:
        raise SystemExit("No se selecciono ningun PDF.")

    return path


def extract_page_text(pdf_path: Path, page_number: int) -> str:
    reader = PdfReader(str(pdf_path))
    index = page_number - 1
    if index < 0 or index >= len(reader.pages):
        raise SystemExit(
            f"El PDF tiene {len(reader.pages)} paginas y la pagina {page_number} no existe."
        )
    page = reader.pages[index]
    text = page.extract_text() or ""
    return fix_mojibake(text.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae solo la pagina 6 de un PDF y la guarda en JSON."
    )
    parser.add_argument("pdf", nargs="?", help="Ruta del PDF")
    parser.add_argument(
        "--page",
        type=int,
        default=6,
        help="Numero de pagina a extraer. Por defecto: 6",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf.strip('"')) if args.pdf else Path(pick_file())
    if not pdf_path.exists():
        raise SystemExit(f"No existe el archivo: {pdf_path}")

    text = extract_page_text(pdf_path, args.page)
    lines = [fix_mojibake(line.strip()) for line in text.splitlines() if line.strip()]

    payload = {
        "source_pdf": str(pdf_path.resolve()),
        "page": args.page,
        "file_name": pdf_path.name,
        "page_text": text,
        "lines": lines,
    }

    output_dir = Path(os.environ["DESKTOP"]) / "salidas_pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{pdf_path.stem}_p{args.page}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Listo. JSON generado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
