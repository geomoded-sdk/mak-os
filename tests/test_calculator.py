"""Testes da lógica da Calculadora do Mak OS (função pura evaluate)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Apps", "Calculator"))
from mak_calculator import evaluate  # noqa: E402


class TestEvaluate(unittest.TestCase):
    def test_simple_addition(self):
        self.assertEqual(evaluate("2+3"), "5")

    def test_decimal(self):
        self.assertEqual(evaluate("5.5+4.5"), "10")

    def test_multiplication(self):
        self.assertEqual(evaluate("7*6"), "42")

    def test_division(self):
        self.assertEqual(evaluate("9/2"), "4.5")

    def test_precedence(self):
        self.assertEqual(evaluate("2+3*4"), "14")

    def test_parentheses(self):
        self.assertEqual(evaluate("(2+3)*4"), "20")

    def test_unary_minus(self):
        self.assertEqual(evaluate("-5+2"), "-3")

    def test_percent_expansion(self):
        self.assertEqual(evaluate("50/100"), "0.5")

    def test_power(self):
        self.assertEqual(evaluate("2**10"), "1024")

    def test_division_by_zero(self):
        self.assertEqual(evaluate("1/0"), "Erro")

    def test_invalid_expression(self):
        self.assertEqual(evaluate("2+"), "Erro")
        self.assertEqual(evaluate("abc"), "Erro")

    def test_empty(self):
        self.assertEqual(evaluate(""), "0")

    def test_float_formatting(self):
        self.assertEqual(evaluate("0.1+0.2"), "0.3")


if __name__ == "__main__":
    unittest.main()
