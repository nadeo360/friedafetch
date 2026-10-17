#!/usr/bin/env bash
# Prepares (and optionally opens) the pull request that adds the iCloud MCP artwork to
# https://github.com/home-assistant/brands so that HACS and the Home Assistant UI show the icon.
#
# Usage:
#   scripts/brands_pr.sh            # fork + clone brands, copy images, commit, push, open PR
#   scripts/brands_pr.sh --dry-run  # only show what would happen
#
# Requires: gh (logged in), git. Run scripts/build_icons.py first if the SVGs changed.
set -euo pipefail
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"
command -v gh >/dev/null || { echo "GitHub CLI 'gh' not found. Install it (brew install gh) and run 'gh auth login'." >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is not logged in. Run 'gh auth login' first." >&2; exit 1; }

DOMAIN="icloud_mcp"
UPSTREAM="home-assistant/brands"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/brands/custom_integrations/$DOMAIN"
WORK="${BRANDS_WORKDIR:-$(mktemp -d)}"
DRY_RUN="${1:-}"

for f in icon.png icon@2x.png logo.png logo@2x.png dark_logo.png dark_logo@2x.png; do
  [ -f "$SRC/$f" ] || { echo "Missing $SRC/$f – run scripts/build_icons.py first" >&2; exit 1; }
done

ME="$(gh api user --jq .login)"
echo "GitHub user: $ME"
echo "Working directory: $WORK"

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "Would fork $UPSTREAM to $ME/brands, copy $SRC to custom_integrations/$DOMAIN and open a PR."
  exit 0
fi

# fork (idempotent) and clone
gh repo fork "$UPSTREAM" --clone=false >/dev/null 2>&1 || true
git clone --depth 1 "https://github.com/$ME/brands.git" "$WORK/brands"
cd "$WORK/brands"
git remote add upstream "https://github.com/$UPSTREAM.git"
git fetch --depth 1 upstream master
git checkout -B "add-$DOMAIN" upstream/master

mkdir -p "custom_integrations/$DOMAIN"
cp "$SRC"/*.png "custom_integrations/$DOMAIN/"
git add "custom_integrations/$DOMAIN"
git -c user.name="$ME" -c user.email="$ME@users.noreply.github.com" commit -q -m "Add $DOMAIN (iCloud MCP)"
git push -u origin "add-$DOMAIN" --force

gh pr create --repo "$UPSTREAM" --head "$ME:add-$DOMAIN" \
  --title "Add icloud_mcp (iCloud MCP)" \
  --body "$(cat <<'BODY'
Adds the brand images for the custom integration **iCloud MCP** (`icloud_mcp`).

- Repository: https://github.com/nadeo360/ha-icloud-mcp
- Integration domain: `icloud_mcp` (HACS custom integration)
- Files: `icon.png` 256×256, `icon@2x.png` 512×512, `logo.png` 605×128, `logo@2x.png` 1210×256, `dark_logo.png`, `dark_logo@2x.png`
- Artwork is original and licensed under MIT; it does not use Apple trademarks or logos.
BODY
)"
echo "Done. Review the pull request in your browser."
