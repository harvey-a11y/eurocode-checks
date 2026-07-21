# Validation

Every anchor below is worked by hand, then asserted in the test suite
(`tests/`) against the library output within the stated tolerance. Units:
mm, MPa (N/mm^2), kN, kNm unless noted.

## 1. Steel beam bending: 305x165x40 UB, S275

**Check:** classification and major-axis bending resistance to
EN 1993-1-1 (UK NA, gamma_M0 = 1.0).

Section properties (SCI Blue Book): h = 303.4 mm, b = 165.0 mm,
tw = 6.0 mm, tf = 10.2 mm, r = 8.9 mm, Wpl,y = 623 cm^3.

**Classification (Table 5.2), fy = 275 MPa:**

    epsilon = sqrt(235/275) = 0.9244

    Outstand flange:  c = (b - tw - 2r)/2 = (165.0 - 6.0 - 17.8)/2 = 70.6 mm
                      c/tf = 70.6 / 10.2 = 6.92
                      limit class 1 = 9 epsilon = 8.32  ->  6.92 <= 8.32: class 1

    Web in bending:   c = h - 2 tf - 2r = 303.4 - 20.4 - 17.8 = 265.2 mm
                      c/tw = 265.2 / 6.0 = 44.2
                      limit class 1 = 72 epsilon = 66.6  ->  44.2 <= 66.6: class 1

    Section class = worst of (1, 1) = **class 1**  ->  plastic modulus Wpl,y governs.

**Bending resistance (cl. 6.2.5):**

    Mc,Rd = Wpl,y * fy / gamma_M0
          = 623e3 mm^3 * 275 N/mm^2 / 1.0
          = 171.3e6 Nmm
          = **171.3 kNm**

This matches the order of the published SCI Blue Book resistance value
for this section in S275 (approximately 171 kNm).

Test assertion: `Mc,Rd = 171.3 +/- 0.5 kNm` (`tests/test_ec3.py`).
Library output: 171.325 kNm.

## 2. Concrete beam flexure: rectangular, singly reinforced

**Check:** required tension steel to EN 1992-1-1 (UK NA,
alpha_cc = 0.85, gamma_c = 1.5, gamma_s = 1.15).

Given: b = 300 mm, d = 450 mm, fck = 30 MPa, fyk = 500 MPa,
MEd = 200 kNm.

**Design strengths:**

    fcd = 0.85 * 30 / 1.5  = 17.00 MPa
    fyd = 500 / 1.15       = 434.78 MPa

**Normalised moment:**

    K = MEd / (b d^2 fck)
      = 200e6 / (300 * 450^2 * 30)
      = 200e6 / 1.8225e9
      = 0.10974

    K = 0.10974 <= K' = 0.167  ->  singly reinforced design is valid.

**Lever arm:**

    1 - 3.53 K = 1 - 3.53 * 0.109739 = 0.612620
    sqrt(0.612620) = 0.782700

    z = (d/2) * (1 + 0.782700) = 225 * 1.782700 = 401.11 mm
    cap: 0.95 d = 427.5 mm  ->  no cap, z = 401.11 mm

**Required steel:**

    As,req = MEd / (fyd * z)
           = 200e6 / (434.78 * 401.11)
           = 200e6 / 174,395
           = **1146.8 mm^2**

**Consistency checks:**

    Neutral axis: x = (d - z)/0.4 = (450 - 401.11)/0.4 = 122.2 mm
    x/d = 0.272 <= 0.45  ->  ductile, steel yields as assumed.

    Capacity round trip with As = 1146.8 mm^2:
    x = As fyd / (eta fcd b lambda) = 498,617 / (17 * 300 * 0.8) = 122.2 mm
    MRd = As fyd (d - 0.4 x) = 498,617 * 401.12 = 200.0 kNm = MEd  (consistent)

    Practical sanity: 4 H20 bars = 1257 mm^2 > 1146.8 mm^2 would satisfy.

Test assertion: `As,req within 0.5% of 1146.8 mm^2` (`tests/test_ec2.py`).
Library output: 1146.82 mm^2.

## 3. Steel column flexural buckling: 203x203x46 UC, S275, Lcr = 4.0 m, z-z

**Check:** flexural buckling resistance to EN 1993-1-1 cl. 6.3.1
(UK NA, gamma_M1 = 1.0, E = 210000 MPa).

Section properties (SCI Blue Book): A = 58.7 cm^2 = 5870 mm^2,
h = 203.2 mm, b = 203.6 mm, tf = 11.0 mm, Iz = 1548 cm^4 = 1.548e7 mm^4.

**Buckling curve (Table 6.2):**

    h/b = 203.2 / 203.6 = 0.998 <= 1.2, tf = 11.0 mm <= 100 mm
    ->  rolled I, minor (z-z) axis: **curve c, alpha = 0.49**
        (major axis would be curve b; for h/b > 1.2, tf <= 40 the
        curves would be a (y-y) and b (z-z))

**Elastic critical force:**

    Ncr = pi^2 E Iz / Lcr^2
        = 9.8696 * 210000 * 1.548e7 / 4000^2
        = 3.20866e13 / 1.6e7
        = 2,005,257 N = **2005.3 kN**

**Non-dimensional slenderness:**

    A fy = 5870 * 275 = 1,614,250 N

    lambda_bar = sqrt(A fy / Ncr)
               = sqrt(1,614,250 / 2,005,257)
               = sqrt(0.80501)
               = 0.8972

**Reduction factor:**

    Phi = 0.5 * (1 + alpha (lambda_bar - 0.2) + lambda_bar^2)
        = 0.5 * (1 + 0.49 * 0.6972 + 0.80501)
        = 0.5 * (1 + 0.34164 + 0.80501)
        = 1.0733

    chi = 1 / (Phi + sqrt(Phi^2 - lambda_bar^2))
        = 1 / (1.0733 + sqrt(1.15203 - 0.80501))
        = 1 / (1.0733 + 0.58908)
        = 1 / 1.66241
        = 0.6015   (<= 1.0, as required)

**Buckling resistance:**

    Nb,Rd = chi * A * fy / gamma_M1
          = 0.6015 * 5870 * 275 / 1.0
          = 971,031 N
          = **971.0 kN**

This is consistent with published member resistance tables for this
section and effective length.

Test assertion: `Nb,Rd within 0.5% of 971.0 kN` (`tests/test_ec3.py`).
Library output: 971.03 kN.

## 4. Physics and sanity assertions in the test suite

Beyond the three numeric anchors, the tests assert behaviour that must
hold for any input:

* `chi <= 1.0` for every section, grade, axis and length swept
  (`test_chi_never_exceeds_one`).
* Class 1/2 bending uses `Wpl,y`; the 305x165x40 UB in S275 classifies
  as class 1 in flange, web and overall (`test_classification_305ub`).
* `VRd,c` never falls below the `v_min` floor: with `Asl = 0` the result
  equals `v_min * b * d` exactly (`test_vrdc_floors_at_vmin`).
* `K > K'` returns a "compression reinforcement required" result rather
  than a silent number (`test_over_reinforced_reported`).
* `cot(theta)` outside [1.0, 2.5] and `fck > 50` raise `ValueError`.
* Buckling curve selection follows Table 6.2 for both the `h/b > 1.2`
  (305x165x40 UB: a/b) and `h/b <= 1.2` (203x203x46 UC: b/c) branches.
