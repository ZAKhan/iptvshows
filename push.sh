#!/usr/bin/env bash
# =============================================================================
# push.sh — IPTVShows git push helper
# Usage:
#   ./push.sh              — commit all changes and push (prompts for message)
#   ./push.sh "my message" — commit with given message and push
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo -e "${CYAN}"
echo "=================================================="
echo "  IPTVShows — Push to GitHub"
echo "=================================================="
echo -e "${NC}"

# Check we're in a git repo
git rev-parse --git-dir &>/dev/null || error "Not a git repository."

# Get commit message
if [ -n "$1" ]; then
    COMMIT_MSG="$1"
else
    echo -e "  ${YELLOW}Enter commit message:${NC} "
    read -r COMMIT_MSG
    [ -z "$COMMIT_MSG" ] && error "Commit message cannot be empty."
fi

# Check for changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
    echo -e "  ${YELLOW}Nothing to commit, working tree clean.${NC}"
    exit 0
fi

info "Staging all changes..."
git add .
success "Staged"

info "Committing: \"$COMMIT_MSG\""
git commit -m "$COMMIT_MSG"
success "Committed"

info "Pushing to origin/main..."
git push origin main
success "Pushed to github.com:ZAKhan/iptvshows"

echo ""
echo -e "${GREEN}=================================================="
echo "  Done!"
echo -e "==================================================${NC}"
echo ""
