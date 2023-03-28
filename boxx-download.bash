#!/bin/bash
export BOXX_USER=user-name@email-server.com
export BOXX_PW=something-super-secret

python -u boxx-download.py $@ 2> download.err | tee download.out

