#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JAR = os.environ.get("RARS_JAR", str(ROOT / "rars.jar"))
DEFAULT_TARGETS = ["multiplication.s", "gemm.s", "sobel.s"]
DEFAULT_REGISTERS = ["a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7"]

RESET, RED, GRN, YEL, DIM, CYN = (
    "\033[0m",
    "\033[31m",
    "\033[32m",
    "\033[33m",
    "\033[2m",
    "\033[36m",
)
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    RESET = RED = GRN = YEL = DIM = CYN = ""

STATUS_STYLE = {
    "clean_exit": (GRN, "OK"),
    "assemble_error": (RED, "ASM ERROR"),
    "runtime_error": (RED, "RUNTIME ERROR"),
    "step_limit": (YEL, "STEP LIMIT"),
    "fell_off_end": (YEL, "NO ECALL EXIT"),
    "timeout": (RED, "TIMEOUT"),
    "unknown": (YEL, "UNKNOWN"),
}


def parse_output(stdout, stderr, returncode):
    if "Processing terminated due to errors" in stderr:
        status = "assemble_error"
    elif "Simulation terminated due to errors" in stderr:
        status = "runtime_error"
    elif "maximum step limit" in stderr:
        status = "step_limit"
    elif "dropping off the bottom" in stderr:
        status = "fell_off_end"
    elif "terminated by calling exit" in stderr or returncode == 0:
        status = "clean_exit"
    else:
        status = "unknown"

    error_line = None
    m = re.search(r"^Error in .+$", stderr, re.MULTILINE)
    if m:
        error_line = m.group(0)

    instr_count = None
    m = re.search(r"^\d+$", stderr, re.MULTILINE)
    if m:
        instr_count = int(m.group(0))

    registers = {}
    for m in re.finditer(r"^(\S+)\t(0x[0-9a-fA-F]+)$", stderr, re.MULTILINE):
        registers[m.group(1)] = m.group(2)

    return {
        "status": status,
        "error_line": error_line,
        "instr_count": instr_count,
        "registers": registers,
        "stdout": stdout,
    }


def normalize_words(text):
    words = []
    for line in text.splitlines():
        line = line.strip()
        if re.fullmatch(r"[0-9a-fA-F]+", line):
            words.append(int(line, 16))
    while words and words[-1] == 0:
        words.pop()
    return words


def run_one(jar, src, steps, registers, timeout, data_dump_path):
    args = [
        "java",
        "-jar",
        jar,
        "nc",
        "me",
        "ae1",
        "se1",
        "ic",
        "sm",
        str(steps),
        *registers,
        "dump",
        ".data",
        "HexText",
        str(data_dump_path),
        str(src),
    ]
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error_line": f"wall-clock timeout after {timeout}s",
            "instr_count": None,
            "registers": {},
            "stdout": "",
        }
    return parse_output(p.stdout, p.stderr, p.returncode)


def report_one(name, result, data_words, expect):
    color, label = STATUS_STYLE[result["status"]]
    print(f"{color}{label:<15}{RESET} {name}")

    if result["instr_count"] is not None:
        print(f"  instructions executed: {result['instr_count']}")

    if result["error_line"]:
        print(f"  {RED}{result['error_line']}{RESET}")

    if result["registers"]:
        regline = "  ".join(f"{r}={v}" for r, v in result["registers"].items())
        print(f"  registers: {regline}")

    if result["stdout"]:
        out = (
            result["stdout"]
            if len(result["stdout"]) <= 200
            else result["stdout"][:200] + "..."
        )
        print(f"  program output: {out!r}")

    if data_words:
        shown = ", ".join(f"0x{w:08x}" for w in data_words[:16])
        more = f" ... ({len(data_words)} words total)" if len(data_words) > 16 else ""
        print(f"  .data (post-run, trailing zeros trimmed): {shown}{more}")

    ok = result["status"] not in ("assemble_error", "runtime_error", "timeout")
    mismatches = []
    for key, want in expect.items():
        want_val = int(want, 0)
        if key in result["registers"]:
            got_val = int(result["registers"][key], 16)
        elif key.startswith("data[") and key.endswith("]"):
            idx = int(key[5:-1])
            got_val = data_words[idx] if idx < len(data_words) else None
        else:
            got_val = None
        if got_val != want_val:
            mismatches.append((key, want_val, got_val))
            ok = False

    for key, want_val, got_val in mismatches:
        got_str = "missing" if got_val is None else f"0x{got_val:08x}"
        print(
            f"  {RED}expect FAIL{RESET} {key}: wanted 0x{want_val:08x}, got {got_str}"
        )

    if result["status"] == "fell_off_end":
        print(
            f"  {YEL}warning: program did not terminate via ecall "
            f"(phase_1.pdf requires ecall termination){RESET}"
        )

    return ok


def write_summary(path, rows):
    lines = [
        "## Simulation results",
        "",
        "| | program | status | instructions | notes |",
        "|---|---|---|---|---|",
    ]
    icon = {
        "clean_exit": "✅",
        "assemble_error": "💥",
        "runtime_error": "💥",
        "step_limit": "⚠️",
        "fell_off_end": "⚠️",
        "timeout": "💥",
        "unknown": "⚠️",
    }
    for name, result, ok in rows:
        _, label = STATUS_STYLE[result["status"]]
        note = result["error_line"] or ""
        ic = result["instr_count"] if result["instr_count"] is not None else "-"
        lines.append(
            f"| {icon[result['status']]} | `{name}` | {label} | {ic} | {note} |"
        )
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=None)
    ap.add_argument("--rars", default=DEFAULT_JAR)
    ap.add_argument("--steps", type=int, default=2_000_000)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--registers", nargs="*", default=DEFAULT_REGISTERS)
    ap.add_argument(
        "--expect",
        action="append",
        default=[],
        help="e.g. --expect a0=42 --expect data[2]=0x2a",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="treat step-limit and no-ecall-exit as failures too",
    )
    ap.add_argument("--summary-md")
    args = ap.parse_args()

    if not Path(args.rars).exists():
        sys.exit(f"rars.jar not found at {args.rars}")

    if args.paths:
        srcs = [Path(p) for p in args.paths]
    else:
        srcs = [ROOT / n for n in DEFAULT_TARGETS if (ROOT / n).exists()]
    if not srcs:
        sys.exit(
            "no target .s files found (expected multiplication.s, gemm.s, sobel.s "
            "in repo root, or pass paths explicitly)"
        )

    per_file_expect = {}
    for item in args.expect:
        k, v = item.split("=", 1)
        per_file_expect[k] = v

    rows = []
    any_hard_fail = False
    for src in srcs:
        if not src.exists():
            print(f"{RED}MISSING{RESET}        {src}")
            any_hard_fail = True
            continue
        data_dump = Path(f"/tmp/simulate_{src.stem}_data.hex")
        result = run_one(
            args.rars, src, args.steps, args.registers, args.timeout, data_dump
        )
        data_words = (
            normalize_words(data_dump.read_text()) if data_dump.exists() else []
        )
        ok = report_one(src.name, result, data_words, per_file_expect)
        if args.strict and result["status"] in ("step_limit", "fell_off_end"):
            ok = False
        if not ok:
            any_hard_fail = True
        rows.append((src.name, result, ok))
        print()
        data_dump.unlink(missing_ok=True)

    if args.summary_md:
        write_summary(args.summary_md, rows)

    n_ok = sum(1 for _, _, ok in rows if ok)
    print(f"{n_ok}/{len(rows)} ran cleanly")
    return 1 if any_hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
