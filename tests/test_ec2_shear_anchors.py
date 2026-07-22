"""Hand-calculation anchors for the EC2 shear checks (see VALIDATION.md)."""
from eurocheck.ec2_beam import shear_concrete, shear_links


def test_vrdc_hand_anchor():
    # b=300, d=450, fck=30, Asl=1147 mm^2:
    # k = 1 + sqrt(200/450) = 1.6667 ; rho_l = 1147/135000 = 0.008496
    # (100 rho_l fck)^(1/3) = 25.489^(1/3) = 2.943
    # VRd,c = 0.12 * 1.6667 * 2.943 * 300 * 450 / 1e3 = 79.5 kN
    # v_min = 0.035 * 1.6667^1.5 * sqrt(30) = 0.412 MPa (does not govern)
    r = shear_concrete(b=300, d=450, fck=30, asl=1147)
    assert abs(r.v_rd_c - 79.5) / 79.5 < 0.005
    assert not r.vmin_governs


def test_vrdmax_hand_anchor():
    # b=300, d=450 (z=405), fck=30, cot(theta)=2.5:
    # nu1 = 0.6*(1-30/250) = 0.528 ; fcd_shear = 30/1.5 = 20 (alpha_cc=1.0, PD 6687-1)
    # VRd,max = 300*405*0.528*20*2.5 / (1+2.5^2) / 1e3 = 442.4 kN
    r = shear_links(b=300, d=450, fck=30, fywk=500, asw=157, s=200, cot_theta=2.5)
    assert abs(r.v_rd_max - 442.4) / 442.4 < 0.005


def test_vrds_hand_anchor():
    # 2-leg H10 links (asw=157 mm^2) at s=200, fywk=500, cot(theta)=2.5:
    # VRd,s = (157/200) * 405 * 434.78 * 2.5 / 1e3 = 345.6 kN
    r = shear_links(b=300, d=450, fck=30, fywk=500, asw=157, s=200, cot_theta=2.5)
    assert abs(r.v_rd_s - 345.6) / 345.6 < 0.005
