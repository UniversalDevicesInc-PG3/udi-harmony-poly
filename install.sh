#!/usr/bin/env bash
pip3 install -r requirements.txt --user

if [ ! -f profile.zip ]; then
    echo "Creating default profile.zip"
    rm -rf profile.zip
    cp profile_default.zip profile.zip
else
    echo "profile.zip already exists, not replacing"
fi
