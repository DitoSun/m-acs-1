#!/bin/bash
# M-ACS-1 Uninstall — removes all services and data
# Usage: sudo ./uninstall.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
echo -e "${RED}║  M-ACS-1 Uninstall                       ║${NC}"
echo -e "${RED}║  This will remove all services and data.  ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
echo ""

if [[ "$(id -u)" -ne 0 ]]; then
    echo -e "${RED}This script must run as root.${NC}"
    echo "  sudo ./uninstall.sh"
    exit 1
fi

echo -e "${CYAN}[·]${NC} Stopping services..."
systemctl stop m-acs-host-agent 2>/dev/null || true
systemctl stop m-acs-1.service 2>/dev/null || true
systemctl disable m-acs-host-agent 2>/dev/null || true
systemctl disable m-acs-1.service 2>/dev/null || true

echo -e "${CYAN}[·]${NC} Removing systemd units..."
rm -f /etc/systemd/system/m-acs-host-agent.service
rm -f /etc/systemd/system/m-acs-1.service
systemctl daemon-reload

echo -e "${CYAN}[·]${NC} Stopping Docker containers..."
cd /opt/m-acs-1 2>/dev/null && docker compose down -v 2>/dev/null || true

echo -e "${CYAN}[·]${NC} Removing M-ACS-1 directory..."
rm -rf /opt/m-acs-1

echo -e "${CYAN}[·]${NC} Unsetting Docker package holds..."
apt-mark unhold docker-ce docker-ce-cli 2>/dev/null || true

echo ""
echo -e "${GREEN}✓ M-ACS-1 has been removed.${NC}"
echo ""
echo "Your NVIDIA driver and Docker remain installed."
echo "To remove them separately:"
echo "  sudo apt-get purge nvidia-driver-*"
echo "  sudo apt-get purge docker-ce docker-ce-cli"
echo ""
