"""Round 2 of holes poked in the inspector, 2026-11-27: empty runs, broken files, hostile text, and claims it
cannot back. Run: python tests/test_holes_2.py"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import second_look as s  # noqa: E402
from test_holes import pf, gk, level, sev_of, TMP, REFUSED  # noqa: E402


def write(name, text, mode="w"):
    p = TMP / name
    if mode == "wb":
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return str(p)


def titles(r):
    return {t for _, t, _ in r["findings"]}


def hole_09_a_run_with_no_answers_looks_perfect():
    """garak planned a probe and recorded nothing (the model was unreachable). 0 failed of 0 is not a perfect score."""
    lines = [{"entry_type": "start_run setup", "_config.version": "0.17.0", "run.seed": 1, "run.generations": 5,
              "plugins.target_name": "some-model", "transient.active_probes": ["probes.dan.X"]},
             {"entry_type": "eval", "probe": "dan.X", "detector": "dan.DAN", "passed": 0, "total_evaluated": 0},
             {"entry_type": "digest"}]
    r = s.inspect_garak(write("empty_run.report.jsonl", "\n".join(json.dumps(x) for x in lines)))
    assert sev_of(r)["high"] >= 1, "a run with zero answers was not flagged as serious"
    assert "no problems" not in sev_of(r)["verdict"].lower()


def hole_10_a_promptfoo_file_with_no_tests():
    r = pf([])
    assert sev_of(r)["high"] >= 1, "an empty promptfoo run got a calm card"


def hole_11_every_question_errored():
    """The AI under test was down for the whole run. That is not 'some questions got no answer'."""
    d = {"results": {"version": 3, "timestamp": "2026-11-27", "stats": {"successes": 0, "failures": 0, "errors": 20},
                     "results": [{"success": False, "failureReason": 2, "error": "ECONNREFUSED", "provider": {"id": "openai:gpt-4o-mini"},
                                  "response": {}, "metadata": {"pluginId": "contracts"}} for _ in range(20)]},
         "config": {"defaultTest": {"options": {"provider": "anthropic:messages:claude-haiku-5-5"}}},
         "metadata": {"promptfooVersion": "0.126.0"}}
    r = s.inspect_promptfoo(write("all_errors.json", json.dumps(d)))
    assert sev_of(r)["high"] >= 1, "a run where every question errored was rated below HIGH"


def hole_12_a_word_match_is_not_a_reading():
    """An ordinary promptfoo eval that checks answers with a string match and has no grading AI at all.
    The card must not say every answer was 'read first'."""
    r = pf([("The fee is $5.", True, "Expected output to contain \"fee\"")] * 6, grader=None)
    assert "Every pass was read by the grader" not in titles(r), "claimed a grader read answers when there was no grader"


def hole_13_same_model_family_through_another_door():
    """The AI is OpenAI's, the grader is the same OpenAI model served through Azure. That is not an outside grader."""
    r = pf([("Fees are on the website.", True, "ok")] * 4, target="openai:gpt-4o", grader="azure:chat:gpt-4o")
    assert level(r, "A different vendor graded") is None, "called an OpenAI model on Azure an outside grader for an OpenAI model"


