"""Round 7, 2026-11-27: a stranger's machine. The same result file, saved the ways Windows saves files, must still be
read; and anything that is not a result file must be turned away in plain words, never with a crash dump.
Run: python tests/test_holes_7.py"""
import shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_holes import TMP  # noqa: E402

ROOT = HERE.parent
S = ROOT / "samples"
CLI = [sys.executable, str(ROOT / "second_look.py")]
FILES = (("promptfoo_twelve_checks.json", b"promptfoo"), ("garak_has_any.report.jsonl", b"garak"),
         ("inspect_blank_answers.json", b"Inspect"))


def run(path, *more):
    p = subprocess.run(CLI + [str(path)] + list(more), capture_output=True)
    return p.returncode, p.stdout, p.stderr


def reads(path, tool):
    rc, out, err = run(path)
    assert rc == 0 and b"INSPECTION CARD" in out and tool in out and b"Traceback" not in err, (rc, out[:120], err[-200:])


def turned_away(path):
    rc, out, err = run(path)
    text = (out + err).decode("utf-8", "replace")
    assert rc != 0 and "Traceback" not in text and "Nothing was inspected" in text, text[-300:]


def hole_49_windows_line_endings():
    for name, tool in FILES:
        p = TMP / ("crlf_" + name)
        p.write_bytes((S / name).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        reads(p, tool)


def hole_50_a_byte_order_mark_in_front():
    """Many Windows editors and tools put three marker bytes at the start of a file. It is still the same file."""
    for name, tool in FILES:
        p = TMP / ("bom_" + name)
        p.write_bytes(b"\xef\xbb\xbf" + (S / name).read_bytes())
        reads(p, tool)


def hole_51_saved_as_utf16():
    """PowerShell's ">" writes UTF-16. A result file redirected that way must still be read."""
    for name, tool in FILES:
        p = TMP / ("utf16_" + name)
        p.write_bytes((S / name).read_text(encoding="utf-8").encode("utf-16"))
        reads(p, tool)


def hole_52_the_version_survives_a_byte_order_mark():
    """With a mark in front, the first line of a garak file used to be lost, and the version with it."""
    p = TMP / "bom_version.report.jsonl"
    p.write_bytes(b"\xef\xbb\xbf" + (S / "garak_has_any.report.jsonl").read_bytes())
    rc, out, err = run(p)
    assert b"garak 0.17.0" in out, out[:300]


def hole_53_an_awkward_file_name():
    p = TMP / "résultats 结果 (final).json"
    shutil.copyfile(S / "promptfoo_twelve_checks.json", p)
    reads(p, b"promptfoo")


def hole_54_not_a_result_file():
    (TMP / "empty.json").write_bytes(b"")
    (TMP / "garbage.bin").write_bytes(bytes(range(256)) * 50)
    (TMP / "list.json").write_text("[1, 2, 3]", encoding="utf-8")
    for p in (TMP / "empty.json", TMP / "garbage.bin", TMP / "list.json", TMP, TMP / "no_such_file.json", ROOT / "README.md"):
        turned_away(p)


def hole_55_help_and_no_arguments():
    p = subprocess.run(CLI + ["--help"], capture_output=True)
    assert p.returncode == 0 and b"promptfoo, garak or Inspect" in p.stdout
    p = subprocess.run(CLI, capture_output=True)
    assert p.returncode != 0 and b"Traceback" not in p.stderr


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
