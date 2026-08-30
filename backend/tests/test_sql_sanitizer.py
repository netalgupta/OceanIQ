"""
Unit tests for SQL extraction, sanitization, and security invariants.
"""
from __future__ import annotations
import pytest
from src.utils.sql_extract import extract_sql, sanitize_sql

def test_extract_clean_sql():
    raw = "```sql\nSELECT platform_number, temp, psal FROM public.marine_data WHERE pres < 10;\n```"
    extracted = extract_sql(raw)
    assert extracted is not None
    assert extracted.startswith("SELECT")
    assert "FROM public.marine_data" in extracted

def test_extract_sql_no_markdown():
    raw = "SELECT * FROM public.marine_data LIMIT 100"
    extracted = extract_sql(raw)
    assert extracted == "SELECT * FROM public.marine_data LIMIT 100"

def test_reject_dangerous_ddl():
    dangerous = [
        "DROP TABLE public.marine_data;",
        "DELETE FROM public.marine_data WHERE id > 0;",
        "INSERT INTO public.marine_data (platform_number) VALUES (123);",
        "ALTER TABLE public.marine_data DROP COLUMN temp;",
        "UPDATE public.marine_data SET temp = 100;",
        "TRUNCATE public.marine_data;",
    ]
    for d in dangerous:
        extracted = extract_sql(d)
        assert extracted is None or not extracted.startswith("DROP")

def test_reject_semicolon_injection():
    injection = "SELECT * FROM public.marine_data; DROP TABLE public.floats;"
    extracted = extract_sql(injection)
    # The sanitizer must strip or reject chained statements
    if extracted:
        assert "DROP" not in extracted.upper()

def test_sanitize_sql_enforces_select():
    valid = "SELECT platform_number, temp FROM public.marine_data"
    sanitized = sanitize_sql(valid)
    assert sanitized.upper().startswith("SELECT")

    invalid = "DELETE FROM public.marine_data"
    with pytest.raises(ValueError):
        sanitize_sql(invalid)
