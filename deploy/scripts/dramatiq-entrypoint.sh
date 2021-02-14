#!/bin/bash

delay=1
while true; do
  if test $HELIX_ENVIRONMENT = "development"; then
      $@
  else
      # Production
      python manage.py rundramatiq
  fi
  if [ $? -eq 3 ]; then
    echo "Dramatiq connection error encountered on startup. Retrying in $delay second(s)..."
    sleep $delay
    delay=$((delay * 2))
  else
    exit $?
  fi
done
