#!/usr/bin/env bash
# scripts/check_env.sh — pre-flight check for new developers.
# Run before `docker compose up` to verify prerequisites.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }
warn() { echo -e "${YELLOW}!${NC} $1"; }

FAILED=0

echo "Bolkhata — environment pre-flight check"
echo "========================================"

# Docker
if docker info &>/dev/null; then
  pass "Docker running"
else
  fail "Docker is not running. Start Docker Desktop."
fi

# Docker Compose
if docker compose version &>/dev/null; then
  pass "docker compose available"
else
  fail "docker compose not found (need v2)"
fi

# uv
if command -v uv &>/dev/null; then
  pass "uv $(uv --version | head -1)"
else
  warn "uv not found — only needed for local backend dev (not required for Docker)"
fi

# Node
NODE_VER=$(node --version 2>/dev/null || echo "none")
if [[ "$NODE_VER" != "none" ]]; then
  pass "node $NODE_VER"
else
  warn "node not found — only needed for local frontend dev (not required for Docker)"
fi

# .env file
if [[ -f ".env" ]]; then
  pass ".env file exists"
else
  fail ".env not found. Run: cp .env.example .env"
fi

echo "========================================"
if [[ $FAILED -eq 0 ]]; then
  echo -e "${GREEN}All checks passed. Run: docker compose up --build${NC}"
else
  echo -e "${RED}Fix the above issues before continuing.${NC}"
  exit 1
fi
