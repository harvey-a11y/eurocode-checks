"""Command-line interface for the eurocheck package.

Examples::

    python -m eurocheck ec2-beam --b 300 --d 450 --fck 30 --fyk 500 --med 200
    python -m eurocheck ec2-shear --b 300 --d 450 --fck 30 --asl 1470 --asw 157 --s 200
    python -m eurocheck ec3-beam --section 305x165x40UB --fy 275
    python -m eurocheck ec3-column --section 203x203x46UC --fy 275 --lcr 4.0 --axis z
    python -m eurocheck sections
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, ec2_beam, ec3_member
from .sections import get_section, list_sections

_DISCLAIMER = "educational tool; verify independently before any real use"


def _cmd_ec2_beam(args: argparse.Namespace) -> int:
    res = ec2_beam.design_flexure(args.b, args.d, args.fck, args.fyk, args.med)
    print("EC2 beam flexure design (EN 1992-1-1 + UK NA)")
    print(f"  section     b = {args.b:g} mm, d = {args.d:g} mm")
    print(f"  materials   fck = {args.fck:g} MPa, fyk = {args.fyk:g} MPa")
    print(f"              fcd = {ec2_beam.f_cd(args.fck):.2f} MPa, "
          f"fyd = {ec2_beam.f_yd(args.fyk):.1f} MPa")
    print(f"  action      MEd = {args.med:g} kNm")
    print(f"  K = MEd/(b d^2 fck) = {res.K:.4f}   (K' = {res.K_lim:.3f})")
    if res.singly_reinforced:
        print(f"  z = {res.z:.1f} mm   (0.95d cap = {0.95 * args.d:.1f} mm)")
        print(f"  As,req = {res.as_req:.0f} mm^2")
    print(f"  RESULT: {res.note}")
    print(f"  note: {_DISCLAIMER}")
    return 0


def _cmd_ec2_shear(args: argparse.Namespace) -> int:
    if (args.asw is None) != (args.s is None):
        print("error: --asw and --s must be given together (got only one; "
              "supply both for a link check, or neither for VRd,c only)",
              file=sys.stderr)
        return 2
    con = ec2_beam.shear_concrete(args.b, args.d, args.fck, args.asl)
    print("EC2 beam shear (EN 1992-1-1 + UK NA)")
    print(f"  section     b = {args.b:g} mm, d = {args.d:g} mm, "
          f"fck = {args.fck:g} MPa")
    print(f"  k = {con.k:.3f}, rho_l = {con.rho_l:.5f}, "
          f"v_min = {con.v_min:.3f} MPa")
    governs = "v_min governs" if con.vmin_governs else "strength term governs"
    print(f"  VRd,c = {con.v_rd_c:.1f} kN   ({governs})")
    if args.asw is not None and args.s is not None:
        links = ec2_beam.shear_links(args.b, args.d, args.fck, args.fywk,
                                     args.asw, args.s, args.cot)
        print(f"  links       Asw = {args.asw:g} mm^2 at s = {args.s:g} mm, "
              f"fywk = {args.fywk:g} MPa, cot(theta) = {args.cot:g}")
        print(f"  z = {links.z:.1f} mm, nu1 = {links.nu1:.3f}")
        print(f"  VRd,s   = {links.v_rd_s:.1f} kN")
        print(f"  VRd,max = {links.v_rd_max:.1f} kN")
        print(f"  VRd     = {links.v_rd:.1f} kN (governing)")
    print(f"  note: {_DISCLAIMER}")
    return 0


def _cmd_ec3_beam(args: argparse.Namespace) -> int:
    sec = get_section(args.section)
    cls = ec3_member.classify(sec, args.fy)
    mom = ec3_member.moment_resistance(sec, args.fy)
    shr = ec3_member.shear_resistance(sec, args.fy)
    print("EC3 beam cross-section checks (EN 1993-1-1 + UK NA)")
    print(f"  section     {sec.name}, fy = {args.fy:g} MPa "
          f"(epsilon = {cls.eps:.3f})")
    print(f"  flange      c/t = {cls.flange_ratio:.2f} -> class "
          f"{cls.flange_class}")
    print(f"  web         c/t = {cls.web_ratio:.2f} -> class {cls.web_class}")
    print(f"  section class {cls.section_class} -> {mom.modulus} governs")
    print(f"  Mc,Rd  = {mom.mc_rd:.1f} kNm   "
          f"(no LTB check: valid for fully restrained beams only)")
    av_src = ("eta*hw*tw floor, cl. 6.2.6(3)a" if shr.floor_governs
              else "A - 2*b*tf + (tw + 2r)*tf")
    print(f"  Av     = {shr.av:.0f} mm^2   ({av_src} governs)")
    print(f"  Vpl,Rd = {shr.vpl_rd:.1f} kN")
    print(f"  note: {_DISCLAIMER}")
    return 0


def _cmd_ec3_column(args: argparse.Namespace) -> int:
    sec = get_section(args.section)
    res = ec3_member.flexural_buckling(sec, args.fy, args.lcr * 1000.0,
                                       args.axis)
    print("EC3 column flexural buckling (EN 1993-1-1 + UK NA)")
    print(f"  section     {sec.name} (h/b = {sec.h_over_b:.2f})")
    print(f"  materials   fy = {args.fy:g} MPa, E = {ec3_member.E_STEEL:g} MPa")
    print(f"  buckling    Lcr = {args.lcr:g} m about {args.axis}-{args.axis}, "
          f"curve {res.curve} (alpha = {res.alpha})")
    print(f"  Ncr        = {res.ncr:.1f} kN")
    print(f"  lambda_bar = {res.lambda_bar:.3f}")
    print(f"  Phi        = {res.phi:.3f}")
    print(f"  chi        = {res.chi:.3f}")
    print(f"  Nb,Rd      = {res.nb_rd:.1f} kN")
    print(f"  note: {_DISCLAIMER}")
    return 0


def _cmd_sections(args: argparse.Namespace) -> int:
    print("Section database (SCI Blue Book excerpt, N-mm units)")
    header = (f"  {'name':<16}{'A mm^2':>9}{'h mm':>8}{'b mm':>8}"
              f"{'tw':>6}{'tf':>6}{'r':>6}{'Wpl,y mm^3':>13}")
    print(header)
    for sec in list_sections():
        print(f"  {sec.name:<16}{sec.A:>9.0f}{sec.h:>8.1f}{sec.b:>8.1f}"
              f"{sec.tw:>6.1f}{sec.tf:>6.1f}{sec.r:>6.1f}{sec.Wpl_y:>13.0f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eurocheck",
        description=("Educational EC2/EC3 member design checks. "
                     "Not a certified design package."),
    )
    parser.add_argument("--version", action="version",
                        version=f"eurocheck {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ec2-beam",
                       help="EC2 singly reinforced beam: As required for MEd")
    p.add_argument("--b", type=float, required=True, help="width, mm")
    p.add_argument("--d", type=float, required=True, help="effective depth, mm")
    p.add_argument("--fck", type=float, required=True,
                   help="concrete cylinder strength, MPa (<= 50)")
    p.add_argument("--fyk", type=float, required=True,
                   help="reinforcement characteristic yield, MPa")
    p.add_argument("--med", type=float, required=True,
                   help="design moment MEd, kNm")
    p.set_defaults(func=_cmd_ec2_beam)

    p = sub.add_parser("ec2-shear",
                       help="EC2 shear: VRd,c, and VRd,s/VRd,max if links given")
    p.add_argument("--b", type=float, required=True, help="width, mm")
    p.add_argument("--d", type=float, required=True, help="effective depth, mm")
    p.add_argument("--fck", type=float, required=True,
                   help="concrete cylinder strength, MPa (<= 50)")
    p.add_argument("--asl", type=float, required=True,
                   help="anchored tension steel area Asl, mm^2")
    p.add_argument("--asw", type=float, default=None,
                   help="link area per set (all legs), mm^2")
    p.add_argument("--s", type=float, default=None, help="link spacing, mm")
    p.add_argument("--fywk", type=float, default=500.0,
                   help="link characteristic yield, MPa (default 500)")
    p.add_argument("--cot", type=float, default=2.5,
                   help="cot(theta), 1 to 2.5 (default 2.5)")
    p.set_defaults(func=_cmd_ec2_shear)

    p = sub.add_parser("ec3-beam",
                       help="EC3 rolled I-beam: classification, Mc,Rd, Vpl,Rd")
    p.add_argument("--section", required=True,
                   help="designation, e.g. 305x165x40UB")
    p.add_argument("--fy", type=float, required=True,
                   help="yield strength, MPa (e.g. 275 or 355)")
    p.set_defaults(func=_cmd_ec3_beam)

    p = sub.add_parser("ec3-column",
                       help="EC3 rolled I-column: flexural buckling Nb,Rd")
    p.add_argument("--section", required=True,
                   help="designation, e.g. 203x203x46UC")
    p.add_argument("--fy", type=float, required=True,
                   help="yield strength, MPa (e.g. 275 or 355)")
    p.add_argument("--lcr", type=float, required=True,
                   help="effective (buckling) length, m")
    p.add_argument("--axis", choices=("y", "z"), required=True,
                   help="buckling axis: y (major) or z (minor)")
    p.set_defaults(func=_cmd_ec3_column)

    p = sub.add_parser("sections", help="list the section database")
    p.set_defaults(func=_cmd_sections)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyError as exc:
        print(f"error: {exc.args[0]}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
