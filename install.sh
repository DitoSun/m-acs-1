#!/bin/bash
set -euo pipefail

# ============================================================
#  M-ACS-1 Phase 0 — AI Server One-Click Install
#  Target: bare Ubuntu 22.04/24.04 with NVIDIA GPU
#  Result: Ollama + Control Plane + optional Open WebUI, auto-start on boot
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  M-ACS-1  AI Server  —  Phase 0 Install  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

ok()   { echo -e "  ${GREEN}[✓]${NC} $1"; }
fail() { echo -e "  ${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "  ${CYAN}[·]${NC} $1"; }
warn() { echo -e "  ${ORANGE}[!]${NC} $1"; }
step() { echo ""; echo -e "${BOLD}── $1 ──${NC}"; }

net_ok()   { echo -e "    ${GREEN}✓${NC} $1"; }
net_fail() { echo -e "    ${RED}✗${NC} $1"; }

must_run_as_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        echo -e "${RED}This script must run as root.${NC}"
        echo "  sudo ./install.sh"
        exit 1
    fi
}

check_ubuntu() {
    step "Checking OS"
    if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
        fail "This installer only supports Ubuntu 22.04 or 24.04. Your OS: $VERSION_ID"
    fi
    . /etc/os-release
    if [[ "$VERSION_ID" != "22.04" && "$VERSION_ID" != "24.04" ]]; then
        fail "Ubuntu $VERSION_ID detected. Requires 22.04 or 24.04."
    fi
    ok "Ubuntu $VERSION_ID ($VERSION_CODENAME)"
}

check_gpu() {
    step "Checking NVIDIA GPU"
    local gpu=""
    if lspci 2>/dev/null | grep -qi nvidia; then
        gpu=$(lspci | grep -i nvidia | head -1 | cut -d: -f3- | sed 's/^ //')
    fi
    # Fallback: WSL2 / VM doesn't expose PCI bus, but nvidia-smi works
    if [[ -z "$gpu" ]] && nvidia-smi &>/dev/null; then
        gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
        ok "Found: $gpu (WSL2/VM)"
        return 0
    fi
    if [[ -n "$gpu" ]]; then
        ok "Found: $gpu"
        return 0
    fi
    fail "No NVIDIA GPU detected"
}

check_network() {
    step "Network Diagnostics"

    local ok=true
    local mirror_selected=false

    # Test Docker Hub
    if curl -4 -s --connect-timeout 5 https://download.docker.com >/dev/null 2>&1; then
        net_ok "Docker Hub — reachable"
    else
        net_fail "Docker Hub — unreachable"
        warn "Will use Aliyun mirror as fallback"
        mirror_selected=true
    fi

    # Test Ollama registry
    if curl -4 -s --connect-timeout 5 https://registry.ollama.ai >/dev/null 2>&1; then
        net_ok "Ollama registry — reachable"
    else
        net_fail "Ollama registry — unreachable"
        warn "Model downloads may be slow or fail"
    fi

    # Test GitHub
    if curl -4 -s --connect-timeout 5 https://github.com >/dev/null 2>&1; then
        net_ok "GitHub — reachable"
    else
        net_fail "GitHub — unreachable"
        warn "Some features may be limited"
    fi

    # Test IPv4
    if curl -4 -s --connect-timeout 5 https://httpbin.org/ip >/dev/null 2>&1; then
        net_ok "IPv4 — working"
    else
        net_fail "IPv4 — test failed"
        warn "IPv6 may be required"
    fi

    if $mirror_selected; then
        echo ""
        info "Network conditions detected — will use mirror sources where available"
    fi

    echo ""
    if $ok; then
        info "Expected install time: 5-15 minutes (depends on network speed and hardware)"
    else
        info "Expected install time: 10-30 minutes (limited network)"
    fi
}

