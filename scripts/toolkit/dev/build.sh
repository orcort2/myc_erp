#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

"$PROJECT_ROOT/scripts/build.sh"
