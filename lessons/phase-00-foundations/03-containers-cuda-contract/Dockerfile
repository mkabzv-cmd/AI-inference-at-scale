ARG BASE_IMAGE=pytorch/pytorch@sha256:c8268a92a69bd500f8be0e665b2630ee006dadaf7bfbc24249141b15ff622755
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="Lesson 03 CUDA contract probe"
LABEL org.opencontainers.image.description="Educational GPU visibility probe"

WORKDIR /app
COPY src/gpu_probe.py /app/gpu_probe.py

RUN groupadd --gid 10001 learner \
    && useradd --uid 10001 --gid 10001 --no-create-home learner \
    && mkdir -p /results \
    && chown 10001:10001 /results

USER 10001:10001
ENTRYPOINT ["python", "/app/gpu_probe.py"]