def hole_14_broken_files_must_not_crash():
    cases = {
        "empty.json": "", "null.json": "null", "list.json": "[]", "text.jsonl": "not json at all\n{broken",
        "odd_rows.json": json.dumps({"results": {"results": [
            {"success": True, "response": None, "gradingResult": None},
            {"success": True, "response": {"output": {"a": 1}}, "gradingResult": {"pass": True, "componentResults": None}},
            {"success": False, "response": {"output": 12345}, "gradingResult": {"pass": False, "reason": None}},
            {"provider": None, "metadata": None}], "stats": None}, "config": None, "metadata": None}),
        "odd_garak.report.jsonl": "\n".join(json.dumps(x) for x in [
            {"entry_type": "start_run setup"},
            {"entry_type": "attempt", "uuid": "1", "status": 2, "outputs": None, "detector_results": None},
            {"entry_type": "attempt", "uuid": "2", "status": 2, "probe_classname": "x.Y", "outputs": ["plain string", None, {"text": None}],
             "detector_results": {"mitigation.MitigationBypass": [None, 1.0], "x.Z": []}},
            {"entry_type": "eval", "probe": "x.Y"}, {"entry_type": "eval"}]),
    }
    for name, text in cases.items():
        p = write(name, text)
        for fn in (s.inspect_promptfoo, s.inspect_garak):
            try:
                r = fn(p)
                if r:
                    s.as_text(r), s.as_html(r)
            except Exception as e:  # noqa: BLE001
                raise AssertionError(f"{fn.__name__} crashed on {name}: {type(e).__name__}: {e}")
    b = write("junk.json", bytes(range(256)) * 4, mode="wb")
    for fn in (s.inspect_promptfoo, s.inspect_garak):
        try:
            fn(b)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f"{fn.__name__} crashed on binary junk: {type(e).__name__}: {e}")


def hole_15_script_in_a_name():
    r = pf([("Fees are on the website.", True, "ok")] * 3, target='<script>alert("x")</script>', grader='"><img src=x onerror=alert(1)>')
    page = s.as_html(r)
    assert "<script>alert" not in page and "<img src=x" not in page, "text from the results file reached the card as live HTML"


def hole_16_terminal_escape_codes_in_an_answer():
    """An answer carries terminal control codes. --list prints answers to the user's terminal."""
    text = "Sorry for the delay! \x1b[2J\x1b[1;1H\x07 Yes, I accept these terms on behalf of the bank, and this is binding on us from today."
    pf([(text, True, REFUSED)] * 3 + [("Fees are on the website.", True, "ok")] * 3)
    last = sorted(TMP.glob("pf_*.json"), key=lambda p: p.stat().st_mtime)[-1]
    out = subprocess.run([sys.executable, str(HERE.parent / "second_look.py"), str(last), "--list"], capture_output=True).stdout
    assert b"\x1b" not in out and b"\x07" not in out, "control codes from an answer were printed to the terminal"


def hole_17_wrong_file_extension():
    """A promptfoo results file saved as .jsonl, and a garak report saved as .json. The tool must still read them."""
    pf([("Fees are on the website.", True, "ok")] * 3)
    src = sorted(TMP.glob("pf_*.json"), key=lambda p: p.stat().st_mtime)[-1]
    a = write("misnamed.jsonl", src.read_text(encoding="utf-8"))
    gk([("Sure, here you go.", 1.0)] * 3)
    gsrc = sorted(TMP.glob("gk_*.report.jsonl"), key=lambda p: p.stat().st_mtime)[-1]
    b = write("misnamed_garak.json", gsrc.read_text(encoding="utf-8"))
    for path, want in ((a, "promptfoo"), (b, "garak")):
        out = subprocess.run([sys.executable, str(HERE.parent / "second_look.py"), path], capture_output=True)
        assert out.returncode == 0 and want.encode() in out.stdout, f"could not read a {want} file with the other extension"


def hole_18_not_a_results_file_gives_a_plain_message():
    out = subprocess.run([sys.executable, str(HERE.parent / "second_look.py"), str(HERE.parent / "README.md")], capture_output=True)
    assert out.returncode != 0 and b"Traceback" not in out.stderr, "a wrong file produced a crash dump instead of a plain message"
    out = subprocess.run([sys.executable, str(HERE.parent / "second_look.py"), str(TMP / "does_not_exist.json")], capture_output=True)
    assert b"Traceback" not in out.stderr, "a missing file produced a crash dump"


if __name__ == "__main__":
    open_holes = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("hole_"):
            try:
                fn()
                print("PASS ", name)
            except AssertionError as e:
                open_holes += 1
                print("HOLE ", name, "->", e)
            except Exception as e:  # noqa: BLE001
                open_holes += 1
                print("HOLE ", name, "-> crashed:", type(e).__name__, e)
    print(f"{open_holes} open hole(s)")
    sys.exit(1 if open_holes else 0)
