#!/usr/bin/env bash
set -euo pipefail

# scripts/generate-all-examples.sh
#
# For every *.json under ./examples/**, run scripts/cli-bulk-gif-gen.tape with:
#   - $config = path to the json file
#   - $output = docs/images/examples/<json_basename>.gif

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

EXAMPLES_DIR="${REPO_ROOT}/examples"
OUT_DIR="${REPO_ROOT}/docs/images/examples"
TAPE_FILE="${REPO_ROOT}/scripts/cli-bulk-gif-gen.tape"

if [[ ! -d "${EXAMPLES_DIR}" ]]; then
  echo "ERROR: examples folder not found at: ${EXAMPLES_DIR}" >&2
  exit 1
fi

if [[ ! -f "${TAPE_FILE}" ]]; then
  echo "ERROR: tape file not found at: ${TAPE_FILE}" >&2
  exit 1
fi

if ! command -v vhs >/dev/null 2>&1; then
  echo "ERROR: 'vhs' is not installed or not on PATH." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
cd "${REPO_ROOT}"

count=0
while IFS= read -r -d '' json_file; do
  base="$(basename -- "${json_file}" .json)"
  out_file="${OUT_DIR}/${base}.gif"

  echo "Generating: ${out_file}"
  config="${json_file}" vhs -o "${out_file}" "${TAPE_FILE}"

  count=$((count + 1))
done < <(find "${EXAMPLES_DIR}" -type f -name '*.json' -print0 | sort -z)

echo "Done. Generated ${count} GIF(s) in: ${OUT_DIR}"