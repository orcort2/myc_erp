from __future__ import annotations

from app.services.office_converter import diagnose_office_converter


def main() -> int:
    diagnostic = diagnose_office_converter()
    print("LibreOffice:")
    print(f"- disponible: {'sí' if diagnostic.available else 'no'}")
    print(f"- ejecutable resuelto: {diagnostic.executable or '-'}")
    print(f"- origen: {diagnostic.source or '-'}")
    print(f"- versión: {diagnostic.version or '-'}")
    if diagnostic.error:
        print(f"- diagnóstico: {diagnostic.error}")
    return 0 if diagnostic.available else 1


if __name__ == "__main__":
    raise SystemExit(main())
