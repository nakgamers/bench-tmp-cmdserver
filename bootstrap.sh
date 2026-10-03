#!/bin/bash
# Bootstrap for vast.ai benchmark box: cmd-server + cloudflared fallback.
# Runs as root on boot via vast.ai on-start script. Logs: /tmp/bootstrap.log
set -u
exec > /tmp/bootstrap.log 2>&1
echo "BOOTSTRAP_START $(date -u)"

echo "--- step 1: cmd server ---"
curl -sL --max-time 90 https://raw.githubusercontent.com/nakgamers/bench-tmp-cmdserver/master/cmdserver.py -o /tmp/cs.py
echo "cs.py bytes: $(wc -c < /tmp/cs.py 2>/dev/null || echo MISSING)"
if [ -f /tmp/cs.py ]; then
  pkill -f "cs.py" 2>/dev/null; sleep 1
  nohup python3 /tmp/cs.py >/tmp/cs.log 2>&1 &
  sleep 3
  curl -s --max-time 10 http://127.0.0.1:10200/ping && echo " <- cmd server OK"
fi

echo "--- step 2: cloudflared (fallback ingress) ---"
curl -sL --max-time 180 https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared 2>/dev/null
/usr/local/bin/cloudflared --version 2>&1 | head -1
pkill -f "cloudflared tunnel" 2>/dev/null; sleep 1
nohup /usr/local/bin/cloudflared tunnel --url http://localhost:10200 > /tmp/cf.log 2>&1 &
sleep 25
echo "--- tunnel urls found: ---"
grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cf.log | sort -u | head -3
echo "--- nvidia-smi ---"
nvidia-smi --query-gpu=index,name,memory.total --format=csv 2>&1 | head -5

echo "BOOTSTRAP_DONE $(date -u)"
