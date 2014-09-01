#!/bin/bash

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd $REPO_DIR/watt
python_src=$(git ls-files | grep ".py$")
pylint --rcfile=$REPO_DIR/pylint.rc $python_src
