ARG BASE_IMAGE=pytorch/pytorch@sha256:c8268a92a69bd500f8be0e665b2630ee006dadaf7bfbc24249141b15ff622755
FROM ${BASE_IMAGE}

ARG MODEL_ID=sshleifer/tiny-gpt2
ARG MODEL_REVISION=5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be

LABEL org.opencontainers.image.title="Lesson 04 tiny GPU model server"
LABEL course.lesson="04"

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt \
    && python -m pip check
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='${MODEL_ID}', revision='${MODEL_REVISION}', local_dir='/opt/model', allow_patterns=['config.json','generation_config.json','merges.txt','model.safetensors','pytorch_model.bin','special_tokens_map.json','tokenizer.json','tokenizer_config.json','vocab.json'])"

COPY app/server.py /app/server.py
RUN groupadd --gid 10001 learner \
    && useradd --uid 10001 --gid 10001 --no-create-home learner \
    && chown -R 10001:10001 /app /opt/model

ENV MODEL_PATH=/opt/model \
    MODEL_ID=${MODEL_ID} \
    MODEL_REVISION=${MODEL_REVISION} \
    BIND_HOST=0.0.0.0 \
    REQUIRE_CUDA=true \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    HOME=/tmp

EXPOSE 8080
USER 10001:10001
ENTRYPOINT ["python", "/app/server.py"]
