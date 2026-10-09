import sys

from PySide6.QtWidgets import QApplication

from ezphoto.window import EditorWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("ezPhoto")
    application.setOrganizationName("ezPhoto")
    window = EditorWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())