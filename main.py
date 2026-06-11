#!/usr/bin/env python3

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
        from gui.main_window import MainWindow
    except ImportError as exc:
        print(
            "PySide6 is required to run the GUI.\n"
            "Install dependencies with:\n"
            "  pip install -r requirements.txt\n"
            "Or for a smaller download:\n"
            "  pip install PySide6_Essentials shiboken6\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    app = QApplication(sys.argv)
    app.setApplicationName("Document Scanner")
    app.setOrganizationName("DocumentScanner")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
