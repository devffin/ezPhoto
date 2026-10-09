import locale

from PySide6.QtCore import QLocale


LANGUAGES = {"en": "English", "fr": "Français", "es": "Español"}

_STRINGS = {
    "app_tagline": {"fr": "ATELIER PHOTO", "en": "PHOTO STUDIO", "es": "ESTUDIO FOTOGRÁFICO"},
    "file": {"fr": "Fichier", "en": "File", "es": "Archivo"},
    "edit": {"fr": "Édition", "en": "Edit", "es": "Edición"},
    "image_menu": {"fr": "Image", "en": "Image", "es": "Imagen"},
    "language_menu": {"fr": "Langue", "en": "Language", "es": "Idioma"},
    "open": {"fr": "Ouvrir", "en": "Open", "es": "Abrir"},
    "save": {"fr": "Enregistrer", "en": "Save", "es": "Guardar"},
    "export": {"fr": "Exporter", "en": "Export", "es": "Exportar"},
    "undo": {"fr": "Annuler", "en": "Undo", "es": "Deshacer"},
    "redo": {"fr": "Rétablir", "en": "Redo", "es": "Rehacer"},
    "crop": {"fr": "Recadrage", "en": "Crop", "es": "Recortar"},
    "apply_crop": {"fr": "Appliquer le recadrage", "en": "Apply crop", "es": "Aplicar recorte"},
    "adjust": {"fr": "Réglages", "en": "Adjust", "es": "Ajustes"},
    "filters": {"fr": "Filtres", "en": "Filters", "es": "Filtros"},
    "details": {"fr": "Informations", "en": "Details", "es": "Detalles"},
    "adjust_photo": {"fr": "Lumière et couleur", "en": "Light and color", "es": "Luz y color"},
    "brightness": {"fr": "Luminosité", "en": "Brightness", "es": "Brillo"},
    "contrast": {"fr": "Contraste", "en": "Contrast", "es": "Contraste"},
    "saturation": {"fr": "Saturation", "en": "Saturation", "es": "Saturación"},
    "exposure": {"fr": "Exposition", "en": "Exposure", "es": "Exposición"},
    "warmth": {"fr": "Température", "en": "Warmth", "es": "Temperatura"},
    "sharpness": {"fr": "Netteté", "en": "Sharpness", "es": "Nitidez"},
    "apply": {"fr": "Appliquer les réglages", "en": "Apply adjustments", "es": "Aplicar ajustes"},
    "reset": {"fr": "Réinitialiser", "en": "Reset", "es": "Restablecer"},
    "effects": {"fr": "Effets", "en": "Effects", "es": "Efectos"},
    "grayscale": {"fr": "Noir et blanc", "en": "Black & white", "es": "Blanco y negro"},
    "sepia": {"fr": "Sépia", "en": "Sepia", "es": "Sepia"},
    "negative": {"fr": "Négatif", "en": "Invert", "es": "Negativo"},
    "blur": {"fr": "Flou doux", "en": "Soft blur", "es": "Desenfoque suave"},
    "sharpen": {"fr": "Renforcer la netteté", "en": "Sharpen", "es": "Enfocar"},
    "transform": {"fr": "Transformation", "en": "Transform", "es": "Transformar"},
    "rotate_left": {"fr": "Rotation gauche", "en": "Rotate left", "es": "Girar a la izquierda"},
    "rotate_right": {"fr": "Rotation droite", "en": "Rotate right", "es": "Girar a la derecha"},
    "flip_horizontal": {"fr": "Miroir horizontal", "en": "Flip horizontal", "es": "Voltear horizontal"},
    "flip_vertical": {"fr": "Miroir vertical", "en": "Flip vertical", "es": "Voltear vertical"},
    "resize": {"fr": "Redimensionner…", "en": "Resize…", "es": "Redimensionar…"},
    "width": {"fr": "Largeur", "en": "Width", "es": "Ancho"},
    "height": {"fr": "Hauteur", "en": "Height", "es": "Alto"},
    "keep_ratio": {"fr": "Conserver les proportions", "en": "Lock aspect ratio", "es": "Conservar proporción"},
    "file_info": {"fr": "Fichier", "en": "File", "es": "Archivo"},
    "dimensions": {"fr": "Dimensions", "en": "Dimensions", "es": "Dimensiones"},
    "color_mode": {"fr": "Mode colorimétrique", "en": "Color mode", "es": "Modo de color"},
    "history": {"fr": "Historique", "en": "History", "es": "Historial"},
    "untitled": {"fr": "Sans titre", "en": "Untitled", "es": "Sin título"},
    "drop_image": {"fr": "Déposez une photo ici", "en": "Drop a photo here", "es": "Suelta una foto aquí"},
    "or_open": {"fr": "ou cliquez sur « Ouvrir » pour commencer", "en": "or click Open to get started", "es": "o haz clic en Abrir para empezar"},
    "no_image": {"fr": "Aucune image ouverte", "en": "No image open", "es": "Ninguna imagen abierta"},
    "select_crop": {"fr": "Tracez un rectangle sur l’image à conserver.", "en": "Drag to select the area to keep.", "es": "Arrastra para seleccionar el área que quieres conservar."},
    "zoom": {"fr": "Zoom", "en": "Zoom", "es": "Zoom"},
    "auto": {"fr": "Automatique", "en": "Automatic", "es": "Automático"},
    "show_history": {"fr": "Afficher l’historique des modifications", "en": "Show editing history", "es": "Mostrar historial de edición"},
    "open_images": {"fr": "Images", "en": "Images", "es": "Imágenes"},
    "save_images": {"fr": "Images PNG, JPEG, WebP et TIFF", "en": "PNG, JPEG, WebP and TIFF images", "es": "Imágenes PNG, JPEG, WebP y TIFF"},
    "confirm_title": {"fr": "Modifications non enregistrées", "en": "Unsaved changes", "es": "Cambios sin guardar"},
    "confirm_open": {"fr": "Enregistrer vos modifications avant d’ouvrir une autre image ?", "en": "Save your changes before opening another image?", "es": "¿Guardar los cambios antes de abrir otra imagen?"},
    "error_title": {"fr": "Impossible d’ouvrir l’image", "en": "Could not open image", "es": "No se pudo abrir la imagen"},
    "export_title": {"fr": "Exporter l’image", "en": "Export image", "es": "Exportar imagen"},
    "quality": {"fr": "Qualité JPEG (60 à 100)", "en": "JPEG quality (60 to 100)", "es": "Calidad JPEG (60 a 100)"},
    "quit": {"fr": "Quitter", "en": "Quit", "es": "Salir"},
}


def automatic_language() -> str:
    code = QLocale.system().name().split("_")[0].lower()
    if code in LANGUAGES:
        return code
    try:
        code = locale.getlocale()[0].split("_")[0].lower()
    except (AttributeError, TypeError):
        pass
    return code if code in LANGUAGES else "en"


def translate(key: str, language: str) -> str:
    entry = _STRINGS[key]
    return entry.get(language, entry["en"])