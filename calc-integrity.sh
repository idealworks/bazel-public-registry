#!/bin/bash

if [ "$#" != 1 ]; then
  echo "Usage ${0} <filename>"
  exit 1
fi

openssl dgst -sha256 -binary ${1} | openssl base64 -A | sed 's/^/sha256-/'
echo ""
