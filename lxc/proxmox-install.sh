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
LXC_IP="dhcp"           # Default: DHCP, mit --ip CIDR ueberschreibbar
LXC_GW=""               # nur bei statischer IP noetig
LXC_STORAGE=""          # wird automatisch erkannt (local-lvm oder local-zfs)
TEMPLATE_STORAGE="local"
REMOTE="https://github.com/achilleusGER/ctc-camera-traffic-control.git"
BRANCH="main"
UNATTENDED=0
RUN_SETUP=0
RUN_DEPLOY=0
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
  --ip CIDR|dhcp     IP/Maske oder 'dhcp' (default: ${LXC_IP})
  --gw IP            Gateway   (nur bei statischer IP; default: ${LXC_GW:-n/a})
  --bridge NAME      Linux-Bridge  (default: ${LXC_BRIDGE})
  --cores N          CPU-Kerne  (default: ${LXC_CORES})
  --memory MB        RAM in MB   (default: ${LXC_MEMORY})
  --disk GB          Disk in GB  (default: ${LXC_DISK})
  --storage NAME     Storage fuer RootFS (default: ${LXC_STORAGE})
  --ssh-key FILE     Pfad zu authorized_keys (default: ${SSH_KEY_FILE})
  --unattended       Keine Rueckfragen
  --run-setup        Nach pct create sofort setup.sh im LXC ausfuehren
  --deploy           Nach setup.sh automatisch Backend+Worker+Frontend installieren,
                     .env + Services + nginx einrichten, Services starten
                     (setzt --run-setup implizit voraus)
  --remote URL       Git-Remote (default: ${REMOTE})
  --branch NAME      Git-Branch (default: ${BRANCH})
  --help             Diese Hilfe

${BOLD}Beispiele:${CLR}
  $0 --id 240                                      # Standard (DHCP)
  $0 --id 241 --ip 10.10.1.251/24 --gw 10.10.1.1   # statische IP
  $0 --id 240 --unattended --run-setup             # CI/Automation
  $0 --id 240 --unattended --deploy                # Komplett-Setup inkl. App-Deploy

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
        --deploy)    RUN_DEPLOY=1; shift;;
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

# ── Storage automatisch erkennen ──────────────────────────────────────
# Default-Storage auf Proxmox variiert: 'local-lvm' (LVM-Install) oder
# 'local-zfs' (ZFS-Install). Wir nehmen den ersten Storage mit Content 'rootdir',
# der NICHT 'local' (das ist per Default fuer ISO/Template, nicht fuer Disks).
if [[ -z "${LXC_STORAGE}" ]]; then
    LXC_STORAGE=$(
        pvesm status --content rootdir 2>/dev/null \
            | awk 'NR>1 && $1 != "local" && $1 != "local (pmxcfs)" {print $1; exit}'
    )
    if [[ -z "${LXC_STORAGE}" ]]; then
        # Fallback: erstes Storage mit 'rootdir' oder 'images' Content
        LXC_STORAGE=$(
            pvesm status 2>/dev/null \
                | awk 'NR>1 && ($2 ~ /rootdir|images/) {print $1; exit}'
        )
    fi
    if [[ -z "${LXC_STORAGE}" ]]; then
        msg_err "Konnte keinen Root-Storage finden."
        msg_err "Pruefe: pvesm status ; manuelles --storage <name> setzen"
        exit 1
    fi
fi
msg_info "Verwende Root-Storage: ${LXC_STORAGE}"

# ── Template zuerst erkennen (für die Zusammenfassung) ─────────────────
# Hartcodierte Namen veralten (z. B. 12.2 → 12.7 → 12.12); die Suche ist robust.
TEMPLATE_NAME=$(
    pveam available --section system 2>/dev/null \
        | awk '/debian-12-standard_/ {print $2}' \
        | sort -V \
        | tail -1
)
if [[ -z "${TEMPLATE_NAME}" ]]; then
    msg_err "Kein Debian-12-Standard-Template auf pveam verfuegbar."
    msg_err "Pruefe: pveam update ; pveam available --section system | grep debian-12"
    exit 1
fi

msg_step "Zusammenfassung"
cat <<EOF
  LXC-ID:       ${LXC_ID}
  Hostname:     ${LXC_HOSTNAME}
  CPU/RAM/Disk: ${LXC_CORES} Kerne / ${LXC_MEMORY} MB / ${LXC_DISK} GB
  Netz:         ${LXC_IP} via ${LXC_BRIDGE}${LXC_GW:+ (GW ${LXC_GW})}
  Storage:      ${LXC_STORAGE}
  Template:     ${TEMPLATE_NAME} (wird heruntergeladen falls noetig)
  Remote:       ${REMOTE}@${BRANCH}
  Unattended:   ${UNATTENDED}
  Run-Setup:    ${RUN_SETUP}
  Deploy:       ${RUN_DEPLOY}
