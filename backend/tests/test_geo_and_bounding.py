"""
Unit tests for geospatial classification, bounding box inferences, and city coordinates.
"""
from __future__ import annotations
import pytest
from src.utils.geo import city_lookup, infer_coast_from_name, classify_region

def test_city_lookup_valid():
    mumbai = city_lookup("mumbai")
    assert mumbai is not None
    assert pytest.approx(mumbai["lat"], 0.01) == 19.076
    assert pytest.approx(mumbai["lon"], 0.01) == 72.877

    kochi = city_lookup("Kochi")
    assert kochi is not None
    assert pytest.approx(kochi["lat"], 0.01) == 9.931

    chennai = city_lookup("chennai ")
    assert chennai is not None
    assert pytest.approx(chennai["lon"], 0.01) == 80.270

def test_city_lookup_invalid():
    assert city_lookup("paris") is None
    assert city_lookup("") is None

def test_infer_coast():
    assert infer_coast_from_name("Nearest float to Mumbai") == "west"
    assert infer_coast_from_name("Floats along the Kerala coast") == "west"
    assert infer_coast_from_name("Temperature in the Bay of Bengal") == "east"
    assert infer_coast_from_name("Floats near Chennai and Vizag") == "east"
    assert infer_coast_from_name("Random query without coast terms") is None

def test_classify_region():
    # Arabian Sea: lat 5-25, lon 40-75
    assert classify_region(15.0, 65.0) == "arabian_sea"
    assert classify_region(19.0, 72.0) == "arabian_sea"

    # Bay of Bengal: lat 5-25, lon 75-100
    assert classify_region(15.0, 88.0) == "bay_of_bengal"
    assert classify_region(12.0, 92.0) == "bay_of_bengal"

    # Equatorial Indian Ocean: lat -5 to 5, lon 40-115
    assert classify_region(0.0, 77.0) == "equatorial_io"
    assert classify_region(-2.0, 80.0) == "equatorial_io"

    # Southern Indian Ocean: lat < -30
    assert classify_region(-35.0, 60.0) == "southern_io"

    # Red Sea & Persian Gulf
    assert classify_region(20.0, 38.0) == "red_sea"
    assert classify_region(26.0, 52.0) == "persian_gulf"
