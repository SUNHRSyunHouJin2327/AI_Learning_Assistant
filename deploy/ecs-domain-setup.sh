#!/usr/bin/env bash
# Run on the ECS server after the DNS A record resolves to this server.
# Usage: DOMAIN=ai.yourdomain.com AUTH_USER=student bash ecs-domain-setup.sh
set -euo pipefail
: "${DOMAIN:?set DOMAIN}"; AUTH_USER="${AUTH_USER:-student}"
cd "$(dirname "$0")"
sudo apt-get update
sudo apt-get install -y nginx apache2-utils certbot python3-certbot-nginx
sudo htpasswd -c /etc/nginx/.htpasswd-ai-agent "$AUTH_USER"   # prompts for password
T="$(openssl rand -hex 32)"
printf 'map_hash_bucket_size 128;\nmap $cookie_aila_gate $aila_gate_ok {\n    default 0;\n    "%s" 1;\n}\n' "$T" | sudo tee /etc/nginx/conf.d/aila-gate.conf >/dev/null
printf 'add_header Set-Cookie "aila_gate=%s; Path=/; Max-Age=604800; Secure; HttpOnly; SameSite=Lax" always;\n' "$T" | sudo tee /etc/nginx/snippets/aila-gate-cookie.conf >/dev/null
sudo chmod 600 /etc/nginx/conf.d/aila-gate.conf /etc/nginx/snippets/aila-gate-cookie.conf
sed "s/ai.example.com/${DOMAIN}/" nginx-ai-agent.conf | sudo tee /etc/nginx/sites-available/ai-agent >/dev/null
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/ai-agent /etc/nginx/sites-enabled/ai-agent
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d "$DOMAIN" --redirect   # asks you to accept the Let's Encrypt agreement
echo "--- checks ---"
echo -n "No credentials at gate (expect 401): "; curl -s -o /dev/null -w '%{http_code}\n' "https://${DOMAIN}/__gate"
echo "With credentials at gate (expect 302 to /ui/ with a cookie):"; curl -s -o /dev/null -w '%{http_code}\n' -u "$AUTH_USER" "https://${DOMAIN}/__gate"
