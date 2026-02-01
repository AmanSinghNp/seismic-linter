#!/bin/bash
set -e

# Construct optional arguments based on Action inputs (ENV vars)
EXTRA_ARGS=""

if [ "$INPUT_FAIL_ON_ERROR" = "false" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --no-fail-on-error"
fi
if [ -n "$INPUT_IGNORE" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --ignore $INPUT_IGNORE"
fi
if [ -n "$INPUT_FAIL_ON" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --fail-on $INPUT_FAIL_ON"
fi

# Pass all arguments from action.yml args + our extra args
exec seismic-linter "$@" $EXTRA_ARGS
