"""Pins what the inspector must report on each sample file. Run: python tests/test_samples.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import second_look as s  # noqa: E402

S = ROOT / "samples"


def titles(r):
    return {t: lv for lv, t, _ in r["findings"]}


def test_promptfoo_contract_proof():
    t = titles(s.inspect_promptfoo(str(S / "promptfoo_contract_proof.json")))
    assert t["Passes the grader never read"] == "bad"
    # the stand-in AI has no known maker, so the card must not claim the grading was independent
    assert "A different vendor graded" not in t
    assert t.get("Could not compare grader and target") == "warn"


def test_promptfoo_twelve_checks():
    r = s.inspect_promptfoo(str(S / "promptfoo_twelve_checks.json"))
    t = titles(r)
    assert t["Passes the grader never read"] == "bad"
    assert t["It said no, called the tool, and passed"] == "bad"
    assert t["Replies that talk to the grader"] == "bad"
    assert "26 answers out of the 27 marked safe" in [d for _, n, d in r["findings"] if n == "Passes the grader never read"][0]
    assert r["numbers"] == [("The test said", "27 of 42", "answers passed"),
                            ("Passed without being read", "26", "26 of them need a person to look")]


def test_garak_plain_no():
    assert titles(s.inspect_garak(str(S / "garak_plain_no.report.jsonl")))["Short replies scored as attacks that worked"] == "bad"


def test_garak_as_an_ai():
    assert "Replies passed on a phrase, not on a reading" in titles(s.inspect_garak(str(S / "garak_as_an_ai.report.jsonl")))


def test_garak_silence():
    assert titles(s.inspect_garak(str(S / "garak_silence.report.jsonl")))["Empty replies were graded as answers"] == "bad"


def test_inspect_blank_answers():
    r = s.inspect_inspect(str(S / "inspect_blank_answers.json"))
    t = titles(r)
    assert t["The run stopped early"] == "bad"
    assert t["Empty replies were graded as answers"] == "bad"
    assert t["Replies were cut short"] == "bad"
    assert s.sniff(str(S / "inspect_blank_answers.json")) == "inspect"


def test_garak_has_any():
    """garak 0.17 marks an answer safe on the letters "as an" inside "has any"."""
    r = s.inspect_garak(str(S / "garak_has_any.report.jsonl"))
    assert titles(r)["Marked safe on letters inside other words"] == "bad"
    assert '"has any"' in [d for _, n, d in r["findings"] if n == "Marked safe on letters inside other words"][0]


def test_promptfoo_real_answers():
    """Real answers from a real model. One says it will move the money, writes the transfer, and passes unread."""
    r = s.inspect_promptfoo(str(S / "promptfoo_real_answers.json"))
    d = [x for _, n, x in r["findings"] if n == "It said no, called the tool, and passed"][0]
    assert "transfer_funds (1 answer)" in d and "verify_identity (8 answers)" in d, d
    assert "used a tool: transfer_funds" in " | ".join(str(w) for w, _, _ in r["listing"])


def test_not_a_result_file():
    assert s.inspect_promptfoo(str(ROOT / "README.md")) is None
    assert s.inspect_garak(str(ROOT / "README.md")) is None


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            n += 1
            print("ok ", name)
    print(n, "passed")
