# Pin both the Python patch release and Alpine minor release. Avoid floating
# tags such as python:latest or python:alpine in a reproducible lesson.
FROM python:3.13.15-alpine3.23@sha256:6438599575cca0d1df94aeee0d2ae088d4d8846eab554b2ee7784a3a6df0d516

WORKDIR /app
COPY --chown=10001:10001 app/server.py /app/server.py

USER 10001:10001
EXPOSE 8080

ENTRYPOINT ["python", "/app/server.py"]
