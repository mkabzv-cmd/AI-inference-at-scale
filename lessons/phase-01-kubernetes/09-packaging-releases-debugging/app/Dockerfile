FROM python:3.12.7-slim-bookworm@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BIND_HOST=0.0.0.0

WORKDIR /app

RUN groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" \
       --no-create-home --shell /usr/sbin/nologin app

COPY server.py /app/server.py

USER 10001:10001
EXPOSE 8080

ENTRYPOINT ["python", "/app/server.py"]
