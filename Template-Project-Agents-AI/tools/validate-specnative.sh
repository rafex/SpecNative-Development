#!/usr/bin/env bash

set -euo pipefail

required_files=(
  "AGENTS.md"
  "README.md"
  "agents/README.md"
  "agents/PRODUCT.md"
  "agents/ARCHITECTURE.md"
  "agents/STACK.md"
  "agents/CONVENTIONS.md"
  "agents/COMMANDS.md"
  "agents/DECISIONS.md"
  "agents/ROADMAP.md"
  "agents/SCHEMA.md"
  "agents/TRACEABILITY.md"
  "tasks/README.md"
  "workflows/README.md"
)

failed=0

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required file: $file"
    failed=1
  fi
done

if ! find agents -path "*/SPEC.md" -o -name "SPEC.md" | grep -q "SPEC.md"; then
  echo "Missing required spec: agents/SPEC.md or agents/specs/**/SPEC.md"
  failed=1
fi

if [[ $failed -ne 0 ]]; then
  echo "SpecNative validation failed"
  exit 1
fi

echo "SpecNative validation passed"
