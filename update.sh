#!/bin/bash 

commit=$(git rev-parse --short HEAD)

sed -i "s/CWS_LIB_COMMIT_ID=.*/CWS_LIB_COMMIT_ID=${commit}/g"  ./profile.d/00_vars.sh
