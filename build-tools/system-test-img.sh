#!/bin/bash
# builds docker image with top of tree CCCL using build-tools in repo using CCCL
# for use in system tests within the repo using CCCL
# local usage example:
# `./build-tools/system-test-img.sh F5Networks/k8s-bigip-ctlr 3609340 "make prod" f5networksdevel f5devcentral/f5-cccl.git@83d7a311767ea8ca47e144233c4697fce0a3a2bd`

set -ex

USER_REPO=$1
SHA=$2
BUILD_CMD=$3
DOCKER_NAMESPACE=$4
EDITABLE_REQ=$5

REPO=$(echo $USER_REPO | cut -d "/" -f 2)

if [ \
    "$USER_REPO" == "" -o \
    "$SHA" == "" -o \
    "$BUILD_CMD" == "" -o \
    "$DOCKER_NAMESPACE" == "" \
    ]; then
    echo "[ERROR:] repo, sha, build command & docker namespace required"
    false
fi

# in travis, fail f5devcentral commits that cannot push to docker
# warn and skip docker if on fork

if [ "$TRAVIS" ]; then
  if [ "$DOCKER_P" == "" -o "$DOCKER_U" == "" -o $DOCKER_NAMESPACE == "" ]; then
    echo "[INFO] DOCKER_U, DOCKER_P, or DOCKER_NAMESPACE vars absent from travis-ci."
    if [ "$TRAVIS_REPO_SLUG" == "f5devcentral/f5-cccl" ]; then
      echo "[ERROR] Docker push for f5devcentral will fail. Contact repo admin."
      false
    else
      echo "[INFO] Not an 'f5devcentral' commit, docker optional."
      echo "[INFO] Add DOCKER_U, DOCKER_P, and DOCKER_NAMESPACE to travis-ci to push to DockerHub."
    fi
  else
    docker login -u="$DOCKER_U" -p="$DOCKER_P"
    EDITABLE_REQ="$TRAVIS_REPO_SLUG.git@$TRAVIS_COMMIT"
    DOCKER_READY="true"
  fi
else
  if [ "$EDITABLE_REQ" == "" ]; then
    echo "[ERROR] Specify an editable requirement for pip of the form <user>/f5-cccl.git@<sha>"
    false
  fi
  TRAVIS_COMMIT=$(echo $EDITABLE_REQ | cut -d "@" -f 2)
  TRAVIS_BUILD_ID=$(date +%Y%m%d-%H%M)
  TRAVIS_BUILD_NUMBER="local"
  DOCKER_READY="true"
fi

if [ "$DOCKER_READY" ]; then
  git clone https://github.com/$USER_REPO.git
  cd $REPO
  git checkout -b cccl-systest $SHA
  find . -name "*requirements.txt" | xargs sed -i -e 's|f5devcentral/f5-cccl\.git@.*#|'"$EDITABLE_REQ"'#|'
  export IMG_TAG="${DOCKER_NAMESPACE}/cccl:$REPO-${TRAVIS_COMMIT}"
  $BUILD_CMD
  docker tag "$IMG_TAG" "$DOCKER_NAMESPACE/cccl:$REPO"
  docker tag "$IMG_TAG" "$DOCKER_NAMESPACE/cccl:$REPO-n-$TRAVIS_BUILD_NUMBER-id-$TRAVIS_BUILD_ID"
  docker push "$IMG_TAG"
  docker push "$DOCKER_NAMESPACE/cccl:$REPO"
  docker push "$DOCKER_NAMESPACE/cccl:$REPO-n-$TRAVIS_BUILD_NUMBER-id-$TRAVIS_BUILD_ID"
fi
