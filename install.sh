#!/usr/bin/env bash

if ! pip3 install -r requirements.txt --user; then
  echo "ERROR: pip3 failed, see above"
  exit 1
fi

echo ""
if [ -e pyharmony ]; then
  echo "Updating pyharmony..."
  git pull pyharmony
else
  git clone https://github.com/jimboca/pyharmony.git
fi

./write_profile.py
