import unittest
from unittest.mock import patch

from ezphoto.i18n import automatic_language, translate


class LanguageTests(unittest.TestCase):
    def test_unsupported_system_language_falls_back_to_english(self) -> None:
        with (
            patch("ezphoto.i18n.QLocale.system") as system_locale,
            patch("ezphoto.i18n.locale.getlocale", return_value=("de_DE", "UTF-8")),
        ):
            system_locale.return_value.name.return_value = "de_DE"
            self.assertEqual(automatic_language(), "en")

    def test_translations_fall_back_to_english(self) -> None:
        self.assertEqual(translate("open", "de"), "Open")


if __name__ == "__main__":
    unittest.main()