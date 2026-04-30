#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_service_tests() {
  local service="$1"
  local test_dir="$ROOT_DIR/services/$service/tests"
  local service_dir="$ROOT_DIR/services/$service"

  echo "=============================================="
  echo "Running tests for: $service"
  echo "=============================================="

  if [[ -d "$test_dir" ]] && compgen -G "$test_dir/test_*.py" > /dev/null; then
    (cd "$service_dir" && python -m pytest tests -q)
  else
    echo "WARNING: No tests found for $service"
  fi
}

run_service_tests "gps-service"
run_service_tests "camera-service"
run_service_tests "risk-engine"
run_service_tests "cloud-api"
run_service_tests "pipeline"
run_service_tests "telemetry-service"
run_service_tests "v2x-simulator"

echo "All available service tests completed successfully."
