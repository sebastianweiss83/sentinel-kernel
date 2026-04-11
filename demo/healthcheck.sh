#!/usr/bin/env bash
# Check Sentinel demo service health from the host.
set -u
echo "Checking Sentinel demo services..."
curl -sf http://localhost:3001/api/health >/dev/null && echo "  Grafana       OK" || echo "  Grafana       DOWN"
curl -sf http://localhost:9090/-/healthy >/dev/null && echo "  Prometheus    OK" || echo "  Prometheus    DOWN"
curl -sf http://localhost:13133         >/dev/null && echo "  OTel          OK" || echo "  OTel          DOWN"
curl -sf http://localhost:3000/api/public/health >/dev/null && echo "  LangFuse      OK" || echo "  LangFuse      DOWN (not expected in minimal)"
echo "Done."
