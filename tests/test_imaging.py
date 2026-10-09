import unittest

from PIL import Image

from ezphoto.imaging import adjust_image, apply_filter, crop_image, resize_image


class ImagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = Image.new("RGBA", (12, 8), (110, 140, 170, 170))

    def test_adjustments_preserve_transparency_and_dimensions(self) -> None:
        result = adjust_image(self.image, brightness=20)
        self.assertEqual(result.size, self.image.size)
        self.assertEqual(result.getpixel((0, 0))[3], 170)
        self.assertGreater(result.getpixel((0, 0))[0], self.image.getpixel((0, 0))[0])

    def test_warmth_adds_a_warm_color_cast(self) -> None:
        result = adjust_image(self.image, warmth=20).getpixel((0, 0))
        original = self.image.getpixel((0, 0))
        self.assertGreater(result[0], original[0])
        self.assertLess(result[2], original[2])

    def test_filters_preserve_transparency(self) -> None:
        for name in ("grayscale", "sepia", "negative", "blur", "sharpen"):
            with self.subTest(filter=name):
                result = apply_filter(self.image, name)
                self.assertEqual(result.size, self.image.size)
                self.assertEqual(result.getpixel((0, 0))[3], 170)

    def test_crop_and_resize(self) -> None:
        cropped = crop_image(self.image, (-3, 2, 7, 20))
        self.assertEqual(cropped.size, (7, 6))
        self.assertEqual(resize_image(cropped, 14, 12).size, (14, 12))

    def test_reject_empty_crop_and_invalid_size(self) -> None:
        with self.assertRaises(ValueError):
            crop_image(self.image, (4, 4, 4, 6))
        with self.assertRaises(ValueError):
            resize_image(self.image, 0, 8)


if __name__ == "__main__":
    unittest.main()