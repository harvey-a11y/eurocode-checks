# eurocheck

Eurocode 2 / Eurocode 3 member design checks in pure Python.

An educational structural engineering library covering a defined subset
of EN 1992-1-1 (concrete) and EN 1993-1-1 (steel) member checks, with UK
National Annex parameters built in. Written as a portfolio project by a
civil engineering undergraduate; every result type it produces (EC2
flexure and the shear trio, EC3 classification, `Mc,Rd`, `Vpl,Rd` and
`Nb,Rd`) is anchored to an independent worked hand calculation in
[VALIDATION.md](VALIDATION.md).

> **This is not a certified design package.** It implements a small,
> well-defined subset of the Eurocodes so that hand calculations can be
> checked and automated for coursework. Nothing it outputs should be
> used for construction without independent verification by a qualified
> engineer.

## Scope

What the library covers, and what it deliberately does not:

| Area | Covered | NOT covered |
| --- | --- | --- |
| EC2 bending | Rectangular, singly reinforced sections: design (`As,req` for `MEd`) and capacity (`MRd` for a given `As`), fck <= 50 MPa, UK NA `alpha_cc = 0.85`; ductility flags (`K'` = 0.167, `x/d` <= 0.45) | Compression (doubly reinforced) sections, flanged T/L beams, fck > 50 MPa, moment redistribution |
| EC2 shear | `VRd,c` for members without links (with the `v_min` floor), `VRd,s` and `VRd,max` for vertical links with variable strut inclination (1 <= cot theta <= 2.5); `alpha_cc = 1.0` for the `VRd,max` crushing check (UK NA Table NA.1 / PD 6687-1) | Punching shear, shear between web and flanges, torsion, bent-up bars |
| EC2 serviceability | Nothing | Deflection, crack width, stress limits: no SLS checks at all |
| EC3 cross-section | Classification of rolled I flanges and webs in major-axis bending (classes 1-3), `Mc,Rd` (class 1/2 plastic, class 3 elastic), `Vpl,Rd` (load parallel to web) | Class 4 effective sections, welded sections, webs under axial/combined stress, shear buckling |
| EC3 stability | Flexural buckling `Nb,Rd` about y-y or z-z with Table 6.2 curve selection for rolled I-sections | **Lateral-torsional buckling**, torsional and torsional-flexural buckling, member interaction (cl. 6.3.3), frame stability |
| Sections | Three-section SCI Blue Book excerpt: 305x165x40 UB, 203x203x46 UC, 457x191x67 UB | Everything else (the database is a plain dict; adding rows is trivial) |

Because there is no LTB check, the `Mc,Rd` reported for beams is only
directly usable where the compression flange is fully restrained. The
CLI says so on every beam run.

## Installation

Python 3.11+. No required dependencies beyond the standard library.

```
python -m pip install -e .
```

Optional extras: `pip install -e .[dev]` for pytest, `.[plot]` for
matplotlib (not needed for any check).

## Command-line usage

```
python -m eurocheck ec2-beam   --b 300 --d 450 --fck 30 --fyk 500 --med 200
python -m eurocheck ec2-shear  --b 300 --d 450 --fck 30 --asl 1470 --asw 157 --s 200
python -m eurocheck ec3-beam   --section 305x165x40UB --fy 275
python -m eurocheck ec3-column --section 203x203x46UC --fy 275 --lcr 4.0 --axis z
python -m eurocheck sections
```

Units: dimensions in mm, strengths in MPa, moments in kNm, effective
length `--lcr` in metres.

## Library usage

```python
from eurocheck import get_section, ec2_beam, ec3_member

# EC2: steel required for a 200 kNm moment
res = ec2_beam.design_flexure(b=300, d=450, fck=30, fyk=500, m_ed=200)
print(res.as_req)        # 1146.8 mm^2

# EC3: column buckling resistance
sec = get_section("203x203x46 UC")
buck = ec3_member.flexural_buckling(sec, fy=275, lcr=4000, axis="z")
print(buck.nb_rd)        # 971.0 kN
```

All results are frozen dataclasses carrying the intermediate values
(K, z, lambda_bar, chi, ...) so a hand calculation can be checked line
by line, not just against the final number.

## Validation

Worked hand calculations anchor every result type, written out step by
step in [VALIDATION.md](VALIDATION.md) and asserted in the test suite:

* `Mc,Rd` of a 305x165x40 UB in S275 = 171.3 kNm (class 1, plastic;
  the classification arithmetic is worked in the same section)
* `As,req` for a 300x450 fck 30 beam under 200 kNm = 1146.8 mm^2
* `Nb,Rd` of a 203x203x46 UC in S275, Lcr = 4.0 m about z-z = 971.0 kN
* `VRd,c` of the same 300x450 beam with Asl = 1147 mm^2 = 79.5 kN
* `VRd,s` / `VRd,max` of that beam with H10 links at 200 mm,
  cot theta = 2.5: 345.6 / 442.4 kN
* `Vpl,Rd` of a 457x191x67 UB in S275 = 649.9 kN (the cl. 6.2.6(3)a
  `eta hw tw` floor is checked and does not govern with the UK NA
  `eta = 1.0`)

Plus physics assertions: `chi <= 1` always, `VRd,c` floors at `v_min`,
class 1/2 sections use the plastic modulus, out-of-scope situations
(K > K', class 4, cot theta out of range, fck > 50) are reported or
raised, never silently computed.

Run the suite with:

```
python -m pytest
```

## Roadmap

Roughly in order of intent:

1. Lateral-torsional buckling (EN 1993-1-1 cl. 6.3.2) so unrestrained
   beams can be checked honestly.
2. Doubly reinforced EC2 sections (remove the K > K' limitation).
3. EC2 span/effective-depth deflection check (cl. 7.4.2).
4. Combined axial + bending interaction for columns (cl. 6.3.3).
5. Full UB/UC section database imported from the Blue Book tables.

## References

* BS EN 1992-1-1:2004+A1:2014, Eurocode 2: Design of concrete
  structures, Part 1-1, and its UK National Annex.
* BS EN 1993-1-1:2005+A1:2014, Eurocode 3: Design of steel structures,
  Part 1-1, and its UK National Annex.
* SCI P363, "Steel Building Design: Design Data" (the Blue Book):
  section properties and comparison resistance values.
* The Concrete Centre, "Concise Eurocode 2" (the K, K', z design route).

## License

MIT, Copyright (c) 2026 Harvey Sohal. See [LICENSE](LICENSE).
