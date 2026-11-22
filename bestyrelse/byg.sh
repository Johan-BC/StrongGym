#!/usr/bin/env bash
# Kopierer "Strong Gym i tal" (styring.html i repo-roden) ind som bestyrelsens forside.
# Køres før hver deploy: ./byg.sh && npx wrangler deploy
set -euo pipefail
cd "$(dirname "$0")"
cp ../styring.html public/bestyrelse/index.html
echo "Bygget: public/bestyrelse/index.html ($(wc -c < public/bestyrelse/index.html) bytes)"
