"""
Unit tests for rule-based SQL generator fallback queries.
"""
from __future__ import annotations
import pytest
from src.llm.sql_gen import generate_fallback_sql
from src.utils.sql_extract import extract_sql

def test_fallback_salinity_equator():
    q = "Show me the salinity profile near the equator in March 2023."
    sql = generate_fallback_sql(q)
    assert "public.marine_data" in sql
    assert "latitude BETWEEN -5 AND 5" in sql
    assert extract_sql(sql) is not None

def test_fallback_bgc_arabian_sea():
    q = "Compare BGC parameters in the Arabian Sea over the last 6 months."
    sql = generate_fallback_sql(q)
    assert "public.marine_data" in sql
    assert "avg_chla" in sql or "avg_doxy" in sql
    assert extract_sql(sql) is not None

def test_fallback_nearest_mumbai():
    q = "Find the 5 closest floats to Mumbai."
    sql = generate_fallback_sql(q)
    assert "public.floats" in sql or "public.marine_data" in sql
    assert extract_sql(sql) is not None

def test_fallback_float_specific():
    q = "Show me all profiles recorded by float 1902303."
    sql = generate_fallback_sql(q)
    assert "1902303" in sql
    assert extract_sql(sql) is not None

def test_fallback_generic():
    q = "Tell me something random about the ocean."
    sql = generate_fallback_sql(q)
    assert sql.startswith("SELECT")
    assert extract_sql(sql) is not None
