#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "usage: $0 <name> [submission_dir]" >&2
    exit 1
fi
SUMMARY_FILE="${SCRIPT_DIR}/results/$1.txt"
SUBMISSION_ARG="${2:-${SCRIPT_DIR}}"

OUTPUT_DIR="${SCRIPT_DIR}/output"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}" "${SCRIPT_DIR}/results"

if [[ ! -d "${SUBMISSION_ARG}" ]]; then
    echo "ERROR: submission directory not found: ${SUBMISSION_ARG}" >&2
    echo "Put your assembler.py and your addition.s, gemm.s, mult.s and" >&2
    echo "sobel.s in ${SCRIPT_DIR}/, or pass the directory that holds them" >&2
    echo "as the second argument." >&2
    exit 1
fi
SUBMISSION_DIR="$(cd "${SUBMISSION_ARG}" && pwd)"
echo "Submission under test: ${SUBMISSION_DIR}"

status=0
python3 "${SCRIPT_DIR}/source_test/grade_test.py" \
    "${SUBMISSION_DIR}" "${OUTPUT_DIR}" "${SUMMARY_FILE}" || status=$?

echo "Wrote ${SUMMARY_FILE}"
echo "Run artifacts (spliced programs, RARS dumps, gen/ files): ${OUTPUT_DIR}"
exit "${status}"