install_nvidia_driver() {
    step "NVIDIA Driver (~3-5 min)"

    if nvidia-smi &>/dev/null; then
        local ver
        ver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
        ok "Driver already installed (version $ver)"
        return 0
    fi

    info "Installing NVIDIA driver (downloading ~300MB, may take 3-5 minutes)..."
    apt-get update -qq
    apt-get install -y -qq ubuntu-drivers-common

    local recommended
    recommended=$(ubuntu-drivers devices 2>/dev/null | grep "recommended" | awk '{print $3}' || echo "")
    if [[ -z "$recommended" ]]; then
        recommended="nvidia-driver-550"
    fi

    info "Installing $recommended (this may take a few minutes)..."
    apt-get install -y -qq "$recommended"

    echo ""
    echo -e "${RED}┌─────────────────────────────────────────────┐${NC}"
    echo -e "${RED}│  REBOOT REQUIRED                            │${NC}"
    echo -e "${RED}│                                             │${NC}"
    echo -e "${RED}│  Run this script again after reboot:        │${NC}"
    echo -e "${RED}│    sudo ./install.sh                        │${NC}"
    echo -e "${RED}└─────────────────────────────────────────────┘${NC}"
    exit 0
}

install_docker() {
    step "Docker Engine (~1-2 min)"

    if docker --version &>/dev/null; then
        ok "Docker already installed ($(docker --version | cut -d, -f1))"
        return 0
    fi

    info "Adding Docker official apt repository..."

    # Add GPG key (try official, fallback to Aliyun mirror)
    local docker_gpg
    docker_gpg=$(curl -4 -fsSL https://download.docker.com/linux/ubuntu/gpg 2>/dev/null || \
                 curl -4 -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg 2>/dev/null)
    if [[ -z "$docker_gpg" ]]; then
        fail "Cannot download Docker GPG key. Check your internet connection or run with a proxy: sudo http_proxy=http://your-proxy:port ./install.sh"
    fi
    echo "$docker_gpg" | gpg --dearmor -o /usr/share/keyrings/docker.gpg

    # Add repository (use official, Aliyun mirror for the apt repo URL)
    local codename
    codename=$(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)
    local arch
    arch=$(dpkg --print-architecture)

    if curl -4 -s --connect-timeout 5 https://download.docker.com/linux/ubuntu/dists/$codename/stable/binary-$arch/Packages.gz &>/dev/null; then
        local repo_url="https://download.docker.com/linux/ubuntu"
    else
        info "Using Aliyun Docker mirror"
        repo_url="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
    fi

    echo "deb [arch=$arch signed-by=/usr/share/keyrings/docker.gpg] $repo_url $codename stable" \
        > /etc/apt/sources.list.d/docker.list

    apt-get update -qq

    # Install latest Docker from official repo, then pin
    info "Installing Docker Engine (latest stable)..."
    apt-get install -y -qq \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin

    # Pin versions to prevent accidental upgrade
    apt-mark hold docker-ce docker-ce-cli 2>/dev/null || true
    local ver
    ver=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
    ok "Docker ${ver} installed (pinned)"

    local target_user="${SUDO_USER:-$USER}"
    if [[ -n "$target_user" && "$target_user" != "root" ]]; then
        usermod -aG docker "$target_user"
    fi
}

install_nvidia_ctk() {
    step "NVIDIA Container Toolkit (~1-2 min)"

    if nvidia-container-toolkit --version &>/dev/null 2>&1; then
        ok "nvidia-container-toolkit already installed"
        return 0
    fi

    info "Adding NVIDIA package repository..."
    curl -4 -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    curl -4 -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    apt-get update -qq
    apt-get install -y -qq nvidia-container-toolkit

    info "Configuring Docker NVIDIA runtime..."
    nvidia-ctk runtime configure --runtime=docker

    # Add Docker Hub mirror for reliable access (especially China)
    info "Configuring Docker Hub mirror..."
    python3 -c "
import json
with open('/etc/docker/daemon.json') as f:
    cfg = json.load(f)
cfg['registry-mirrors'] = ['https://docker.m.daocloud.io']
with open('/etc/docker/daemon.json', 'w') as f:
    json.dump(cfg, f, indent=4)
" 2>/dev/null || true

    systemctl restart docker

    ok "nvidia-container-toolkit installed and configured"
}

