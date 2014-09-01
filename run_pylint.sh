#!/bin/bash

cd watt
pylint --rcfile=../pylint.rc ./*.py ./*/*.py
