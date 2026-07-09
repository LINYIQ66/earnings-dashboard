#!/bin/bash
export SSHPASS='w7(Fsjf[9hptxypz'
HOST="45.32.109.144"
USER="root"
sshpass -e scp -o StrictHostKeyChecking=no ~/earnings-data/docs/earnings_report.html "$USER@$HOST:/var/www/html/earnings.html" 2>&1
echo "SCP_EXIT:$?"
sshpass -e ssh -o StrictHostKeyChecking=no "$USER@$HOST" "cp /var/www/html/earnings.html /root/mcp-server/earnings.html" 2>&1
echo "SSH_EXIT:$?"
