#!/usr/bin/env bash
# Hermes-Trafficcontrol — Installer-Wrapper
# Umgeht raw.githubusercontent.com-Cache (5-10 Min) durch direkten Git-Clone.
#
# Verwendung auf Proxmox-Host als root:
#   bash <(curl -fsSL https://raw.githubusercontent.com/achilleusGER/ctc-camera-traffic-control/main/lxc/proxmox-wrapper.sh)
#
# Was es macht:
#   1. Klont das Repo frisch nach /tmp/ctc-installer
#   2. Ruft das echte Installer-Skript mit allen Argumenten auf

set -euo pipefail
REMOTE="https://github.com/achilleusGER/ctc-camera-traffic-control.git"
WORK="/tmp/ctc-installer-$$"

# Clean
rm -rf "${WORK}"
git clone --depth=1 "${REMOTE}" "${WORK}" 2>&1 | sed 's/^/[clone] /'
bash "${WORK}/lxc/proxmox-install.sh" "$@"
RC=$?
rm -rf "${WORK}"
exit ${RC}
