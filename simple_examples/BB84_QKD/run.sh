#!/usr/bin/env sh

python alice.py $1 &
python bob.py $1 &
python eve.py $1 &