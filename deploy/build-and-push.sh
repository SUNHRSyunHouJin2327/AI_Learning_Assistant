#!/usr/bin/env bash
# Run on your own computer: build a linux image matching the ECS CPU and push it to ACR.
# Usage: ACR_REGISTRY=crpi-xxxx.cn-hangzhou.personal.cr.aliyuncs.com \
#        ACR_NAMESPACE=your-namespace ECS_ARCH=amd64 bash deploy/build-and-push.sh
set -euo pipefail
: "${ACR_REGISTRY:?set ACR_REGISTRY (shown on the ACR repository page)}"
: "${ACR_NAMESPACE:?set ACR_NAMESPACE}"
ACR_REPO="${ACR_REPO:-ai-learning-assistant}"
TAG="${TAG:-v1}"
ECS_ARCH="${ECS_ARCH:-amd64}"   # x86_64 on ECS -> amd64; aarch64 -> arm64
IMAGE="${ACR_REGISTRY}/${ACR_NAMESPACE}/${ACR_REPO}:${TAG}"

cd "$(dirname "$0")/.."
docker login "${ACR_REGISTRY}"
docker buildx build --platform "linux/${ECS_ARCH}" --provenance=false --sbom=false -t "${IMAGE}" --push .
echo "Pushed ${IMAGE}"
