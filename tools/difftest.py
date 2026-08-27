#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JAR = os.environ.get("RARS_JAR", str(ROOT / "rars.jar"))
STUDENT_SH = ROOT / "tools" / "run_student.sh"

ARTIFACTS = {
    "text.hex": (".text", "HexText"),
    "text.bin": (".text", "BinaryText"),
    "data.hex": (".data", "HexText"),
    "data.bin": (".data", "BinaryText"),
}

SOL_PATTERNS = {
    "text.hex": "{base}_sol.hex.txt",
    "text.bin": "{base}_sol.bin.txt",
    "data.hex": "{base}_sol_data.hex.txt",
    "data.bin": "{base}_sol_data.bin.txt",
}

PROVIDED = {"addition"}

RESET, RED, GRN, YEL, DIM = "\033[0m", "\033[31m", "\033[32m", "\033[33m", "\033[2m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    RESET = RED = GRN = YEL = DIM = ""


def normalize(text, kind, ignore_trailing_zeros=True):
    words = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//", ";")):
            continue
        line = re.sub(r"^0x[0-9a-fA-F]+\s*:\s*", "", line)
        for tok in line.split():
            tok = tok.strip(",")
            if kind == "bin":
                t = tok[2:] if tok[:2].lower() == "0b" else tok
                if not re.fullmatch(r"[01]+", t):
                    continue
                words.append(int(t, 2) & 0xFFFFFFFF)
            else:
                t = tok[2:] if tok[:2].lower() == "0x" else tok
                if not re.fullmatch(r"[0-9a-fA-F]+", t):
                    continue
                words.append(int(t, 16) & 0xFFFFFFFF)
    if ignore_trailing_zeros:
        while words and words[-1] == 0:
            words.pop()
    return words


REG = [
    "zero",
    "ra",
    "sp",
    "gp",
    "tp",
    "t0",
    "t1",
    "t2",
    "s0",
    "s1",
    "a0",
    "a1",
    "a2",
    "a3",
    "a4",
    "a5",
    "a6",
    "a7",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "s8",
    "s9",
    "s10",
    "s11",
    "t3",
    "t4",
    "t5",
    "t6",
]

OPFMT = {
    0x33: "R",
    0x13: "I",
    0x03: "I",
    0x67: "I",
    0x73: "I",
    0x0F: "I",
    0x23: "S",
    0x63: "B",
    0x37: "U",
    0x17: "U",
    0x6F: "J",
}

MNEM = {
    (0x33, 0, 0x00): "add",
    (0x33, 0, 0x20): "sub",
    (0x33, 1, 0x00): "sll",
    (0x33, 2, 0x00): "slt",
    (0x33, 3, 0x00): "sltu",
    (0x33, 4, 0x00): "xor",
    (0x33, 5, 0x00): "srl",
    (0x33, 5, 0x20): "sra",
    (0x33, 6, 0x00): "or",
    (0x33, 7, 0x00): "and",
    (0x13, 0, None): "addi",
    (0x13, 2, None): "slti",
    (0x13, 3, None): "sltiu",
    (0x13, 4, None): "xori",
    (0x13, 6, None): "ori",
    (0x13, 7, None): "andi",
    (0x13, 1, 0x00): "slli",
    (0x13, 5, 0x00): "srli",
    (0x13, 5, 0x20): "srai",
    (0x03, 0, None): "lb",
    (0x03, 1, None): "lh",
    (0x03, 2, None): "lw",
    (0x03, 4, None): "lbu",
    (0x03, 5, None): "lhu",
    (0x23, 0, None): "sb",
    (0x23, 1, None): "sh",
    (0x23, 2, None): "sw",
    (0x63, 0, None): "beq",
    (0x63, 1, None): "bne",
    (0x63, 4, None): "blt",
    (0x63, 5, None): "bge",
    (0x63, 6, None): "bltu",
    (0x63, 7, None): "bgeu",
    (0x67, 0, None): "jalr",
    (0x6F, None, None): "jal",
    (0x37, None, None): "lui",
    (0x17, None, None): "auipc",
    (0x73, 0, None): "ecall/ebreak",
}


