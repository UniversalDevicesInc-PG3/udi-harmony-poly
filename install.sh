#!/usr/bin/env bash

rf=requirements.txt
if [ -f /usr/local/etc/pkg/repos/udi.conf ]; then
  rf=requirements_polisy.txt
fi
echo "Using: $rf"
if ! pip3 install -r $rf --user; then
  echo "ERROR: pip3 failed, see above"
  exit 1
fi

echo ""
if [ -e pyharmony ]; then
  echo "Updating pyharmony..."
  cd pyharmony
  git pull
  cd ..
else
  git clone https://github.com/jimboca/pyharmony.git
fi
