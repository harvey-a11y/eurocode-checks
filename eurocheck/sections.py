"""Rolled steel section database for the EC3 checks.

Section properties are taken from the SCI "Blue Book" (P363) tables for
UK Universal Beams (UB) and Universal Columns (UC). Everything is stored
in consistent newton-millimetre units:

* dimensions        mm
* area              mm^2
* second moments    mm^4
* section moduli    mm^3

The database intentionally contains only the sections used by the
validation examples; adding more is a matter of appending rows to
``SECTIONS``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    """A hot-rolled I-section (UB/UC) in N-mm units."""

    name: str
    kind: str        # "UB" or "UC"
    A: float         # cross-sectional area, mm^2
    h: float         # overall depth, mm
    b: float         # flange width, mm
    tw: float        # web thickness, mm
    tf: float        # flange thickness, mm
    r: float         # root radius, mm
    Iy: float        # second moment of area, major (y-y) axis, mm^4
    Iz: float        # second moment of area, minor (z-z) axis, mm^4
    Wpl_y: float     # plastic section modulus, major axis, mm^3
    Wel_y: float     # elastic section modulus, major axis, mm^3

    @property
    def h_over_b(self) -> float:
        """Depth-to-width ratio, used for buckling curve selection."""
        return self.h / self.b


def _section(name: str, kind: str, A_cm2: float, h: float, b: float,
             tw: float, tf: float, r: float, Iy_cm4: float, Iz_cm4: float,
             Wpl_cm3: float, Wel_cm3: float) -> Section:
    """Build a :class:`Section` from Blue Book (cm-based) tabulated values."""
    return Section(
        name=name,
        kind=kind,
        A=A_cm2 * 1.0e2,          # cm^2 -> mm^2
        h=h,
        b=b,
        tw=tw,
        tf=tf,
        r=r,
        Iy=Iy_cm4 * 1.0e4,        # cm^4 -> mm^4
        Iz=Iz_cm4 * 1.0e4,
        Wpl_y=Wpl_cm3 * 1.0e3,    # cm^3 -> mm^3
        Wel_y=Wel_cm3 * 1.0e3,
    )


#: Blue Book excerpt. Keys are the canonical designation.
SECTIONS: dict[str, Section] = {
    "305x165x40 UB": _section("305x165x40 UB", "UB", 51.3, 303.4, 165.0,
                              6.0, 10.2, 8.9, 8503, 764, 623, 560),
    "203x203x46 UC": _section("203x203x46 UC", "UC", 58.7, 203.2, 203.6,
                              7.2, 11.0, 10.2, 4568, 1548, 497, 450),
    "457x191x67 UB": _section("457x191x67 UB", "UB", 85.5, 453.4, 189.9,
                              8.5, 12.7, 10.2, 29380, 1452, 1471, 1296),
}

_LOOKUP: dict[str, str] = {key.upper().replace(" ", ""): key for key in SECTIONS}


def get_section(name: str) -> Section:
    """Look up a section by designation, tolerant of spacing and case.

    ``"305x165x40 UB"``, ``"305x165x40UB"`` and ``"305X165X40 ub"`` all
    resolve to the same entry.

    Raises:
        KeyError: if the designation is not in the database.
    """
    key = name.upper().replace(" ", "")
    if key not in _LOOKUP:
        available = ", ".join(sorted(SECTIONS))
        raise KeyError(f"Unknown section '{name}'. Available: {available}")
    return SECTIONS[_LOOKUP[key]]


def list_sections() -> list[Section]:
    """All sections in the database, in declaration order."""
    return list(SECTIONS.values())
