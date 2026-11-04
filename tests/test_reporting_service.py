import unittest
import datetime as dt

from services.reporting_service import get_fortnight_periods, format_currency_es_co


class ReportingServiceTests(unittest.TestCase):
    def test_formato_moneda_es_co(self):
        self.assertEqual(format_currency_es_co(1234567), "$1.234.567")
        self.assertEqual(format_currency_es_co(0), "$0")

    def test_quincena_oficial_dia_15(self):
        current, previous = get_fortnight_periods(dt.date(2026, 11, 15), mode="official")
        self.assertEqual(current["start"], dt.date(2026, 11, 1))
        self.assertEqual(current["end"], dt.date(2026, 11, 15))
        self.assertEqual(previous["start"], dt.date(2026, 10, 16))
        self.assertEqual(previous["end"], dt.date(2026, 10, 31))

    def test_quincena_oficial_ultimo_dia(self):
        current, previous = get_fortnight_periods(dt.date(2026, 11, 30), mode="official")
        self.assertEqual(current["start"], dt.date(2026, 11, 16))
        self.assertEqual(current["end"], dt.date(2026, 11, 30))
        self.assertEqual(previous["start"], dt.date(2026, 11, 1))
        self.assertEqual(previous["end"], dt.date(2026, 11, 15))

    def test_quincena_previa_en_curso(self):
        current, previous = get_fortnight_periods(dt.date(2026, 11, 3), mode="preview")
        self.assertEqual(current["start"], dt.date(2026, 11, 1))
        self.assertEqual(current["end"], dt.date(2026, 11, 3))
        self.assertEqual(current["label"], "Quincena en curso: 3 de 15 días")
        self.assertEqual(previous["start"], dt.date(2026, 10, 16))
        self.assertEqual(previous["end"], dt.date(2026, 10, 31))

    def test_febrero_y_year_change(self):
        current, previous = get_fortnight_periods(dt.date(2026, 2, 15), mode="official")
        self.assertEqual(current["end"], dt.date(2026, 2, 15))
        self.assertEqual(previous["end"], dt.date(2026, 1, 31))

        current, previous = get_fortnight_periods(dt.date(2026, 1, 31), mode="official")
        self.assertEqual(current["start"], dt.date(2026, 1, 16))
        self.assertEqual(current["end"], dt.date(2026, 1, 31))

    def test_no_future_dates_in_preview(self):
        current, previous = get_fortnight_periods(dt.date(2026, 11, 3), mode="preview")
        self.assertLessEqual(current["start"], current["end"])
        self.assertLessEqual(current["end"], dt.date(2026, 11, 3))
        self.assertLessEqual(previous["start"], previous["end"])


if __name__ == "__main__":
    unittest.main()
