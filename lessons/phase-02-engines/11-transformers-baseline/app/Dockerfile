ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG MODEL_ID="Qwen/Qwen2.5-0.5B-Instruct"
ARG MODEL_REVISION="7ae557604adf67be50417f59c2c2f167def9a775"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface \
    MODEL_ID=${MODEL_ID} \
    MODEL_REVISION=${MODEL_REVISION}

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt \
    && python -m pip freeze --all > /app/dependency-versions.txt

COPY server.py /app/server.py
RUN useradd --create-home --uid 10001 model \
    && mkdir -p /models/huggingface \
    && chown -R model:model /app /models

USER 10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
