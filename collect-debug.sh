#!/bin/bash
# M-ACS-1 Debug Bundle — run this and paste the output into your GitHub issue
# Usage: bash collect-debug.sh

set -euo pipefail

echo "============================================"
echo "  M-ACS-1 Debug Bundle"
echo "  Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# 1. OS info
echo "--- OS ---"
grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '"'
uname -r
echo ""

# 2. GPU info
echo "--- GPU ---"
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,driver_version,temperature.gpu,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi failed"
else
    echo "nvidia-smi not found"
fi
echo ""

# 3. Docker
echo "--- Docker ---"
docker --version 2>/dev/null || echo "docker not found"
docker compose version 2>/dev/null || echo "docker compose not found"
echo ""
echo "--- Containers ---"
(cd /opt/m-acs-1 && docker compose ps 2>/dev/null) || echo "Cannot run docker compose ps"
echo ""

# 4. Service status
echo "--- Services ---"
systemctl status m-acs-host-agent --no-pager 2>/dev/null | grep Active || echo "m-acs-host-agent not found"
systemctl status m-acs-1.service --no-pager 2>/dev/null | grep Active || echo "m-acs-1.service not found"
echo ""

# 5. GPU metrics
echo "--- GPU Metrics File ---"
if [ -f /opt/m-acs-1/data/gpu.json ]; then
    cat /opt/m-acs-1/data/gpu.json
else
    echo "gpu.json not found"
fi
echo ""

# 6. Control-plane logs (last 10 lines)
echo "--- Control Plane Logs ---"
(cd /opt/m-acs-1 && docker compose logs --tail=10 control-plane 2>/dev/null) || echo "Cannot get logs"
echo ""

# 7. Ports
echo "--- Port Check ---"
ss -tlnp 2>/dev/null | grep -E '8080|11434|3000' || echo "ports not checked"
echo ""

# 8. Network
echo "--- Network ---"
curl -4 -s --connect-timeout 3 https://download.docker.com >/dev/null 2>&1 && echo "Docker Hub: reachable" || echo "Docker Hub: unreachable"
curl -4 -s --connect-timeout 3 https://registry.ollama.ai >/dev/null 2>&1 && echo "Ollama registry: reachable" || echo "Ollama registry: unreachable"
curl -4 -s --connect-timeout 3 https://github.com >/dev/null 2>&1 && echo "GitHub: reachable" || echo "GitHub: unreachable"
echo ""

# 9. Disk
echo "--- Disk ---"
df -h / | tail -1 | awk '{print "Available: "$4" of "$2}'
echo ""

echo "============================================"
echo "  End of Debug Bundle"
echo "  Copy everything above and paste it into"
echo "  your GitHub issue."
echo "============================================"