EOF
echo

if [[ $UNATTENDED -eq 0 ]]; then
    read -rp "Mit diesen Werten fortfahren? [j/N] " ok
    [[ "$ok" =~ ^j ]] || { msg_warn "Abgebrochen."; exit 0; }
fi

# --deploy setzt --run-setup implizit voraus
[[ ${RUN_DEPLOY} -eq 1 ]] && RUN_SETUP=1
if pct status "${LXC_ID}" &>/dev/null; then
    msg_err "LXC ${LXC_ID} existiert bereits. Andere ID waehlen oder loeschen:"
    echo "  pct stop ${LXC_ID} && pct destroy ${LXC_ID}" >&2
    exit 1
fi

# ── Template sicherstellen ───────────────────────────────────────────
msg_step "Template sicherstellen"
if ! pveam list "${TEMPLATE_STORAGE}" 2>/dev/null | grep -q "${TEMPLATE_NAME}"; then
    msg_info "Lade Template ${TEMPLATE_NAME} herunter (kann 1-2 Min dauern)..."
    pveam download "${TEMPLATE_STORAGE}" "${TEMPLATE_NAME}" \
        || { msg_err "pveam download fehlgeschlagen."; exit 1; }
else
    msg_ok "Template bereits lokal vorhanden."
fi
TEMPLATE_PATH="${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE_NAME}"

# ── LXC erstellen ─────────────────────────────────────────────────────
msg_step "LXC ${LXC_ID} erstellen"
PASSWORD="$(openssl rand -base64 18)"

# Netz-Konfig: DHCP oder statische IP
if [[ "${LXC_IP,,}" == "dhcp" ]]; then
    NET0_OPT="name=eth0,bridge=${LXC_BRIDGE},ip=dhcp"
    msg_info "Netz: DHCP"
else
    if [[ -z "${LXC_GW}" ]]; then
        msg_err "Statische IP (${LXC_IP}) braucht --gw. Beispiel: --gw 10.10.1.1"
        exit 1
    fi
    NET0_OPT="name=eth0,bridge=${LXC_BRIDGE},ip=${LXC_IP},gw=${LXC_GW}"
    msg_info "Netz: ${LXC_IP} via GW ${LXC_GW}"
fi

