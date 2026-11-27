"""Round 5, 2026-11-27: the Inspect reader, attacked the way the other two were.
Run: python tests/test_holes_5.py"""
import json, subprocess, sys, tracemalloc
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import second_look as s  # noqa: E402
from test_holes import TMP, sev_of  # noqa: E402

CLI = [sys.executable, str(HERE.parent / "second_look.py")]
TARGET, GRADER = "openai-api/moonshot/kimi-k2.6", "openai/gpt-4o"


def call(model, text="An answer.", stop="stop", error=None):
    e = {"event": "model", "model": model, "output": {"completion": text, "choices": [{"stop_reason": stop}]}}
    if error:
        e["error"] = error
    return e


def sample(i, events, grade="honest", error=None):
    d = {"id": i, "epoch": 1, "events": events, "output": {"completion": ""}, "scores": {"sc": {"value": grade}}}
    if error:
        d["error"] = {"message": error}
    return d


def log(samples, status="success", planned=None, target=TARGET, ver="0.3.273", name=None, raw_tail=None):
    d = {"version": 2, "status": status,
         "eval": {"task": "inspect_evals/mask", "model": target, "created": "2026-11-27T00:00:00+00:00",
                  "dataset": {"samples": planned if planned is not None else len(samples)}, "packages": {"inspect_ai": ver}},
         "plan": {"config": {"max_tokens": 1000}}, "samples": samples}
    p = TMP / (name or f"insp_{len(list(TMP.iterdir()))}.json")
    text = json.dumps(d)
    if raw_tail is not None:
        text = text[:raw_tail]
    p.write_text(text, encoding="utf-8")
    return p


def level(r, title):
    return {t: lv for lv, t, _ in r["findings"]}.get(title)


def good(i):
    return sample(i, [call(TARGET), call(GRADER, "honest")])


def hole_30_a_clean_inspect_run_reads_clean():
    r = s.inspect_inspect(str(log([good(i) for i in range(50)])))
    assert sev_of(r)["high"] == 0 and sev_of(r)["medium"] == 0, [x[:2] for x in r["findings"]]
    assert level(r, "A different vendor graded") == "ok"


def hole_31_blank_answers_graded():
    blank = [sample(i, [call(TARGET, "", stop="max_tokens"), call(GRADER, "evade")], grade="evade") for i in range(20)]
    r = s.inspect_inspect(str(log(blank + [good(i) for i in range(20, 50)])))
    assert level(r, "Empty replies were graded as answers") == "bad"
    assert level(r, "Replies were cut short") == "bad"
    assert ("Had a blank answer", "20", "20 of them were graded anyway") in r["numbers"]


def hole_32_a_run_that_stopped():
    r = s.inspect_inspect(str(log([good(i) for i in range(30)], status="started", planned=100)))
    assert level(r, "The run stopped early") == "bad"


def hole_33_a_file_cut_off_mid_record():
    """The file ends halfway through a question. Report what was read and say the file is cut off; never crash."""
    full = log([good(i) for i in range(40)], name="whole.json")
    size = len(full.read_text(encoding="utf-8"))
    p = log([good(i) for i in range(40)], name="cut.json", raw_tail=int(size * 0.6))
    r = s.inspect_inspect(str(p))
    assert r is not None and level(r, "The run did not close") == "bad", "a file cut off mid-record was not reported as cut off"
    out = subprocess.run(CLI + [str(p)], capture_output=True)
    assert out.returncode == 0 and b"Traceback" not in out.stderr


def hole_34_the_ai_graded_itself():
    """The same model answers and grades. There is no separate grader to compare, and the card must not call it GOOD."""
    r = s.inspect_inspect(str(log([sample(i, [call("openai/gpt-4o"), call("openai/gpt-4o", "honest")]) for i in range(20)], target="openai/gpt-4o")))
    assert level(r, "A different vendor graded") is None, "called a self-graded run independently graded"
    assert level(r, "The file does not say who graded") == "warn"


def hole_35_same_company_different_model():
    r = s.inspect_inspect(str(log([sample(i, [call("openai/gpt-4o"), call("openai/gpt-4o-mini", "honest")]) for i in range(20)], target="openai/gpt-4o")))
    assert level(r, "The same vendor graded its own model") == "warn"


def hole_36_no_event_trail():
    """A log saved without its record of calls. Use the final answer, and say what could not be seen."""
    ss = [{"id": i, "output": {"completion": "" if i < 10 else "An answer."}, "scores": {"sc": {"value": "C"}}} for i in range(40)]
    r = s.inspect_inspect(str(log(ss)))
    assert level(r, "Empty replies were graded as answers") == "bad", "missed blank final answers in a log with no event trail"
    assert level(r, "Untested version") == "warn"


def hole_37_nothing_in_it():
    r = s.inspect_inspect(str(log([])))
    assert level(r, "No answers were recorded") == "bad"


def hole_38_broken_shapes_do_not_crash():
    bad = [None, 5, "x", {"events": "nope", "scores": 7, "output": []}, {"events": [None, 3, {"event": "model", "model": 9, "output": "s"}],
           "scores": {"a": None, "b": {"value": {"x": None}}}}, {"events": [{"event": "model", "model": TARGET, "output": {"choices": [None]}}]}]
    try:
        r = s.inspect_inspect(str(log(bad)))
        s.as_text(r), s.as_html(r), s.as_data(r)
    except Exception as e:  # noqa: BLE001
        raise AssertionError(f"crashed on odd shapes: {type(e).__name__}: {e}")


def hole_39_cli_picks_the_right_reader_and_stays_small():
    """The command line must send an Inspect file to the Inspect reader without first loading it whole."""
    p = log([sample(i, [call(TARGET, "x" * 4000), call(GRADER, "honest")]) for i in range(8000)], name="big_inspect.json")
    size = p.stat().st_size
    assert s.sniff(str(p)) == "inspect"
    tracemalloc.start()
    r = s.inspect_inspect(str(p))
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    out = subprocess.run(CLI + [str(p)], capture_output=True)
    p.unlink()
    assert b"Inspect" in out.stdout and out.returncode == 0
    assert r["score"].startswith("8,000") and peak < size / 3, f"peak {peak / 1e6:.0f} MB on a {size / 1e6:.0f} MB file"


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
