#!/bin/bash
cd /home/kavia/workspace/code-generation/wiki-to-neo4j-4236-4467/BackendService
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

