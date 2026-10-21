#!/usr/bin/env bash
set -euo pipefail

image_name="${IMAGE_NAME:-open-models/cuda-contract:lesson03}"
docker image inspect "$image_name" \
  --format 'image={{index .RepoTags 0}}
id={{.Id}}
created={{.Created}}
architecture={{.Architecture}}
os={{.Os}}
repo_digests={{json .RepoDigests}}
entrypoint={{json .Config.Entrypoint}}
user={{json .Config.User}}'
