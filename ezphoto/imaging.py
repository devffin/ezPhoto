from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def open_image(path: str) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image.load()
        return image.convert("RGBA")


def adjust_image(
    image: Image.Image,
    *,
    brightness: int = 0,
    contrast: int = 0,
    saturation: int = 0,
    exposure: int = 0,
    warmth: int = 0,
    sharpness: int = 0,
) -> Image.Image:
    base = image.convert("RGBA")
    alpha = base.getchannel("A")
    result = base.convert("RGB")
    result = ImageEnhance.Brightness(result).enhance(2 ** (exposure / 100) * (1 + brightness / 100))
    result = ImageEnhance.Contrast(result).enhance(1 + contrast / 100)
    result = ImageEnhance.Color(result).enhance(1 + saturation / 100)
    result = ImageEnhance.Sharpness(result).enhance(1 + sharpness / 100)
    if warmth:
        red, green, blue = result.split()
        result = Image.merge(
            "RGB",
            (
                red.point(lambda value: min(255, max(0, int(value * (1 + warmth / 250))))),
                green,
                blue.point(lambda value: min(255, max(0, int(value * (1 - warmth / 250))))),
            ),
        )
    return Image.merge("RGBA", (*result.split(), alpha))


def apply_filter(image: Image.Image, name: str) -> Image.Image:
    base = image.convert("RGBA")
    alpha = base.getchannel("A")
    rgb = base.convert("RGB")
    if name == "grayscale":
        result = ImageOps.grayscale(rgb).convert("RGB")
    elif name == "sepia":
        result = ImageOps.colorize(ImageOps.grayscale(rgb), "#302318", "#ecd8ac")
    elif name == "negative":
        result = ImageOps.invert(rgb)
    elif name == "blur":
        result = rgb.filter(ImageFilter.GaussianBlur(radius=2.4))
    elif name == "sharpen":
        result = rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    else:
        raise ValueError(f"Unknown image filter: {name}")
    return Image.merge("RGBA", (*result.split(), alpha))


def resize_image(image: Image.Image, width: int, height: int) -> Image.Image:
    if not 1 <= width <= 30_000 or not 1 <= height <= 30_000:
        raise ValueError("Image dimensions must be between 1 and 30,000 pixels.")
    return image.resize((width, height), Image.Resampling.LANCZOS)


def crop_image(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = box
    left, top = max(0, left), max(0, top)
    right, bottom = min(image.width, right), min(image.height, bottom)
    if right <= left or bottom <= top:
        raise ValueError("Select a non-empty crop area.")
    return image.crop((left, top, right, bottom))