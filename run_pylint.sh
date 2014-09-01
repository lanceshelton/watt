#!/bin/bash

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd $REPO_DIR
python_src=$(git ls-files | grep ".py$")
for src in $python_src
do
    echo $src
    pylint --rcfile=./pylint.rc $src
done
