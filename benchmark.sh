#!/bin/bash

set -euo pipefail

DURATION_MINUTES="${1:-30}"
INTERVAL_SECONDS="${2:-15}"
SAMPLES=$((DURATION_MINUTES * 60 / INTERVAL_SECONDS))

echo "Starting Phase 2 benchmark for ${DURATION_MINUTES} minutes"
docker compose down
docker compose up -d --build

echo "timestamp,container,cpu_perc,mem_perc,mem_usage" > benchmark_metrics.csv

for ((i=1; i<=SAMPLES; i++)); do
    TIMESTAMP=$(date +%s)
    docker stats --no-stream --format "${TIMESTAMP},{{.Name}},{{.CPUPerc}},{{.MemPerc}},{{.MemUsage}}" >> benchmark_metrics.csv
    sleep "${INTERVAL_SECONDS}"
done

echo "Collecting engine logs"
docker compose logs engine > benchmark_latency.log 2>&1

echo "Benchmark completed"
