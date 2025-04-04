#!/bin/bash -e

#
# Simple helper script to tag and push to required docker registry
# Mostly used for alpha deployments
#
# Eg:
# DOCKER_IMAGE=my.local.docker.server/idmc/helix-server ./deploy/scripts/tag_and_push_to_docker_registry.sh

DOCKER_IMAGE=${DOCKER_IMAGE?error}

BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD | sed 's|:|-|' | tr '[:upper:]' '[:lower:]' | sed 's/\//-/g' | sed 's/_/-/g' | cut -c1-100 | sed 's/-*$//')
GIT_HASH=$(git rev-parse --short HEAD | head -c7)
DOCKER_TAG="$BRANCH_NAME.c$(echo $GIT_HASH)"

set -x

docker compose build celery

docker tag helix/helix-worker:latest $DOCKER_IMAGE:$DOCKER_TAG

docker push $DOCKER_IMAGE:$DOCKER_TAG

echo "Tagged image: $DOCKER_IMAGE:$DOCKER_TAG"
