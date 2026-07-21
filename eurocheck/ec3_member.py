"""EC3 member checks to EN 1993-1-1 with the UK National Annex.

Scope
-----
Hot-rolled I-sections (UB/UC), intended for S275 and S355 steel:

* cross-section classification of flanges and web in major-axis bending
* bending resistance ``Mc,Rd`` for class 1-3 sections
* plastic shear resistance ``Vpl,Rd`` (load parallel to the web)
* flexural buckling resistance ``Nb,Rd`` about either principal axis

Lateral-torsional buckling, class 4 effective sections, and combined
axial + bending interaction are NOT covered.

Partial factors (UK NA): ``gamma_M0 = gamma_M1 = 1.0``.
Units at the public interface: mm, MPa, kN, kNm (``lcr`` in mm).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .sections import Section

E_STEEL = 210000.0    # Young's modulus, MPa (cl. 3.2.6)
GAMMA_M0 = 1.0        # UK NA
GAMMA_M1 = 1.0        # UK NA

#: Imperfection factor alpha for each buckling curve (Table 6.1).
IMPERFECTION = {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}


def _check_positive(**values: float) -> None:
    for label, value in values.items():
        if value <= 0.0:
            raise ValueError(f"{label} must be positive, got {value}")


def epsilon(fy: float) -> float:
    """Material parameter ``epsilon = sqrt(235 / fy)`` (Table 5.2)."""
    _check_positive(fy=fy)
    return math.sqrt(235.0 / fy)


def _class_from_ratio(ratio: float, limits: tuple[float, float, float]) -> int:
    """Slenderness class 1-4 given the class 1/2/3 c/t limits."""
    for cls, limit in zip((1, 2, 3), limits):
        if ratio <= limit:
            return cls
    return 4


@dataclass(frozen=True)
class Classification:
    """Cross-section classification in major-axis bending (Table 5.2)."""

    eps: float
    flange_ratio: float       # outstand c/t
    flange_class: int
    web_ratio: float          # internal part c/t
    web_class: int
    section_class: int        # worst of the two


def classify(section: Section, fy: float) -> Classification:
    """Classify a rolled I-section in major-axis bending.

    * Outstand flange: ``c = (b - tw - 2 r) / 2``, ``t = tf``;
      class 1/2/3 limits ``9 eps / 10 eps / 14 eps``.
    * Web in bending: ``c = h - 2 tf - 2 r``, ``t = tw``;
      class 1/2/3 limits ``72 eps / 83 eps / 124 eps``.
    """
    eps = epsilon(fy)

    c_flange = (section.b - section.tw - 2.0 * section.r) / 2.0
    flange_ratio = c_flange / section.tf
    flange_class = _class_from_ratio(flange_ratio,
                                     (9.0 * eps, 10.0 * eps, 14.0 * eps))

    c_web = section.h - 2.0 * section.tf - 2.0 * section.r
    web_ratio = c_web / section.tw
    web_class = _class_from_ratio(web_ratio,
                                  (72.0 * eps, 83.0 * eps, 124.0 * eps))

    return Classification(
        eps=eps,
        flange_ratio=flange_ratio, flange_class=flange_class,
        web_ratio=web_ratio, web_class=web_class,
        section_class=max(flange_class, web_class),
    )


@dataclass(frozen=True)
class MomentResistance:
    """Major-axis bending resistance (cl. 6.2.5)."""

    section_class: int
    modulus: str              # "Wpl,y" or "Wel,y"
    mc_rd: float              # kNm


def moment_resistance(section: Section, fy: float) -> MomentResistance:
    """``Mc,Rd = Wpl,y fy / gamma_M0`` (class 1/2) or ``Wel,y fy / gamma_M0``
    (class 3). Class 4 sections are out of scope and raise ``ValueError``.

    Note: this is the cross-section resistance only. Lateral-torsional
    buckling is NOT checked; the value is only usable directly for
    fully restrained beams.
    """
    cls = classify(section, fy).section_class
    if cls <= 2:
        modulus, label = section.Wpl_y, "Wpl,y"
    elif cls == 3:
        modulus, label = section.Wel_y, "Wel,y"
    else:
        raise ValueError(
            f"{section.name}: class 4 (slender) section; effective-section "
            f"bending resistance is out of scope for this tool"
        )
    return MomentResistance(section_class=cls, modulus=label,
                            mc_rd=modulus * fy / GAMMA_M0 / 1.0e6)


@dataclass(frozen=True)
class ShearResistance:
    """Plastic shear resistance (cl. 6.2.6)."""

    av: float                 # shear area, mm^2
    vpl_rd: float             # kN


def shear_resistance(section: Section, fy: float) -> ShearResistance:
    """``Vpl,Rd = Av (fy / sqrt(3)) / gamma_M0`` for a rolled I-section
    loaded parallel to the web, with
    ``Av = A - 2 b tf + (tw + 2 r) tf``.
    """
    _check_positive(fy=fy)
    av = (section.A - 2.0 * section.b * section.tf
          + (section.tw + 2.0 * section.r) * section.tf)
    return ShearResistance(av=av,
                           vpl_rd=av * (fy / math.sqrt(3.0)) / GAMMA_M0 / 1.0e3)


def buckling_curve(section: Section, axis: str) -> tuple[str, float]:
    """Buckling curve and imperfection factor for a rolled I-section
    (Table 6.2), for S275/S355 steel.

    * ``h/b > 1.2``:  ``tf <= 40`` -> a (y-y), b (z-z);
      ``40 < tf <= 100`` -> b (y-y), c (z-z)
    * ``h/b <= 1.2``: ``tf <= 100`` -> b (y-y), c (z-z);
      ``tf > 100`` -> d (both axes)
    """
    if axis not in ("y", "z"):
        raise ValueError(f"axis must be 'y' or 'z', got {axis!r}")

    hb, tf = section.h_over_b, section.tf
    if hb > 1.2:
        if tf <= 40.0:
            curve = "a" if axis == "y" else "b"
        elif tf <= 100.0:
            curve = "b" if axis == "y" else "c"
        else:
            raise ValueError(
                f"{section.name}: h/b > 1.2 with tf > 100 mm is outside "
                f"Table 6.2 for rolled sections"
            )
    else:
        if tf <= 100.0:
            curve = "b" if axis == "y" else "c"
        else:
            curve = "d"
    return curve, IMPERFECTION[curve]


@dataclass(frozen=True)
class BucklingResistance:
    """Flexural buckling resistance of a compression member (cl. 6.3.1)."""

    axis: str                 # "y" or "z"
    curve: str
    alpha: float
    ncr: float                # elastic critical force, kN
    lambda_bar: float         # non-dimensional slenderness
    phi: float
    chi: float                # reduction factor (<= 1)
    nb_rd: float              # kN


def flexural_buckling(section: Section, fy: float, lcr: float,
                      axis: str) -> BucklingResistance:
    """Flexural buckling resistance about the given axis.

    * ``Ncr = pi^2 E I / Lcr^2`` (``E = 210000 MPa``, ``lcr`` in mm)
    * ``lambda_bar = sqrt(A fy / Ncr)``
    * ``Phi = 0.5 (1 + alpha (lambda_bar - 0.2) + lambda_bar^2)``
    * ``chi = min(1, 1 / (Phi + sqrt(Phi^2 - lambda_bar^2)))``
    * ``Nb,Rd = chi A fy / gamma_M1``
    """
    _check_positive(fy=fy, lcr=lcr)
    curve, alpha = buckling_curve(section, axis)  # validates axis

    inertia = section.Iy if axis == "y" else section.Iz
    ncr = math.pi ** 2 * E_STEEL * inertia / lcr ** 2
    lambda_bar = math.sqrt(section.A * fy / ncr)
    phi = 0.5 * (1.0 + alpha * (lambda_bar - 0.2) + lambda_bar ** 2)
    chi = min(1.0, 1.0 / (phi + math.sqrt(phi ** 2 - lambda_bar ** 2)))
    nb_rd = chi * section.A * fy / GAMMA_M1

    return BucklingResistance(axis=axis, curve=curve, alpha=alpha,
                              ncr=ncr / 1.0e3, lambda_bar=lambda_bar,
                              phi=phi, chi=chi, nb_rd=nb_rd / 1.0e3)
