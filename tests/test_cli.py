"""CLI smoke tests (the two README examples plus error paths)."""

from eurocheck.cli import main


def test_ec2_beam_example(capsys):
    rc = main(["ec2-beam", "--b", "300", "--d", "450",
               "--fck", "30", "--fyk", "500", "--med", "200"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "K = MEd/(b d^2 fck) = 0.1097" in out
    assert "As,req = 1147 mm^2" in out


def test_ec3_column_example(capsys):
    rc = main(["ec3-column", "--section", "203x203x46UC",
               "--fy", "275", "--lcr", "4.0", "--axis", "z"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "curve c" in out
    assert "Nb,Rd      = 971.0 kN" in out


def test_ec2_beam_over_reinforced(capsys):
    rc = main(["ec2-beam", "--b", "300", "--d", "450",
               "--fck", "30", "--fyk", "500", "--med", "500"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "compression reinforcement required" in out


def test_ec3_beam_and_shear_smoke(capsys):
    assert main(["ec3-beam", "--section", "305x165x40UB", "--fy", "275"]) == 0
    assert main(["ec2-shear", "--b", "300", "--d", "450", "--fck", "30",
                 "--asl", "1470", "--asw", "157", "--s", "200"]) == 0
    assert main(["sections"]) == 0


def test_unknown_section_is_error(capsys):
    rc = main(["ec3-column", "--section", "999x999x999UC",
               "--fy", "275", "--lcr", "4.0", "--axis", "z"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Unknown section" in err


def test_bad_fck_is_error(capsys):
    rc = main(["ec2-beam", "--b", "300", "--d", "450",
               "--fck", "60", "--fyk", "500", "--med", "200"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "fck" in err
