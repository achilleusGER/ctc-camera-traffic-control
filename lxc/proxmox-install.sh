#!/usr/bin/env bash
# Hermes-Trafficcontrol — Proxmox-LXC erstellen
# Community-scripts.org-Style: ein Befehl, alles drin.
#
# Verwendung (auf dem Proxmox-Host, als root):
#
#   # Standard: LXC 240, IP 10.10.1.250, alles default
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/achilleusGER/ctc-camera-traffic-control/main/lxc/proxmox-install.sh)"
#
#   # Mit eigenen Werten:
#   bash proxmox-install.sh --id 241 --ip 10.10.1.251/24 --hostname traffic-2
#
#   # Unattended (z.B. Ansible):
#   bash proxmox-install.sh --id 240 --ip 10.10.1.250/24 --unattended
#
# Hilfe:  bash proxmox-install.sh --help
#
# Was es macht:
#   1. Prueft root + pve-Umgebung
#   2. Laedt ggf. Debian-12-Template
#   3. pct create + start
#   4. Wartet auf Netzwerk
#   5. Klone Repo in den LXC
#   6. Fragt: setup.sh jetzt ausfuehren? (oder unattended: ja)

set -euo pipefail
shopt -s nocasematch

# ── Defaults ─────────────────────────────────────────────────────────────
LXC_ID=240
LXC_HOSTNAME="hermes-trafficcontrol"
LXC_CORES=12
LXC_MEMORY=12288        # MB
LXC_SWAP=2048
LXC_DISK=64             # GB
LXC_BRIDGE=vmbr0
LXC_IP="10.10.1.250/24"
LXC_GW="10.10.1.1"
LXC_STORAGE="local-lvm"
TEMPLATE_STORAGE="local"
TEMPLATE_NAME="debian-12-standard_12.2_1.amd64.tar.zst"
REMOTE="https://github.com/achilleusGER/ctc-camera-traffic-control.git"
BRANCH="main"
UNATTENDED=0
RUN_SETUP=0
SSH_KEY_FILE="${HOME}/.ssh/authorized_keys"

# ── Farben (wie community-scripts) ──────────────────────────────────────
RD="\033[01;31m"          # red
YW="\033[01;33m"          # yellow
GN="\033[01;32m"          # green
BL="\033[01;36m"          # blue
CY="\033[01;36m"          # cyan
WT="\033[00m"             # white
BOLD="\033[01m"
HOLD="\033[01;100m"       # background grey
CLR="\033[0m"

msg_info()  { printf "${BL}[INFO]${CLR} %s\n" "$*"; }
msg_ok()    { printf "${GN}[OK]${CLR}   %s\n" "$*"; }
msg_warn()  { printf "${YW}[WARN]${CLR} %s\n" "$*" >&2; }
msg_err()   { printf "${RD}[ERR]${CLR}  %s\n" "$*" >&2; }
msg_step()  { printf "\n${CY}========== %s ==========${CLR}\n" "$*"; }

# ── Help ────────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
${BOLD}Hermes-Trafficcontrol LXC-Installer${CLR}

Erstellt einen Debian-12-LXC auf Proxmox, klont das Repo, optional Setup.

${BOLD}Usage:${CLR} $0 [OPTIONS]

${BOLD}Options:${CLR}
  --id ID            LXC-ID (default: ${LXC_ID})
  --hostname NAME    Hostname  (default: ${LXC_HOSTNAME})
  --ip CIDR          IP/Maske  (default: ${LXC_IP})
  --gw IP            Gateway   (default: ${LXC_GW})
  --bridge NAME      Linux-Bridge  (default: ${LXC_BRIDGE})
  --cores N          CPU-Kerne  (default: ${LXC_CORES})
  --memory MB        RAM in MB   (default: ${LXC_MEMORY})
  --disk GB          Disk in GB  (default: ${LXC_DISK})
  --storage NAME     Storage fuer RootFS (default: ${LXC_STORAGE})
  --ssh-key FILE     Pfad zu authorized_keys (default: ${SSH_KEY_FILE})
  --unattended       Keine Rueckfragen
  --run-setup        Nach pct create sofort setup.sh im LXC ausfuehren
  --remote URL       Git-Remote (default: ${REMOTE})
  --branch NAME      Git-Branch (default: ${BRANCH})
  --help             Diese Hilfe

