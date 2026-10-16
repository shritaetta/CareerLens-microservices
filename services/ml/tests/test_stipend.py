import pytest
from data_loader import parse_numeric_stipend


def test_parse_numeric_stipend_standard_formats():
    assert parse_numeric_stipend("15000") == 15000
    assert parse_numeric_stipend("₹15,000 /month") == 15000
    assert parse_numeric_stipend("$1000 /mo") == 1000
    assert parse_numeric_stipend("25000/month") == 25000
    assert parse_numeric_stipend("Rs. 8,000") == 8000


def test_parse_numeric_stipend_integer_input():
    assert parse_numeric_stipend(20000) == 20000
    assert parse_numeric_stipend(0) == 0


def test_parse_numeric_stipend_non_numeric():
    assert parse_numeric_stipend("Unpaid") == 0
    assert parse_numeric_stipend("Performance Based") == 0
    assert parse_numeric_stipend("") == 0
    assert parse_numeric_stipend(None) == 0
    assert parse_numeric_stipend("N/A") == 0
    assert parse_numeric_stipend("Expenses Covered") == 0


def test_parse_numeric_stipend_with_whitespace():
    assert parse_numeric_stipend("   ₹ 30,000   ") == 30000
    assert parse_numeric_stipend("10000 - 20000") == 1000020000
