#!/bin/bash
# -------------------------------------------------------
# install-runner.sh
#
# Installe et enregistre act_runner sur le host.
# À exécuter une seule fois sur la VM.
#
# Usage :
#   chmod +x install-runner.sh
#   ./install-runner.sh <GITEA_IP> <REGISTRATION_TOKEN>
#
# Exemple :
#   ./install-runner.sh 192.168.175.129 ClOEHoZ1PAJH...
#
# Le token se récupère sur :
#   http://<GITEA_IP>:30300/<user>/<repo>/settings/actions/runners
#   → "Create new runner" → copie le token
# -------------------------------------------------------

set -e

GITEA_IP=${1:?"Usage: $0 <GITEA_IP> <TOKEN>"}
TOKEN=${2:?"Usage: $0 <GITEA_IP> <TOKEN>"}
GITEA_URL="http://${GITEA_IP}:30300"
RUNNER_VERSION="0.2.11"
RUNNER_BIN="$HOME/act_runner"
SERVICE_FILE="/etc/systemd/system/act-runner.service"

echo "→ Téléchargement de act_runner v${RUNNER_VERSION}..."
curl -Lo "$RUNNER_BIN" \
  "https://dl.gitea.com/act_runner/${RUNNER_VERSION}/act_runner-${RUNNER_VERSION}-linux-amd64"
chmod +x "$RUNNER_BIN"

echo "→ Enregistrement du runner sur ${GITEA_URL}..."
"$RUNNER_BIN" register \
  --no-interactive \
  --instance "$GITEA_URL" \
  --token "$TOKEN" \
  --name "local-runner" \
  --labels "ubuntu-latest:host"

echo "→ Installation du service systemd..."
# Remplace le nom d'utilisateur par l'utilisateur courant
sed "s/osboxes/$(whoami)/g" "$(dirname "$0")/act-runner.service" \
  | sudo tee "$SERVICE_FILE" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable act-runner
sudo systemctl start act-runner

echo ""
echo "✅ Runner installé et démarré."
echo "   Logs : sudo journalctl -u act-runner -f"
echo "   Status : sudo systemctl status act-runner"