${BOLD}Beispiele:${CLR}
  $0 --id 240                                      # Standard
  $0 --id 241 --ip 10.10.1.251/24                  # andere IP
  $0 --id 240 --unattended --run-setup             # CI/Automation

EOF
    exit 0
}

# ── Arg parsen ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --id)        LXC_ID="$2"; shift 2;;
        --hostname)  LXC_HOSTNAME="$2"; shift 2;;
        --ip)        LXC_IP="$2"; shift 2;;
        --gw)        LXC_GW="$2"; shift 2;;
        --bridge)    LXC_BRIDGE="$2"; shift 2;;
        --cores)     LXC_CORES="$2"; shift 2;;
        --memory)    LXC_MEMORY="$2"; shift 2;;
        --disk)      LXC_DISK="$2"; shift 2;;
        --storage)   LXC_STORAGE="$2"; shift 2;;
        --ssh-key)   SSH_KEY_FILE="$2"; shift 2;;
        --unattended) UNATTENDED=1; shift;;
        --run-setup) RUN_SETUP=1; shift;;
        --remote)    REMOTE="$2"; shift 2;;
        --branch)    BRANCH="$2"; shift 2;;
        -h|--help)   usage;;
        *)           msg_err "Unbekanntes Argument: $1"; usage;;
    esac
done

# ── Voraussetzungen prüfen ─────────────────────────────────────────────
[[ $EUID -eq 0 ]] || { msg_err "Als root auf dem Proxmox-Host ausfuehren."; exit 1; }
command -v pct    >/dev/null || { msg_err "pct nicht gefunden — ist das ein Proxmox-Host?"; exit 1; }
command -v pveam  >/dev/null || { msg_err "pveam nicht gefunden."; exit 1; }

msg_step "Zusammenfassung"
cat <<EOF
  LXC-ID:       ${LXC_ID}
  Hostname:     ${LXC_HOSTNAME}
  CPU/RAM/Disk: ${LXC_CORES} Kerne / ${LXC_MEMORY} MB / ${LXC_DISK} GB
  Netz:         ${LXC_IP} via ${LXC_BRIDGE} (GW ${LXC_GW})
  Storage:      ${LXC_STORAGE}
  Template:     ${TEMPLATE_NAME}
  Remote:       ${REMOTE}@${BRANCH}
  Unattended:   ${UNATTENDED}
  Run-Setup:    ${RUN_SETUP}
EOF
echo

if [[ $UNATTENDED -eq 0 ]]; then
    read -rp "Mit diesen Werten fortfahren? [j/N] " ok
    [[ "$ok" =~ ^j ]] || { msg_warn "Abgebrochen."; exit 0; }
fi

# ── LXC-ID-Konflikt? ──────────────────────────────────────────────────
if pct status "${LXC_ID}" &>/dev/null; then
    msg_err "LXC ${LXC_ID} existiert bereits. Andere ID waehlen oder loeschen:"
    echo "  pct stop ${LXC_ID} && pct destroy ${LXC_ID}" >&2
    exit 1
fi

# ── Template ──────────────────────────────────────────────────────────
msg_step "Template sicherstellen"
if ! pveam list "${TEMPLATE_STORAGE}" 2>/dev/null | grep -q "${TEMPLATE_NAME}"; then
    msg_info "Lade Template ${TEMPLATE_NAME} herunter..."
    pveam update
    pveam download "${TEMPLATE_STORAGE}" "${TEMPLATE_NAME}"
else
    msg_ok "Template bereits vorhanden."
fi
TEMPLATE_PATH="${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE_NAME}"

# ── LXC erstellen ─────────────────────────────────────────────────────
msg_step "LXC ${LXC_ID} erstellen"
PASSWORD="$(openssl rand -base64 18)"

PCT_OPTS=(
    "${LXC_ID}" "${TEMPLATE_PATH}"
    --hostname "${LXC_HOSTNAME}"
    --cores "${LXC_CORES}"
    --memory "${LXC_MEMORY}"
    --swap "${LXC_SWAP}"
    --rootfs "${LXC_STORAGE}:${LXC_DISK}"
    --net0 "name=eth0,bridge=${LXC_BRIDGE},ip=${LXC_IP},gw=${LXC_GW}"
    --features "nesting=1"
    --onboot 1
    --unprivileged 1
    --ostype debian
    --password "${PASSWORD}"
)
if [[ -f "${SSH_KEY_FILE}" ]]; then
    msg_info "SSH-Key gefunden: ${SSH_KEY_FILE}"
    PCT_OPTS+=(--ssh-public-keys "${SSH_KEY_FILE}")