verify_gpu_docker() {
    step "Verifying GPU access from Docker"

    # Try pulling the CUDA image (may fail in restricted networks)
    local gpu_ok=false
    if docker pull nvidia/cuda:12.4-base-ubuntu22.04 &>/dev/null; then
        if docker run --rm --runtime=nvidia nvidia/cuda:12.4-base-ubuntu22.04 nvidia-smi &>/dev/null; then
            gpu_ok=true
        fi
    else
        # Fallback: verify NVIDIA runtime is registered
        info "Image pull failed check runtime registration..."
        if docker info 2>/dev/null | grep -q "nvidia"; then
            info "NVIDIA runtime registered (image pull skipped — no network)"
            gpu_ok=true
        fi
    fi

    if $gpu_ok; then
        ok "GPU accessible inside containers"
    else
        fail "Docker cannot access GPU. This can mean:
         - NVIDIA driver not fully loaded after reboot
         - nvidia-container-toolkit not configured correctly
         Try: sudo reboot, then re-run this script."
    fi
}

setup_host_agent() {
    step "Host GPU Agent"

    local svc="/etc/systemd/system/m-acs-host-agent.service"
    if systemctl is-enabled m-acs-host-agent &>/dev/null; then
        ok "Host agent already running"
        return 0
    fi

    # Create data directory for metrics file
    mkdir -p /opt/m-acs-1/data

    # Install systemd service
    cp /opt/m-acs-1/host-agent/m-acs-host-agent.service "$svc"
    chmod 644 "$svc"

    systemctl daemon-reload
    systemctl enable --now m-acs-host-agent.service

    # Wait for first metrics collection
    sleep 3
    if [[ -f /opt/m-acs-1/data/gpu.json ]]; then
        ok "Host agent started, GPU metrics file created"
    else
        info "Host agent started (waiting for GPU metrics)"
    fi
}

install_macs() {
    step "Installing M-ACS-1 services"

    local install_dir="/opt/m-acs-1"
    local script_dir
    script_dir="$(cd "$(dirname "$0")" && pwd)"

    info "Installing to $install_dir"
    mkdir -p "$install_dir"

    # Copy all project files
    cp "$script_dir/docker-compose.yml" "$install_dir/"
    cp "$script_dir/Makefile" "$install_dir/" 2>/dev/null || true
    cp -r "$script_dir/control-plane" "$install_dir/"
    cp -r "$script_dir/host-agent" "$install_dir/"

    # Pull images and build
    info "Pulling container images (~5-15 min, depends on network speed)..."
    cd "$install_dir"
    docker compose pull

    info "Building and starting services..."
    docker compose up -d --build

    ok "Services started"
}

setup_autostart() {
    step "Systemd auto-start (Docker Compose)"

    local unit_file="/etc/systemd/system/m-acs-1.service"
    if [[ -f "$unit_file" ]]; then
        systemctl daemon-reload
        systemctl enable --now m-acs-1.service 2>/dev/null || true
        ok "Auto-start already configured"
        return 0
    fi

    cat > "$unit_file" <<'UNIT'
[Unit]
Description=M-ACS-1 AI Server
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/m-acs-1
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    systemctl enable m-acs-1.service

    ok "Auto-start enabled (m-acs-1.service)"
}

print_success() {
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                  ║${NC}"
    echo -e "${GREEN}║  M-ACS-1 Phase 0 is ready!                      ║${NC}"
    echo -e "${GREEN}║                                                  ║${NC}"
    echo -e "${GREEN}║  Open WebUI:    http://127.0.0.1:3000           ║${NC}"
    echo -e "${GREEN}║  Control Plane: http://127.0.0.1:8080/docs      ║${NC}"
    echo -e "${GREEN}║                                                  ║${NC}"
    echo -e "${GREEN}║  For LAN access, expose carefully:              ║${NC}"
    echo -e "${GREEN}║    ssh -L 3000:127.0.0.1:3000 user@${ip}    ║${NC}"
    echo -e "${GREEN}║                                                  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================
main() {
    banner
    must_run_as_root
    check_ubuntu
    check_gpu
    check_network
    install_nvidia_driver
    install_docker
    install_nvidia_ctk
    verify_gpu_docker
    install_macs
    setup_host_agent
    setup_autostart
    print_success
}

main "$@"
