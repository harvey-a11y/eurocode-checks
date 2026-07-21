"""EC2 beam checks to EN 1992-1-1 with the UK National Annex.

Scope
-----
Rectangular, singly reinforced sections in normal-weight concrete with
``fck <= 50 MPa``, so the rectangular stress block factors are
``lambda = 0.8`` and ``eta = 1.0`` (cl. 3.1.7(3)) and the simplified
lever-arm expression applies. Doubly reinforced (compression steel)
design, flanged sections and higher-strength concretes are out of scope.

Partial factors and coefficients (UK NA):

* ``alpha_cc = 0.85`` (UK NA to cl. 3.1.6(1))
* ``gamma_c = 1.5``, ``gamma_s = 1.15``
* ``fcd = alpha_cc * fck / gamma_c``
* ``fyd = fyk / gamma_s``

Units at the public interface: mm, MPa (N/mm^2), kN, kNm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

ALPHA_CC = 0.85       # UK NA to EN 1992-1-1, cl. 3.1.6(1)
GAMMA_C = 1.5
GAMMA_S = 1.15
LAMBDA = 0.8          # stress block depth factor, cl. 3.1.7(3), fck <= 50 MPa
ETA = 1.0             # effective strength factor, cl. 3.1.7(3), fck <= 50 MPa
K_LIM = 0.167         # ductility limit on K = MEd/(b d^2 fck)
X_OVER_D_LIMIT = 0.45  # neutral axis depth limit for a ductile section
RHO_L_MAX = 0.02      # cap on longitudinal ratio in VRd,c (cl. 6.2.2)
COT_THETA_MIN = 1.0   # variable strut inclination limits (cl. 6.2.3)
COT_THETA_MAX = 2.5


def _check_positive(**values: float) -> None:
    for label, value in values.items():
        if value <= 0.0:
            raise ValueError(f"{label} must be positive, got {value}")


def _check_fck(fck: float) -> None:
    if not 0.0 < fck <= 50.0:
        raise ValueError(
            f"fck must be in (0, 50] MPa for this tool "
            f"(lambda = 0.8, eta = 1.0 stress block), got {fck}"
        )


def f_cd(fck: float) -> float:
    """Design compressive strength ``fcd = 0.85 * fck / 1.5``, MPa."""
    _check_fck(fck)
    return ALPHA_CC * fck / GAMMA_C


def f_yd(fyk: float) -> float:
    """Design steel yield strength ``fyd = fyk / 1.15``, MPa."""
    _check_positive(fyk=fyk)
    return fyk / GAMMA_S


@dataclass(frozen=True)
class FlexureDesign:
    """Result of a singly reinforced flexural design for MEd."""

    b: float                  # mm
    d: float                  # mm
    fck: float                # MPa
    fyk: float                # MPa
    m_ed: float               # kNm
    K: float
    K_lim: float
    singly_reinforced: bool
    z: float | None           # lever arm, mm (None if K > K')
    as_req: float | None      # required tension steel, mm^2 (None if K > K')
    note: str


def design_flexure(b: float, d: float, fck: float, fyk: float,
                   m_ed: float) -> FlexureDesign:
    """Required tension reinforcement for a design moment ``m_ed`` (kNm).

    Implements the standard UK design route:

    * ``K = MEd / (b d^2 fck)``; ductility limit ``K' = 0.167``
    * ``z = min(0.95 d, (d/2) (1 + sqrt(1 - 3.53 K)))``
    * ``As,req = MEd / (fyd z)``

    If ``K > K'`` the section needs compression reinforcement, which is
    out of scope: the result reports this and ``as_req`` is ``None``.
    """
    _check_positive(b=b, d=d, fyk=fyk, m_ed=m_ed)
    _check_fck(fck)

    m = m_ed * 1.0e6  # kNm -> Nmm
    K = m / (b * d ** 2 * fck)

    if K > K_LIM:
        return FlexureDesign(
            b=b, d=d, fck=fck, fyk=fyk, m_ed=m_ed,
            K=K, K_lim=K_LIM, singly_reinforced=False, z=None, as_req=None,
            note=(f"compression reinforcement required "
                  f"(K = {K:.4f} > K' = {K_LIM}); doubly reinforced design "
                  f"is out of scope for this tool"),
        )

    z = min(0.95 * d, (d / 2.0) * (1.0 + math.sqrt(1.0 - 3.53 * K)))
    as_req = m / (f_yd(fyk) * z)
    return FlexureDesign(
        b=b, d=d, fck=fck, fyk=fyk, m_ed=m_ed,
        K=K, K_lim=K_LIM, singly_reinforced=True, z=z, as_req=as_req,
        note="singly reinforced section is sufficient",
    )


@dataclass(frozen=True)
class MomentCapacity:
    """Moment capacity of a given singly reinforced section."""

    x: float                  # neutral axis depth, mm
    x_over_d: float
    m_rd: float               # kNm
    ductile: bool             # x/d <= 0.45
    note: str


def moment_capacity(b: float, d: float, fck: float, fyk: float,
                    as_prov: float) -> MomentCapacity:
    """Moment resistance ``MRd`` of a section with tension steel ``as_prov``.

    Rectangular stress block (``lambda = 0.8``, ``eta = 1.0``), steel
    assumed yielding:

    * ``x = As fyd / (eta fcd b lambda)``
    * ``MRd = As fyd (d - lambda x / 2)``

    The result is flagged non-ductile if ``x/d > 0.45`` (the steel-yield
    assumption is then unreliable and the section lacks rotation
    capacity).
    """
    _check_positive(b=b, d=d, fyk=fyk, as_prov=as_prov)
    _check_fck(fck)

    fyd = f_yd(fyk)
    x = as_prov * fyd / (ETA * f_cd(fck) * b * LAMBDA)
    x_over_d = x / d
    m_rd = as_prov * fyd * (d - LAMBDA * x / 2.0) / 1.0e6
    ductile = x_over_d <= X_OVER_D_LIMIT
    note = ("ductile section (x/d <= 0.45)" if ductile else
            f"x/d = {x_over_d:.3f} > 0.45: over-reinforced, capacity "
            f"unreliable (steel may not yield)")
    return MomentCapacity(x=x, x_over_d=x_over_d, m_rd=m_rd,
                          ductile=ductile, note=note)


@dataclass(frozen=True)
class ShearConcrete:
    """Shear resistance of a member without shear reinforcement."""

    k: float                  # size effect factor
    rho_l: float              # longitudinal reinforcement ratio (capped 0.02)
    v_min: float              # MPa
    v_rd_c: float             # kN
    vmin_governs: bool


def shear_concrete(b: float, d: float, fck: float, asl: float) -> ShearConcrete:
    """``VRd,c`` to cl. 6.2.2(1) (members not requiring design links).

    * ``k = min(2, 1 + sqrt(200/d))`` with d in mm
    * ``rho_l = min(0.02, Asl / (b d))``
    * ``v_min = 0.035 k^1.5 sqrt(fck)``
    * ``VRd,c = max(0.18/1.5 * k * (100 rho_l fck)^(1/3), v_min) * b d``

    ``asl`` is the area of fully anchored tension steel at the section
    considered (may be zero; the ``v_min`` floor then governs).
    """
    _check_positive(b=b, d=d)
    _check_fck(fck)
    if asl < 0.0:
        raise ValueError(f"asl must be >= 0, got {asl}")

    k = min(2.0, 1.0 + math.sqrt(200.0 / d))
    rho_l = min(RHO_L_MAX, asl / (b * d))
    v_min = 0.035 * k ** 1.5 * math.sqrt(fck)
    v_base = (0.18 / GAMMA_C) * k * (100.0 * rho_l * fck) ** (1.0 / 3.0)
    v = max(v_base, v_min)
    return ShearConcrete(
        k=k, rho_l=rho_l, v_min=v_min,
        v_rd_c=v * b * d / 1.0e3,
        vmin_governs=v_base < v_min,
    )


@dataclass(frozen=True)
class ShearLinks:
    """Shear resistance with vertical links (variable strut inclination)."""

    z: float                  # lever arm 0.9 d, mm
    nu1: float                # strength reduction factor for cracked concrete
    cot_theta: float
    v_rd_s: float             # link resistance, kN
    v_rd_max: float           # strut crushing limit, kN
    v_rd: float               # governing = min(v_rd_s, v_rd_max), kN


def shear_links(b: float, d: float, fck: float, fywk: float, asw: float,
                s: float, cot_theta: float = 2.5) -> ShearLinks:
    """``VRd,s`` and ``VRd,max`` to cl. 6.2.3 (vertical links).

    * ``VRd,s = (Asw / s) z fywd cot(theta)`` with ``z = 0.9 d``
    * ``VRd,max = b z nu1 fcd cot(theta) / (1 + cot(theta)^2)``
      with ``nu1 = 0.6 (1 - fck/250)``
    * ``1 <= cot(theta) <= 2.5``

    ``asw`` is the link area per set (all legs crossing the shear plane),
    ``s`` the link spacing.
    """
    _check_positive(b=b, d=d, fywk=fywk, asw=asw, s=s)
    _check_fck(fck)
    if not COT_THETA_MIN <= cot_theta <= COT_THETA_MAX:
        raise ValueError(
            f"cot(theta) must be within [{COT_THETA_MIN}, {COT_THETA_MAX}], "
            f"got {cot_theta}"
        )

    z = 0.9 * d
    fywd = fywk / GAMMA_S
    nu1 = 0.6 * (1.0 - fck / 250.0)
    v_rd_s = (asw / s) * z * fywd * cot_theta / 1.0e3
    v_rd_max = (b * z * nu1 * f_cd(fck) * cot_theta
                / (1.0 + cot_theta ** 2) / 1.0e3)
    return ShearLinks(z=z, nu1=nu1, cot_theta=cot_theta,
                      v_rd_s=v_rd_s, v_rd_max=v_rd_max,
                      v_rd=min(v_rd_s, v_rd_max))