else
    msg_warn "Kein SSH-Key unter ${SSH_KEY_FILE} — Login nur per Passwort."
    [[ $UNATTENDED -eq 0 ]] && read -rp "Trotzdem fortfahren? [j/N] " ok \
        && [[ "$ok" =~ ^j ]] || { msg_warn "Abgebrochen. ssh-keygen + ssh-copy-id root@<proxmox>."; exit 0; }
fi

pct create "${PCT_OPTS[@]}"
msg_ok "LXC ${LXC_ID} erstellt. Passwort: ${PASSWORD}"

# ── Starten + Netz warten ─────────────────────────────────────────────
msg_step "LXC starten"
pct start "${LXC_ID}"

LXC_IP_PLAIN="${LXC_IP%/*}"
msg_info "Warte auf Netzwerk in ${LXC_IP_PLAIN}..."
for i in $(seq 1 30); do
    if pct exec "${LXC_ID}" -- ping -c 1 -W 1 8.8.8.8 &>/dev/null; then
        msg_ok "Netzwerk nach ${i}*2s verfuegbar."
        break
    fi
    sleep 2
    if [[ $i -eq 30 ]]; then
        msg_err "LXC hat nach 60s kein Netzwerk. Pruefen: pct enter ${LXC_ID} ; ip a"
        exit 1
    fi
done

# ── Repo klonen ───────────────────────────────────────────────────────
msg_step "Repo klonen"
pct exec "${LXC_ID}" -- bash -c "
    apt-get update
    apt-get install -y --no-install-recommends git ca-certificates
    git clone --branch ${BRANCH} ${REMOTE} /opt/trafficcontrol/src
"
msg_ok "Repo geklont nach /opt/trafficcontrol/src"

# ── Setup-Schritt ─────────────────────────────────────────────────────
if [[ $RUN_SETUP -eq 1 || ( $UNATTENDED -eq 0 ) ]]; then
    if [[ $UNATTENDED -eq 1 ]]; then
        do_setup=1
    else
        read -rp "setup.sh jetzt ausfuehren? [j/N] " do_setup_input
        [[ "$do_setup_input" =~ ^j ]] && do_setup=1 || do_setup=0
    fi
fi

if [[ "${do_setup:-0}" -eq 1 ]]; then
    msg_step "setup.sh ausfuehren"
    pct exec "${LXC_ID}" -- bash -c "cd /opt/trafficcontrol/src/lxc && bash setup.sh"
    msg_ok "setup.sh fertig."
fi

# ── Abschluss ─────────────────────────────────────────────────────────
LXC_IP_PLAIN="${LXC_IP%/*}"
cat <<BANNER

${GN}============================================${CLR}
${GN}  LXC ${LXC_ID} (${LXC_IP_PLAIN}) ist startklar.${CLR}
${GN}============================================${CLR}

Naechste Schritte:

  pct enter ${LXC_ID}                                # in den LXC wechseln
  cd /opt/trafficcontrol/src
  cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e . && cd ..
  cd worker  && python3.12 -m venv .venv && .venv/bin/pip install -e . && cd ..
  cd frontend && npm install && npm run build && cd ..

  # .env mit Passwoertern anlegen
  sudo cp lxc/.env.production /opt/trafficcontrol/.env
  sudo nano /opt/trafficcontrol/.env

  # Services starten
  sudo cp lxc/systemd/*.service lxc/systemd/*.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo cp lxc/nginx.conf /etc/nginx/sites-available/trafficcontrol
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo ln -s /etc/nginx/sites-available/trafficcontrol /etc/nginx/sites-enabled/
  sudo systemctl enable --now postgresql redis-server nginx
  sudo systemctl enable --now traffic-backend
  sudo systemctl enable --now traffic-worker@1 traffic-worker@2 traffic-worker@3
  sudo systemctl enable --now traffic-cleanup.timer

  # Browser:  http://${LXC_IP_PLAIN}/

BANNER
