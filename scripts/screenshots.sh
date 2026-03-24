#!/bin/bash
# Take Jarvis Dashboard screenshots — run from gaming PC WSL
# Usage: bash /mnt/z/home/animesh/projects/jarvis-dashboard/scripts/screenshots.sh

OUT="/mnt/z/tmp/jarvis-screenshots"
BASE="http://192.168.0.2:3000"

mkdir -p "$OUT"
rm -f "$OUT"/*.png

# Desktop (1440x900)
for page in "" system docker torrents media discover files tasks; do
  name="${page:-overview}"
  echo "Desktop: ${name}"
  npx -y playwright screenshot --browser chromium --full-page --viewport-size="1440,900" "${BASE}/${page}" "${OUT}/desktop-${name}.png" 2>/dev/null
done

# Mobile (390x844)
for page in "" system docker torrents media discover files tasks; do
  name="${page:-overview}"
  echo "Mobile: ${name}"
  npx -y playwright screenshot --browser chromium --full-page --viewport-size="390,844" "${BASE}/${page}" "${OUT}/mobile-${name}.png" 2>/dev/null
done

echo "Done! Screenshots in ${OUT}"
echo "On server: ls /tmp/jarvis-screenshots/"
