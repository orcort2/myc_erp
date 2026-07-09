#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$PROJECT_ROOT" || exit 1

git status --short
