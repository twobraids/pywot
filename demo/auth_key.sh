#!/bin/bash -e

read -p    "Enter      URL: " URL
read -p    "Enter    email: " USERNAME
read -s -p "Enter password: " PASSWORD
echo

curl -H "Content-Type: application/json" \
 -H "Accept: application/json" \
 -X POST -d '{"email": "'${USERNAME}'", "password": "'${PASSWORD}'"}' \
 --insecure --silent \
 ${URL}/login | python3 -c 'import json,sys; print("things_gateway_auth_key={}".format(json.load(sys.stdin)["jwt"]))' > sample_auth.ini
