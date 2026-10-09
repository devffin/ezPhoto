# ezPhoto

A simple, multilingual desktop photo editor built with Python, Qt, and Pillow.

## Getting Started

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

On first launch, the app automatically detects the operating system language. English is the default for unsupported languages. English, French, and Spanish are available in the language selector; your choice is remembered.

Open or drag in a photo to adjust its lighting and color, apply filters, crop, resize, rotate, or flip it. Undo and redo edits with `Ctrl+Z` and `Ctrl+Shift+Z`. Export images as PNG, JPEG, WebP, or TIFF.

On Linux, use a desktop session with the system OpenGL runtime installed.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from PySide6.QtWidgets import QApplication; from ezphoto.window import EditorWindow; app = QApplication([]); window = EditorWindow(); assert window.tabs.count() == 3; print('ezPhoto window OK')"
```