PCT_OPTS=(
    "${LXC_ID}" "${TEMPLATE_PATH}"
    --hostname "${LXC_HOSTNAME}"
    --cores "${LXC_CORES}"
    --memory "${LXC_MEMORY}"
    --swap "${LXC_SWAP}"
    --rootfs "${LXC_STORAGE}:${LXC_DISK}"
    --net0 "${NET0_OPT}"
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

# Bei DHCP kennen wir die IP nicht im Voraus -> nach dem Start aus dem LXC auslesen
get_lxc_ip() {
    pct exec "${LXC_ID}" -- bash -c "
        ip -4 -o addr show dev eth0 2>/dev/null | awk '{print \$4}' | head -1
    " 2>/dev/null | tr -d '\n' || true
}

if [[ "${LXC_IP,,}" == "dhcp" ]]; then
    msg_info "Warte auf DHCP im LXC..."
    LXC_IP_PLAIN=""
    for i in $(seq 1 30); do
        # ip -4 -o addr gibt '10.10.1.101/23' zurueck; Maske abschneiden
        LXC_IP_PLAIN=$(get_lxc_ip | cut -d/ -f1)
        if [[ -n "${LXC_IP_PLAIN}" ]] && pct exec "${LXC_ID}" -- ping -c 1 -W 1 8.8.8.8 &>/dev/null; then
            msg_ok "LXC hat DHCP-IP: ${LXC_IP_PLAIN} (nach ${i}*2s)"
            break
        fi
        sleep 2
        if [[ $i -eq 30 ]]; then
            msg_err "LXC hat nach 60s keine DHCP-IP. Pruefen: pct enter ${LXC_ID} ; ip a"
            exit 1
        fi
    done
else
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
fi

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

# LXC_IP_PLAIN: bei DHCP haben wir oben schon die echte IP ermittelt,
# bei statischer IP ist es die Konfig ohne /Mask.
if [[ "${LXC_IP,,}" == "dhcp" ]]; then
    DISPLAY_IP="${LXC_IP_PLAIN:-<wird-via-DHCP-vergeben>}"
else
    DISPLAY_IP="${LXC_IP%/*}"
fi

# ── App-Deploy (optional) ─────────────────────────────────────────────
# Macht alles, was bisher per Hand im LXC noetig war:
#   - Backend + Worker: venv, pip install -e, alembic upgrade head
#   - Frontend: npm install, npm run build
#   - .env aus Template kopieren (POSTGRES_PASSWORD bleibt erstmal 'traffic'!)
#   - systemd-Units installieren
#   - nginx-site einrichten
#   - Services starten
if [[ ${RUN_DEPLOY} -eq 1 ]]; then
    msg_step "App-Deploy im LXC"

    # 1) pip + npm + alembic
    msg_info "Backend: venv + pip install -e + alembic upgrade head"
    pct exec "${LXC_ID}" -- bash -c "
        set -euo pipefail
        cd /opt/trafficcontrol/src/backend
        python3 -m venv .venv
        .venv/bin/pip install --quiet --upgrade pip
        .venv/bin/pip install --quiet -e .
        .venv/bin/alembic upgrade head
    "

    msg_info "Worker: venv + pip install -e"
    pct exec "${LXC_ID}" -- bash -c "
        set -euo pipefail
        cd /opt/trafficcontrol/src/worker
        python3 -m venv .venv
        .venv/bin/pip install --quiet --upgrade pip
        .venv/bin/pip install --quiet -e .
    "

    # 2) Frontend (kann 1-2 Min dauern bei npm install)
    msg_info "Frontend: npm install + build (kann 1-2 Min dauern)..."
    pct exec "${LXC_ID}" -- bash -c "
        set -euo pipefail
        cd /opt/trafficcontrol/src/frontend
        npm install --no-audit --no-fund
        npm run build
    "

    # 3) .env anlegen (mit Default-Passwörtern, vor Prod unbedingt aendern)
    msg_info "Lege /opt/trafficcontrol/.env mit Default-Passwoertern an (VOR PROD AENDERN!)"
    pct exec "${LXC_ID}" -- bash -c "
        cp /opt/trafficcontrol/src/lxc/.env.production /opt/trafficcontrol/.env
        chown traffic:traffic /opt/trafficcontrol/.env
        chmod 600 /opt/trafficcontrol/.env
    "

    # 4) systemd-Services
    msg_info "systemd-Services installieren + aktivieren"
    pct exec "${LXC_ID}" -- bash -c "
        set -euo pipefail
        cp /opt/trafficcontrol/src/lxc/systemd/*.service /opt/trafficcontrol/src/lxc/systemd/*.timer /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable --now postgresql redis-server nginx
        systemctl enable --now traffic-backend
        systemctl enable --now traffic-worker@1
        systemctl enable --now traffic-cleanup.timer
    "

    # 5) nginx
    msg_info "nginx-Konfiguration einrichten"
    pct exec "${LXC_ID}" -- bash -c "
        set -euo pipefail
        cp /opt/trafficcontrol/src/lxc/nginx.conf /etc/nginx/sites-available/trafficcontrol
        rm -f /etc/nginx/sites-enabled/default
        ln -sf /etc/nginx/sites-available/trafficcontrol /etc/nginx/sites-enabled/
        nginx -t
        systemctl reload nginx
    "

    msg_ok "App-Deploy fertig. Browser: http://${DISPLAY_IP}/"
fi

# ── Abschluss ─────────────────────────────────────────────────────────
if [[ ${RUN_DEPLOY} -eq 1 ]]; then
    cat <<BANNER

${GN}============================================${CLR}
${GN}  LXC ${LXC_ID} (${DISPLAY_IP}) ist startklar.${CLR}
${GN}  App ist deployt und laeuft.${CLR}
${GN}============================================${CLR}

Browser:   http://${DISPLAY_IP}/
SSH (root): ssh root@${DISPLAY_IP}   (oder: pct enter ${LXC_ID})

Wichtige Defaults (VOR PROD AENDERN):
  - POSTGRES_PASSWORD = 'traffic'   (in /opt/trafficcontrol/.env)
  - DB-User/Db = traffic / traffic
  - HTTPS nicht eingerichtet (LAN-Tool laut Q5)
  - Beweisfoto-Retention: 30 Tage, taeglich 03:00 (cleanup-timer)

Logs:    journalctl -u traffic-backend -f
         journalctl -u traffic-worker@1 -f

BANNER
else
    cat <<BANNER

${GN}============================================${CLR}
${GN}  LXC ${LXC_ID} (${DISPLAY_IP}) ist startklar.${CLR}
${GN}============================================${CLR}

Naechste Schritte (falls --deploy nicht genutzt):

  pct enter ${LXC_ID}
  cd /opt/trafficcontrol/src
  bash lxc/deploy-app.sh          # pip + npm + alembic + restart

Oder mit dem Installer neu starten und --deploy nutzen:
  bash proxmox-install.sh --id ${LXC_ID} --unattended --deploy

BANNER
fi
