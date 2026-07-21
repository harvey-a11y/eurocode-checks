"""Section database tests."""

import pytest

from eurocheck.sections import get_section, list_sections


def test_lookup_tolerates_spacing_and_case():
    canonical = get_section("305x165x40 UB")
    assert get_section("305x165x40UB") is canonical
    assert get_section("305X165X40 ub") is canonical
    assert get_section("  305x165x40  UB ") is canonical


def test_unknown_section_raises_with_available_list():
    with pytest.raises(KeyError, match="Available"):
        get_section("999x999x999 UB")


def test_unit_conversions():
    """Blue Book cm-based values must land in N-mm units."""
    uc = get_section("203x203x46 UC")
    assert uc.A == pytest.approx(5870.0)          # 58.7 cm^2
    assert uc.Iz == pytest.approx(1548e4)         # 1548 cm^4
    assert uc.Wpl_y == pytest.approx(497e3)       # 497 cm^3
    ub = get_section("457x191x67 UB")
    assert ub.Iy == pytest.approx(29380e4)
    assert ub.Wel_y == pytest.approx(1296e3)


def test_database_contents():
    names = {sec.name for sec in list_sections()}
    assert names == {"305x165x40 UB", "203x203x46 UC", "457x191x67 UB"}


def test_h_over_b():
    assert get_section("203x203x46 UC").h_over_b == pytest.approx(203.2 / 203.6)
