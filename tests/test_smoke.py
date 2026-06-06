import importlib
import unittest


class SmokeTest(unittest.TestCase):
    def test_package_imports(self):
        mod = importlib.import_module("akt")
        self.assertIsNotNone(mod)


if __name__ == "__main__":
    unittest.main()