def sext(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def decode(w):
    op = w & 0x7F
    fmt = OPFMT.get(op)
    rd, f3 = (w >> 7) & 0x1F, (w >> 12) & 0x7
    rs1, rs2 = (w >> 15) & 0x1F, (w >> 20) & 0x1F
    f7 = (w >> 25) & 0x7F

    mn = (
        MNEM.get((op, f3, f7))
        or MNEM.get((op, f3, None))
        or MNEM.get((op, None, None))
        or "?"
    )

    f = [("opcode", f"0x{op:02x}")]
    if fmt == "R":
        f += [
            ("funct7", f"0x{f7:02x}"),
            ("rs2", f"x{rs2} ({REG[rs2]})"),
            ("rs1", f"x{rs1} ({REG[rs1]})"),
            ("funct3", f"0x{f3:x}"),
            ("rd", f"x{rd} ({REG[rd]})"),
        ]
    elif fmt == "I":
        imm = sext(w >> 20, 12)
        f += [
            ("imm[11:0]", f"{imm} (0x{(w >> 20) & 0xFFF:03x})"),
            ("rs1", f"x{rs1} ({REG[rs1]})"),
            ("funct3", f"0x{f3:x}"),
            ("rd", f"x{rd} ({REG[rd]})"),
        ]
        if op == 0x13 and f3 in (1, 5):
            f.insert(1, ("shamt", str(rs2)))
            f.insert(1, ("funct7", f"0x{f7:02x}"))
    elif fmt == "S":
        imm = sext(((w >> 25) << 5) | ((w >> 7) & 0x1F), 12)
        f += [
            ("imm", str(imm)),
            ("rs2", f"x{rs2} ({REG[rs2]})"),
            ("rs1", f"x{rs1} ({REG[rs1]})"),
            ("funct3", f"0x{f3:x}"),
        ]
    elif fmt == "B":
        imm = sext(
            (((w >> 31) & 1) << 12)
            | (((w >> 7) & 1) << 11)
            | (((w >> 25) & 0x3F) << 5)
            | (((w >> 8) & 0xF) << 1),
            13,
        )
        f += [
            ("imm (byte offset)", str(imm)),
            ("rs2", f"x{rs2} ({REG[rs2]})"),
            ("rs1", f"x{rs1} ({REG[rs1]})"),
            ("funct3", f"0x{f3:x}"),
        ]
    elif fmt == "U":
        f += [
            ("imm[31:12]", f"0x{(w >> 12) & 0xFFFFF:05x}"),
            ("rd", f"x{rd} ({REG[rd]})"),
        ]
    elif fmt == "J":
        imm = sext(
            (((w >> 31) & 1) << 20)
            | (((w >> 12) & 0xFF) << 12)
            | (((w >> 20) & 1) << 11)
            | (((w >> 21) & 0x3FF) << 1),
            21,
        )
        f += [("imm (byte offset)", str(imm)), ("rd", f"x{rd} ({REG[rd]})")]
    else:
        f += [("(not a recognized RV32I opcode)", "")]
    return mn, f


def explain(exp, got):
    xor = exp ^ got
    bits = f"{xor:032b}".replace("0", ".").replace("1", "^")
    mn_e, fe = decode(exp)
    mn_g, fg = decode(got)
    out = [
        f"      expected 0x{exp:08x}  {exp:032b}  [{mn_e}]",
        f"      actual   0x{got:08x}  {got:032b}  [{mn_g}]",
        f"      diffbits {' ' * 10}  {bits}",
    ]
    names = [n for n, _ in fe if not n.startswith("(")]
    gmap = dict(fg)
    for n in names:
        ve = dict(fe)[n]
        vg = gmap.get(n, "-")
        if ve != vg:
            out.append(f"      {RED}! {n:<18} expected {ve:<22} actual {vg}{RESET}")
    if mn_e != mn_g:
        out.append(f"      {RED}! decoded instruction differs: {mn_e} vs {mn_g}{RESET}")
    return out


def explode_words_to_bytes(words, endian):
    out = []
    for w in words:
        b = [(w >> s) & 0xFF for s in (0, 8, 16, 24)]
        out.extend(b if endian == "little" else list(reversed(b)))
    return out


def reglanularize(path, fmt, endian):
    if not path.exists():
        return
    words = normalize(
        path.read_text(errors="replace"), fmt, ignore_trailing_zeros=False
    )
    bytes_ = explode_words_to_bytes(words, endian)
    if fmt == "hex":
        path.write_text("\n".join(f"0x{b:02x}" for b in bytes_) + "\n")
    else:
        path.write_text("\n".join(f"{b:08b}" for b in bytes_) + "\n")


def run_rars(
    jar,
    src,
    outdir,
    mem_config=None,
    extra=(),
    data_granularity="byte",
    instr_granularity="word",
    endian="little",
):
    outdir.mkdir(parents=True, exist_ok=True)
    base = ["java", "-jar", jar, "nc", "me", "ae1", "a", *extra]
    if mem_config:
        base += ["mc", mem_config]

    warnings = []
    for seg in (".text", ".data"):
        args = list(base)
        for name, (s, fmt) in ARTIFACTS.items():
            if s == seg:
                args += ["dump", s, fmt, str(outdir / name)]
        args.append(str(src))
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return False, "RARS timed out"
        if seg == ".text" and p.returncode != 0:
            return False, (p.stderr or p.stdout).strip()
        for line in (p.stderr + p.stdout).splitlines():
            if "Warning" in line and line not in warnings:
                warnings.append(line.strip())

    if data_granularity == "byte":
        reglanularize(outdir / "data.hex", "hex", endian)
        reglanularize(outdir / "data.bin", "bin", endian)
    if instr_granularity == "byte":
        reglanularize(outdir / "text.hex", "hex", endian)
        reglanularize(outdir / "text.bin", "bin", endian)

    return True, "\n".join(warnings)


def run_student(src, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run(
            ["bash", str(STUDENT_SH), str(src), str(outdir)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, "your assembler timed out after 120s"
    if p.returncode != 0:
        return False, (p.stderr or p.stdout).strip()
    return True, ""


def read(path):
    try:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def file_options(src):
    opts = {
        "skip-data": False,
        "skip-bin": False,
        "mc": None,
        "data-granularity": None,
        "instr-granularity": None,
        "endian": None,
    }
    for line in src.read_text(errors="replace").splitlines()[:25]:
        m = re.match(r"\s*#\s*difftest:\s*(.+)", line)
        if not m:
            continue
        for tok in m.group(1).split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                if k in opts:
                    opts[k] = v
            elif tok in opts:
                opts[tok] = True
    return opts


def load(path, kind, ignore_trailing_zeros):
    if not path.exists():
        return None
    return normalize(path.read_text(errors="replace"), kind, ignore_trailing_zeros)


def word_diff(exp, got, seg, base, max_diffs):
    lines = []
    if len(exp) != len(got):
        lines.append(
            f"    {YEL}word count differs: reference {len(exp)}, "
            f"yours {len(got)}{RESET}"
        )
        if len(got) < len(exp):
            lines.append(
                "    (too few — a pseudo-instruction that should expand "
                "to 2 words probably emitted 1)"
            )
        else:
            lines.append(
                "    (too many — check pseudo-instruction expansion "
                "and .align/.space padding)"
            )
    shown = 0
    for i, (a, b) in enumerate(zip(exp, got)):
        if a == b:
            continue
        lines.append(f"    word {i} @ 0x{base + 4 * i:08x}:")
        if seg == "text":
            lines += explain(a, b)
        else:
            lines.append(f"      expected 0x{a:08x}   actual 0x{b:08x}")
        shown += 1
        if shown >= max_diffs:
            lines.append(
                f"    {DIM}... further differences suppressed "
                f"(--max-diffs to see them){RESET}"
            )
            break
    return lines


def compare(src, golden_dir, mine_dir, args, opts):
    lines = []
    ok = True
    stats = {"sol_files": 0, "sol_mismatch": 0}

    for art in ARTIFACTS:
        kind = "bin" if art.endswith(".bin") else "hex"
        seg = "data" if art.startswith("data") else "text"
        base = args.data_base if seg == "data" else args.text_base

        if seg == "data" and (args.skip_data or opts["skip-data"]):
            continue
        if kind == "bin" and (args.skip_bin or opts["skip-bin"]):
            continue

        keep_zeros = args.strict_padding
        rars = load(golden_dir / art, kind, not keep_zeros) or []
        mine = load(mine_dir / art, kind, not keep_zeros) or []

        sol_path = src.parent / SOL_PATTERNS[art].format(base=src.stem)
        sol = None
        if not args.no_sol:
            sol = load(sol_path, kind, not keep_zeros)

        if sol is not None:
            stats["sol_files"] += 1
            if sol != rars:
                stats["sol_mismatch"] += 1
                lines.append(
                    f"  {YEL}ORACLE{RESET} {art}: RARS disagrees with {sol_path.name}"
                )
                lines.append(
                    "    The golden output is not the same oracle as the "
                    "committed reference — likely a memory-config or "
                    "dump-format mismatch, not a bug in your assembler."
                )
                lines += word_diff(sol, rars, seg, base, args.max_diffs)

        reference, ref_name = (
            (sol, sol_path.name) if sol is not None else (rars, "RARS")
        )
        if mine == reference:
            continue
        ok = False
        lines.append(f"  {RED}FAIL{RESET} {art}  (vs {ref_name})")
        lines += word_diff(reference, mine, seg, base, args.max_diffs)

    return ("pass" if ok else "fail"), lines, stats


def discover(paths, filt):
    seen, out = set(), []
    for raw in paths:
        p = Path(raw)
        cands = sorted(p.glob("*.s")) if p.is_dir() else [p]
        for c in cands:
            r = c.resolve()
            if r in seen or filt not in c.name:
                continue
            seen.add(r)
            out.append(c)
    return out


def write_junit(path, results):
    import xml.etree.ElementTree as ET

    ts = ET.Element(
        "testsuite",
        name="assembler-vs-rars",
        tests=str(len(results)),
        failures=str(sum(1 for r in results if r["status"] == "fail")),
        errors=str(sum(1 for r in results if r["status"] == "error")),
    )
    for r in results:
        tc = ET.SubElement(ts, "testcase", classname="difftest", name=r["name"])
        if r["status"] == "fail":
            ET.SubElement(tc, "failure", message="output differs").text = r["detail"]
        elif r["status"] == "error":
            ET.SubElement(tc, "error", message="could not run").text = r["detail"]
    Path(path).write_text(ET.tostring(ts, encoding="unicode"))


def write_summary(path, results, custom_count, required):
    icon = {"pass": "✅", "fail": "❌", "error": "💥"}
    n_pass = sum(1 for r in results if r["status"] == "pass")
    rows = ["| | test | source | result |", "|---|---|---|---|"]
    for r in results:
        rows.append(
            f"| {icon[r['status']]} | `{r['name']}` | `{r['where']}` | {r['note']} |"
        )
    body = [
        f"## Assembler vs RARS — {n_pass}/{len(results)} passing",
        "",
        f"Custom test programs in repo root: **{custom_count}** (required: {required})",
        "",
        *rows,
    ]
    fails = [r for r in results if r["status"] != "pass"]
    if fails:
        body += ["", "<details><summary>Failure detail</summary>", "", "```"]
        for r in fails:
            body += [f"--- {r['name']} ---", r["detail"], ""]
        body += ["```", "</details>"]
    Path(path).write_text("\n".join(body) + "\n")


ANSI = re.compile(r"\033\[[0-9;]*m")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "paths",
        nargs="*",
        default=[str(ROOT)],
        help="directories or .s files to test (default: repo root)",
    )
    ap.add_argument("--rars", default=DEFAULT_JAR, help="path to rars.jar")
    ap.add_argument("-k", "--filter", default="", help="substring filter on name")
    ap.add_argument(
        "--golden", default=str(ROOT / "golden"), help="cache directory for RARS output"
    )
    ap.add_argument(
        "--update-golden",
        action="store_true",
        help="regenerate cached RARS output even if it exists",
    )
    ap.add_argument(
        "--no-sol",
        action="store_true",
        help="ignore committed *_sol.*.txt reference files",
    )
    ap.add_argument(
        "--mem-config", default=None, help="RARS 'mc' value, e.g. CompactTextAtZero"
    )
    ap.add_argument(
        "--data-granularity",
        choices=["byte", "word"],
        default="byte",
        help="format of the .data golden dump: phase_1.pdf specifies "
        "byte-per-line (default); pass 'word' if the committed "
        "*_sol_data.*.txt files turn out to be RARS's native "
        "word-per-line format instead",
    )
    ap.add_argument(
        "--instr-granularity",
        choices=["byte", "word"],
        default="word",
        help="format of the .text golden dump (default: word/entry-"
        "per-line, i.e. one instruction per line)",
    )
    ap.add_argument(
        "--endian",
        choices=["little", "big"],
        default="little",
        help="byte order used when exploding a word into bytes "
        "for byte-granularity output (RV32I is little-endian)",
    )
    ap.add_argument("--text-base", type=lambda s: int(s, 0), default=0x00400000)
    ap.add_argument("--data-base", type=lambda s: int(s, 0), default=0x10010000)
    ap.add_argument("--max-diffs", type=int, default=5)
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--skip-bin", action="store_true")
    ap.add_argument(
        "--strict-padding",
        action="store_true",
        help="do not ignore trailing zero words",
    )
    ap.add_argument(
        "--require-custom",
        type=int,
        default=0,
        help="fail if fewer than N non-provided .s files sit in "
        "the repo root (the programs we must write ourselves)",
    )
    ap.add_argument("--summary-md", help="write a markdown summary here")
    ap.add_argument("--junit", help="write JUnit XML here")
    ap.add_argument("--keep", action="store_true", help="keep the temp work dir")
    args = ap.parse_args()

    if not Path(args.rars).exists():
        sys.exit(
            f"rars.jar not found at {args.rars}. Set RARS_JAR or run: make rars.jar"
        )
    if not STUDENT_SH.exists():
        sys.exit(f"missing {STUDENT_SH} — that's the adapter for your assembler")

    srcs = discover(args.paths, args.filter)
    if not srcs:
        sys.exit(f"no matching .s files under {', '.join(args.paths)}")

    custom = [s for s in srcs if s.parent.resolve() == ROOT and s.stem not in PROVIDED]

    work = Path(tempfile.mkdtemp(prefix="rvdiff-"))
    golden_root = Path(args.golden)
    results = []

    for src in srcs:
        name = src.stem
        where = "root" if src.parent.resolve() == ROOT else src.parent.name
        opts = file_options(src)
        mem_config = opts["mc"] or args.mem_config
        data_gran = opts["data-granularity"] or args.data_granularity
        instr_gran = opts["instr-granularity"] or args.instr_granularity
        endian = opts["endian"] or args.endian
        gdir = golden_root / where / name

        if args.update_golden or not gdir.exists():
            shutil.rmtree(gdir, ignore_errors=True)
            okg, err = run_rars(
                args.rars,
                src,
                gdir,
                mem_config,
                data_granularity=data_gran,
                instr_granularity=instr_gran,
                endian=endian,
            )
            if okg and err:
                print(
                    f"{YEL}WARN {RESET} {name}: RARS warnings on the golden run "
                    f"(the golden file may be wrong):"
                )
                for l in err.splitlines():
                    print(f"  {l}")
            if not okg:
                print(
                    f"{RED}ERROR{RESET} {name}: RARS rejected the source "
                    f"(the test program itself is bad)\n  {err}"
                )
                shutil.rmtree(gdir, ignore_errors=True)
                results.append(
                    {
                        "name": name,
                        "where": where,
                        "status": "error",
                        "note": "RARS rejected the source",
                        "detail": err,
                    }
                )
                continue

        mdir = work / where / name
        okm, err = run_student(src, mdir)
        if not okm:
            print(f"{RED}ERROR{RESET} {name}: your assembler exited non-zero")
            for l in err.splitlines()[:15]:
                print(f"  {l}")
            results.append(
                {
                    "name": name,
                    "where": where,
                    "status": "error",
                    "note": "assembler exited non-zero",
                    "detail": err,
                }
            )
            continue

        status, lines, stats = compare(src, gdir, mdir, args, opts)
        detail = ANSI.sub("", "\n".join(lines))
        note = "matches"
        if stats["sol_files"]:
            note = (
                "matches committed reference"
                if not stats["sol_mismatch"]
                else "reference/RARS oracle mismatch"
            )
        if status == "pass":
            print(
                f"{GRN}PASS {RESET} {name}"
                + (f" {DIM}({note}){RESET}" if stats["sol_files"] else "")
            )
            if lines:
                print("\n".join(lines))
        else:
            print(f"{RED}FAIL {RESET} {name}")
            print("\n".join(lines))
            note = "output differs"
        results.append(
            {
                "name": name,
                "where": where,
                "status": status,
                "note": note,
                "detail": detail,
            }
        )

    n_pass = sum(1 for r in results if r["status"] == "pass")
    n_fail = sum(1 for r in results if r["status"] == "fail")
    n_err = sum(1 for r in results if r["status"] == "error")
    print(f"\n{n_pass} passed, {n_fail} failed, {n_err} errored")
    print(
        f"custom test programs in repo root: {len(custom)}"
        + (f" (need {args.require_custom})" if args.require_custom else "")
    )

    short = args.require_custom and len(custom) < args.require_custom
    if short:
        have = ", ".join(s.name for s in custom) or "none"
        print(
            f"{RED}Only {len(custom)} of {args.require_custom} required custom "
            f"programs present: {have}{RESET}"
        )

    if args.summary_md:
        write_summary(args.summary_md, results, len(custom), args.require_custom)
    if args.junit:
        write_junit(args.junit, results)

    if args.keep:
        print(f"work dir: {work}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if (n_fail or n_err or short) else 0


if __name__ == "__main__":
    sys.exit(main())
