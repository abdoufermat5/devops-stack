# Gitea Actions Runner

Le runner exécute les jobs CI définis dans `.gitea/workflows/`. Il tourne directement sur le host (pas dans un container) pour avoir accès au daemon Docker local.

## Pourquoi sur le host et pas en container ?

Le job CI doit builder et pusher une image Docker vers `localhost:5000`. Si le runner tourne dans un container Docker, `localhost` pointe vers le container lui-même — pas vers le registry sur le host. En tournant directement sur le host, tout est sur le même réseau et le même daemon Docker.

## Installation

```bash
chmod +x runner/install-runner.sh

# Récupère un token sur :
# http://<IP>:30300/<user>/<repo>/settings/actions/runners → "Create new runner"

./runner/install-runner.sh <GITEA_IP> <TOKEN>
```

## Commandes utiles

```bash
# Voir les logs en temps réel
sudo journalctl -u act-runner -f

# Statut du service
sudo systemctl status act-runner

# Redémarrer
sudo systemctl restart act-runner

# Arrêter (désactive le CI)
sudo systemctl stop act-runner
```

## Mise à jour du runner

```bash
sudo systemctl stop act-runner
curl -Lo ~/act_runner \
  https://dl.gitea.com/act_runner/latest/act_runner-linux-amd64
chmod +x ~/act_runner
sudo systemctl start act-runner
```
