#!/usr/bin/env bash
# Run on the ECS server after the DNS A record resolves to this server.
# Usage: DOMAIN=ai.yourdomain.com AUTH_USER=student bash ecs-domain-setup.sh
set -euo pipefail
: "${DOMAIN:?set DOMAIN}"; AUTH_USER="${AUTH_USER:-student}"
cd "$(dirname "$0")"
sudo apt-get update
sudo apt-get install -y nginx apache2-utils certbot python3-certbot-nginx
sudo htpasswd -c /etc/nginx/.htpasswd-ai-agent "$AUTH_USER"   # prompts for password
sed "s/ai.example.com/${DOMAIN}/" nginx-ai-agent.conf | sudo tee /etc/nginx/sites-available/ai-agent >/dev/null
sudo ln -sf /etc/nginx/sites-available/ai-agent /etc/nginx/sites-enabled/ai-agent
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d "$DOMAIN"
echo "--- checks ---"
echo -n "No credentials (expect 401): "; curl -s -o /dev/null -w '%{http_code}\n' "https://${DOMAIN}/ui/"
echo "With credentials (expect 200):"; curl -s -o /dev/null -w '%{http_code}\n' -u "$AUTH_USER" "https://${DOMAIN}/ui/"
