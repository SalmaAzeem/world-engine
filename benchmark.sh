#!/bin/bash

echo "30 min test"
docker compose down
docker compose up -d --build

echo "timestamp,container,cpu_perc,mem_perc,mem_usage" > benchmark_metrics.csv

for i in {1..120}; do
    TIMESTAMP=$(date +%s)
    docker stats --no-stream --format "$TIMESTAMP,{{.Name}},{{.CPUPerc}},{{.MemPerc}},{{.MemUsage}}" >> benchmark_metrics.csv
    sleep 15
done

echo "Event loop latency logs"
docker logs world-engine > benchmark_latency.log 2>&1

echo "benchmark completed"
