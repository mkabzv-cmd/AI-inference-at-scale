ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG APP_UID=10001
ARG APP_GID=10001
ARG BASE_IMAGE

LABEL org.opencontainers.image.base.name="${BASE_IMAGE}"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XDG_CACHE_HOME=/tmp/cache \
    TORCH_HOME=/tmp/torch

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --requirement /app/requirements.txt \
    && python -m pip freeze --all > /app/dependency-versions.txt \
    && groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" \
       --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /tmp/cache /tmp/torch \
    && chown -R "${APP_UID}:${APP_GID}" /app /tmp/cache /tmp/torch

COPY download_model.py server.py /app/
RUN chown "${APP_UID}:${APP_GID}" /app/download_model.py /app/server.py

USER 10001:10001
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
