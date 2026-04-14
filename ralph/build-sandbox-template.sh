#!/usr/bin/env bash
set -euo pipefail

# build-sandbox-template.sh -- Build the `dailyriff-dev:v1` sandbox template.
#
# Starts from the stock `claude` sandbox template and layers on the dev tools
# DailyRiff needs (node 22, pnpm 9, supabase CLI). uv is already in the base.
# Saves the result as a reusable template so afk-ralph.sh can spin up fast.
#
# Supabase itself runs on the HOST (not inside the sandbox) — docker-in-docker
# via socket passthrough can't satisfy supabase's bind-mount requirements.
# afk-ralph.sh handles host-side supabase orchestration and env injection.

REPO_ROOT="$(git rev-parse --show-toplevel)"
BUILD_SANDBOX="dailyriff-build"
TEMPLATE_TAG="dailyriff-dev:v1"

cd "$REPO_ROOT"

# Remove any stale build sandbox
docker sandbox rm "$BUILD_SANDBOX" 2>/dev/null || true

echo "Creating base sandbox from stock 'claude' template..."
docker sandbox create --name "$BUILD_SANDBOX" claude "$REPO_ROOT"

echo ""
echo "Upgrading node 20 -> 22 via NodeSource apt repo..."
docker sandbox exec "$BUILD_SANDBOX" bash -c '
  set -e
  sudo apt-get remove -y nodejs >/dev/null 2>&1 || true
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null 2>&1
  sudo apt-get install -y nodejs >/dev/null 2>&1
  node --version
'

echo ""
echo "Installing pnpm 9..."
docker sandbox exec "$BUILD_SANDBOX" bash -c 'sudo npm install -g pnpm@9 >/dev/null 2>&1 && pnpm --version'

echo ""
echo "Installing supabase CLI..."
docker sandbox exec "$BUILD_SANDBOX" bash -c '
  set -e
  curl -sL -o /tmp/supabase.tar.gz \
    https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz
  cd /tmp && tar -xzf supabase.tar.gz
  sudo mv supabase /usr/local/bin/
  supabase --version
'

echo ""
echo "Saving template as ${TEMPLATE_TAG}..."
docker sandbox save "$BUILD_SANDBOX" "$TEMPLATE_TAG"

echo ""
echo "Cleaning up build sandbox..."
docker sandbox rm "$BUILD_SANDBOX"

echo ""
echo "Done. afk-ralph.sh will automatically pick up ${TEMPLATE_TAG} on next run."
