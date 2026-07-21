"""EC3 member check tests, anchored to the hand calcs in VALIDATION.md."""

import math

import pytest

from eurocheck import ec3_member
from eurocheck.sections import get_section, list_sections


class TestClassification:
    def test_305ub_s275_is_class_1(self):
        """VALIDATION.md section 1: flange c/t = 6.92 <= 9 eps = 8.32,
        web c/t = 44.2 <= 72 eps = 66.6 -> class 1 throughout."""
        res = ec3_member.classify(get_section("305x165x40 UB"), 275)
        assert res.flange_class == 1
        assert res.web_class == 1
        assert res.section_class == 1

    def test_ratios_match_hand_arithmetic(self):
        sec = get_section("305x165x40 UB")
        res = ec3_member.classify(sec, 275)
        assert res.eps == pytest.approx(math.sqrt(235 / 275), rel=1e-12)
        assert res.flange_ratio == pytest.approx(
            ((165.0 - 6.0 - 2 * 8.9) / 2) / 10.2, rel=1e-12)
        assert res.web_ratio == pytest.approx(
            (303.4 - 2 * 10.2 - 2 * 8.9) / 6.0, rel=1e-12)

    def test_all_database_sections_class_1_in_s275(self):
        """All three database sections are class 1 in S275."""
        for sec in list_sections():
            assert ec3_member.classify(sec, 275).section_class == 1

    def test_higher_grade_can_worsen_class(self):
        """Classification tightens with fy: the 203x203x46 UC flange has
        c/t = 8.0, which passes 9 eps = 8.32 in S275 (class 1) but fails
        9 eps = 7.32 in S355, dropping to class 2 (<= 10 eps = 8.14)."""
        sec = get_section("203x203x46 UC")
        assert ec3_member.classify(sec, 275).section_class == 1
        res = ec3_member.classify(sec, 355)
        assert res.flange_class == 2
        assert res.section_class == 2
        # A class 2 section still uses the plastic modulus for bending.
        assert ec3_member.moment_resistance(sec, 355).modulus == "Wpl,y"


class TestMomentResistance:
    def test_mcrd_anchor_305ub_s275(self):
        """VALIDATION.md section 1: Mc,Rd = 623e3 * 275 / 1.0 = 171.3 kNm."""
        res = ec3_member.moment_resistance(get_section("305x165x40 UB"), 275)
        assert abs(res.mc_rd - 171.3) <= 0.5

    def test_class_1_uses_plastic_modulus(self):
        sec = get_section("305x165x40 UB")
        res = ec3_member.moment_resistance(sec, 275)
        assert res.section_class == 1
        assert res.modulus == "Wpl,y"
        assert res.mc_rd == pytest.approx(sec.Wpl_y * 275 / 1e6, rel=1e-12)


class TestShearResistance:
    def test_shear_area_formula(self):
        """Av = A - 2 b tf + (tw + 2r) tf for the 457x191x67 UB."""
        sec = get_section("457x191x67 UB")
        res = ec3_member.shear_resistance(sec, 275)
        av_hand = 8550.0 - 2 * 189.9 * 12.7 + (8.5 + 2 * 10.2) * 12.7
        assert res.av == pytest.approx(av_hand, rel=1e-12)
        assert res.vpl_rd == pytest.approx(av_hand * 275 / math.sqrt(3) / 1e3,
                                           rel=1e-12)


class TestBucklingCurves:
    def test_slender_ub_h_over_b_above_1p2(self):
        """305x165x40 UB: h/b = 1.84 > 1.2, tf = 10.2 <= 40
        -> curve a (y-y), b (z-z)."""
        sec = get_section("305x165x40 UB")
        assert ec3_member.buckling_curve(sec, "y") == ("a", 0.21)
        assert ec3_member.buckling_curve(sec, "z") == ("b", 0.34)

    def test_stocky_uc_h_over_b_below_1p2(self):
        """203x203x46 UC: h/b = 0.998 <= 1.2 -> curve b (y-y), c (z-z)."""
        sec = get_section("203x203x46 UC")
        assert ec3_member.buckling_curve(sec, "y") == ("b", 0.34)
        assert ec3_member.buckling_curve(sec, "z") == ("c", 0.49)

    def test_bad_axis_rejected(self):
        with pytest.raises(ValueError, match="axis"):
            ec3_member.buckling_curve(get_section("203x203x46 UC"), "x")


class TestFlexuralBuckling:
    def test_column_anchor_203uc_s275_4m_z(self):
        """VALIDATION.md section 3, all values derived by hand:

            Ncr        = pi^2 * 210000 * 1.548e7 / 4000^2 = 2005.3 kN
            lambda_bar = sqrt(5870*275 / 2005257)          = 0.8972
            curve c (h/b <= 1.2), alpha = 0.49
            Phi        = 0.5(1 + 0.49*0.6972 + 0.80501)    = 1.0733
            chi        = 1/(1.0733 + 0.58908)              = 0.6015
            Nb,Rd      = 0.6015 * 5870 * 275               = 971.0 kN
        """
        sec = get_section("203x203x46 UC")
        res = ec3_member.flexural_buckling(sec, 275, 4000.0, "z")
        assert res.curve == "c"
        assert res.alpha == pytest.approx(0.49)
        assert res.ncr == pytest.approx(2005.3, rel=0.005)
        assert res.lambda_bar == pytest.approx(0.8972, rel=0.005)
        assert res.phi == pytest.approx(1.0733, rel=0.005)
        assert res.chi == pytest.approx(0.6015, rel=0.005)
        assert res.nb_rd == pytest.approx(971.0, rel=0.005)

    def test_chi_never_exceeds_one(self):
        """Physics: the buckling reduction factor cannot amplify."""
        for sec in list_sections():
            for fy in (275, 355):
                for lcr in (500, 1000, 2000, 4000, 8000, 15000):
                    for axis in ("y", "z"):
                        res = ec3_member.flexural_buckling(sec, fy, lcr, axis)
                        assert res.chi <= 1.0
                        assert res.nb_rd <= sec.A * fy / 1e3

    def test_shorter_column_is_stronger(self):
        sec = get_section("203x203x46 UC")
        strong = ec3_member.flexural_buckling(sec, 275, 2000.0, "z")
        weak = ec3_member.flexural_buckling(sec, 275, 6000.0, "z")
        assert strong.nb_rd > weak.nb_rd

    def test_minor_axis_governs(self):
        """For equal Lcr the z-z (smaller I, worse curve) must govern."""
        sec = get_section("457x191x67 UB")
        yy = ec3_member.flexural_buckling(sec, 275, 4000.0, "y")
        zz = ec3_member.flexural_buckling(sec, 275, 4000.0, "z")
        assert zz.nb_rd < yy.nb_rd
