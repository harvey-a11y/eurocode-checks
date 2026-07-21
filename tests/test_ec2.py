"""EC2 beam check tests, anchored to the hand calcs in VALIDATION.md."""

import math

import pytest

from eurocheck import ec2_beam


class TestFlexureDesign:
    def test_hand_calc_anchor(self):
        """VALIDATION.md section 2: b=300, d=450, fck=30, fyk=500, MEd=200.

        Hand calc:
            K  = 200e6 / (300 * 450^2 * 30) = 0.10974  <= 0.167
            z  = 225 * (1 + sqrt(1 - 3.53*0.10974)) = 401.11 mm (< 0.95d)
            As = 200e6 / (434.78 * 401.11) = 1146.8 mm^2
        """
        res = ec2_beam.design_flexure(b=300, d=450, fck=30, fyk=500, m_ed=200)

        # Reproduce the hand arithmetic explicitly with the contract formulas.
        K_hand = 200e6 / (300 * 450**2 * 30)
        z_hand = (450 / 2) * (1 + math.sqrt(1 - 3.53 * K_hand))
        as_hand = 200e6 / ((500 / 1.15) * z_hand)

        assert res.singly_reinforced
        assert res.K == pytest.approx(K_hand, rel=1e-12)
        assert res.z == pytest.approx(z_hand, rel=1e-12)
        assert res.as_req == pytest.approx(as_hand, rel=1e-12)
        # And against the independently derived hand value:
        assert res.as_req == pytest.approx(1146.8, rel=0.005)

    def test_lever_arm_capped_at_095d(self):
        """A tiny moment must not produce z > 0.95 d."""
        res = ec2_beam.design_flexure(b=300, d=450, fck=30, fyk=500, m_ed=5)
        assert res.z == pytest.approx(0.95 * 450)

    def test_over_reinforced_reported(self):
        """K > K' must report compression reinforcement, not a number."""
        res = ec2_beam.design_flexure(b=300, d=450, fck=30, fyk=500, m_ed=500)
        assert res.K > ec2_beam.K_LIM
        assert not res.singly_reinforced
        assert res.as_req is None
        assert res.z is None
        assert "compression reinforcement required" in res.note

    def test_fck_over_50_rejected(self):
        with pytest.raises(ValueError, match="fck"):
            ec2_beam.design_flexure(b=300, d=450, fck=60, fyk=500, m_ed=200)

    def test_negative_input_rejected(self):
        with pytest.raises(ValueError):
            ec2_beam.design_flexure(b=-300, d=450, fck=30, fyk=500, m_ed=200)


class TestMomentCapacity:
    def test_roundtrip_with_design(self):
        """Capacity of the designed steel area reproduces MEd (both sides
        use the same rectangular stress block)."""
        des = ec2_beam.design_flexure(b=300, d=450, fck=30, fyk=500, m_ed=200)
        cap = ec2_beam.moment_capacity(b=300, d=450, fck=30, fyk=500,
                                       as_prov=des.as_req)
        assert cap.m_rd == pytest.approx(200.0, rel=0.01)
        assert cap.ductile
        assert cap.x_over_d <= 0.45

    def test_stress_block_formula(self):
        """x and MRd follow the contract formulas exactly."""
        cap = ec2_beam.moment_capacity(b=300, d=450, fck=30, fyk=500,
                                       as_prov=1500.0)
        fyd = 500 / 1.15
        fcd = 0.85 * 30 / 1.5
        x_hand = 1500.0 * fyd / (1.0 * fcd * 300 * 0.8)
        m_hand = 1500.0 * fyd * (450 - 0.8 * x_hand / 2) / 1e6
        assert cap.x == pytest.approx(x_hand, rel=1e-12)
        assert cap.m_rd == pytest.approx(m_hand, rel=1e-12)

    def test_over_reinforced_flagged(self):
        """A huge steel area pushes x/d beyond 0.45 and must be flagged."""
        cap = ec2_beam.moment_capacity(b=300, d=450, fck=30, fyk=500,
                                       as_prov=4000.0)
        assert cap.x_over_d > 0.45
        assert not cap.ductile


class TestShearConcrete:
    def test_floors_at_vmin(self):
        """With Asl = 0 the strength term vanishes: VRd,c = v_min * b * d."""
        res = ec2_beam.shear_concrete(b=300, d=450, fck=30, asl=0.0)
        k = min(2.0, 1 + math.sqrt(200 / 450))
        v_min = 0.035 * k**1.5 * math.sqrt(30)
        assert res.vmin_governs
        assert res.v_rd_c == pytest.approx(v_min * 300 * 450 / 1e3, rel=1e-12)

    def test_strength_term(self):
        """Typical beam: 3 H25 (1470 mm^2), formula reproduced by hand."""
        res = ec2_beam.shear_concrete(b=300, d=450, fck=30, asl=1470.0)
        k = min(2.0, 1 + math.sqrt(200 / 450))
        rho = min(0.02, 1470.0 / (300 * 450))
        v = max((0.18 / 1.5) * k * (100 * rho * 30) ** (1 / 3),
                0.035 * k**1.5 * math.sqrt(30))
        assert not res.vmin_governs
        assert res.v_rd_c == pytest.approx(v * 300 * 450 / 1e3, rel=1e-12)

    def test_k_capped_at_2(self):
        res = ec2_beam.shear_concrete(b=300, d=150, fck=30, asl=500.0)
        assert res.k == pytest.approx(2.0)

    def test_rho_capped_at_002(self):
        res = ec2_beam.shear_concrete(b=300, d=450, fck=30, asl=10000.0)
        assert res.rho_l == pytest.approx(0.02)


class TestShearLinks:
    def test_links_and_crushing(self):
        """H10 two-leg links (157 mm^2) at 200 mm, cot theta = 2.5."""
        res = ec2_beam.shear_links(b=300, d=450, fck=30, fywk=500,
                                   asw=157, s=200, cot_theta=2.5)
        z = 0.9 * 450
        fywd = 500 / 1.15
        nu1 = 0.6 * (1 - 30 / 250)
        fcd = 0.85 * 30 / 1.5
        vrds = (157 / 200) * z * fywd * 2.5 / 1e3
        vrdmax = 300 * z * nu1 * fcd * 2.5 / (1 + 2.5**2) / 1e3
        assert res.v_rd_s == pytest.approx(vrds, rel=1e-12)
        assert res.v_rd_max == pytest.approx(vrdmax, rel=1e-12)
        assert res.v_rd == pytest.approx(min(vrds, vrdmax), rel=1e-12)

    @pytest.mark.parametrize("cot", [0.5, 0.99, 2.51, 5.0])
    def test_cot_theta_out_of_range_rejected(self, cot):
        with pytest.raises(ValueError, match="cot"):
            ec2_beam.shear_links(b=300, d=450, fck=30, fywk=500,
                                 asw=157, s=200, cot_theta=cot)

    @pytest.mark.parametrize("cot", [1.0, 2.5])
    def test_cot_theta_bounds_accepted(self, cot):
        res = ec2_beam.shear_links(b=300, d=450, fck=30, fywk=500,
                                   asw=157, s=200, cot_theta=cot)
        assert res.v_rd > 0
