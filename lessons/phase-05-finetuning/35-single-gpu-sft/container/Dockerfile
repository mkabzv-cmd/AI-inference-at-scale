ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /opt/course
COPY lessons/phase-05-finetuning/35-single-gpu-sft/requirements-train.txt /tmp/
RUN python -m pip install --no-cache-dir -r /tmp/requirements-train.txt

COPY lessons/phase-05-finetuning/35-single-gpu-sft /opt/course/lesson35
COPY lessons/phase-05-finetuning/33-dataset-engineering-chat-templates /opt/course/lesson33

ARG MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct
ARG MODEL_REVISION=7ae557604adf67be50417f59c2c2f167def9a775
RUN python /opt/course/lesson35/src/cache_model.py \
    --repository "${MODEL_ID}" \
    --revision "${MODEL_REVISION}" \
    --cache-dir /opt/model-cache

RUN useradd --create-home --uid 10001 learner && \
    chown -R learner:learner /opt/model-cache /opt/course
USER 10001
ENV HF_HOME=/home/learner/.cache/huggingface \
    HF_HUB_CACHE=/opt/model-cache \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/opt/course/lesson35/src/train_transformers.py"]
