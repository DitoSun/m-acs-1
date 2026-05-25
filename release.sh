#!/bin/bash
set -euo pipefail

# ============================================================
# M-ACS-1 Release Packaging Script
# Usage: ./release.sh [version]
#   Produces: m-acs-{version}.tar.gz + SHA256SUMS
# ============================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
HERE="$(cd "$(dirname "$0")" && pwd)"

VERSION="${1:-$(cat "$HERE/VERSION" 2>/dev/null || echo "0.1.0")}"
RELEASE_NAME="m-acs-${VERSION}"
RELEASE_DIR="/tmp/${RELEASE_NAME}"
TARBALL="${HERE}/${RELEASE_NAME}.tar.gz"

echo -e "${CYAN}Building M-ACS-1 release ${VERSION}${NC}"

# Clean
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/control-plane" "$RELEASE_DIR/host-agent"

# Core application files
echo "  Copying application..."
cp "$HERE/VERSION" "$RELEASE_DIR/"
cp "$HERE/docker-compose.yml" "$RELEASE_DIR/"
cp "$HERE/control-plane/Dockerfile" "$RELEASE_DIR/control-plane/"
mkdir -p "$RELEASE_DIR/control-plane"
cp -r "$HERE/control-plane/main.py" "$RELEASE_DIR/control-plane/"
cp "$HERE/control-plane/config.py" "$RELEASE_DIR/control-plane/"
cp -r "$HERE/control-plane/static" "$RELEASE_DIR/control-plane/"
cp -r "$HERE/control-plane/services" "$RELEASE_DIR/control-plane/"
cp -r "$HERE/control-plane/rag" "$RELEASE_DIR/control-plane/"
mkdir -p "$RELEASE_DIR/host-agent"
cp "$HERE/host-agent/collector.py" "$RELEASE_DIR/host-agent/"
cp "$HERE/host-agent/m-acs-host-agent.service" "$RELEASE_DIR/host-agent/"

# Installer and scripts
cp "$HERE/install.sh" "$RELEASE_DIR/"
cp "$HERE/release.sh" "$RELEASE_DIR/"
cp "$HERE/VERSION" "$RELEASE_DIR/"

# Create tarball
echo -e "  Packaging ${TARBALL}..."
tar -czf "$TARBALL" -C /tmp "$RELEASE_NAME"

# Checksums
echo "  Generating checksums..."
(cd "$HERE" && sha256sum "${RELEASE_NAME}.tar.gz" > "${RELEASE_NAME}.sha256")
(cd "$HERE" && sha256sum "${RELEASE_NAME}.tar.gz" | awk '{print $1}' > "${RELEASE_NAME}.checksum")

echo -e "${GREEN}Release ${VERSION} ready:${NC}"
echo "  ${TARBALL}"
echo "  ${RELEASE_NAME}.sha256"
echo "  ${RELEASE_NAME}.checksum"
echo ""
echo "Size: $(du -h "$TARBALL" | cut -f1)"
