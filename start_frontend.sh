#!/bin/bash
cd /home/rezaahmadkhairuddin/ERIN/apps/desktop
nohup npm run dev > /tmp/vite.log 2>&1 &
sleep 5
curl -s http://localhost:1420/ | head -20