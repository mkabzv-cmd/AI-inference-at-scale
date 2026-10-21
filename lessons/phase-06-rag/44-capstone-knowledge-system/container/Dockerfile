ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COURSE_HOST=0.0.0.0 \
    COURSE_PORT=8080 \
    COURSE_PHASE_DIR=/opt/course/lessons/phase-06-rag \
    COURSE_INDEX_DIR=/tmp/course-knowledge-index \
    COURSE_IDENTITIES_PATH=/opt/course/lessons/phase-06-rag/44-capstone-knowledge-system/configs/identities.json

WORKDIR /opt/course

COPY lessons/phase-06-rag/41-ingestion-chunks-embeddings-indexes/configs/ lessons/phase-06-rag/41-ingestion-chunks-embeddings-indexes/configs/
COPY lessons/phase-06-rag/41-ingestion-chunks-embeddings-indexes/data/ lessons/phase-06-rag/41-ingestion-chunks-embeddings-indexes/data/
COPY lessons/phase-06-rag/41-ingestion-chunks-embeddings-indexes/src/ lessons/phase-06-rag/41-ingestion-chunks-embeddings-indexes/src/
COPY lessons/phase-06-rag/42-retrieval-hybrid-reranking/configs/ lessons/phase-06-rag/42-retrieval-hybrid-reranking/configs/
COPY lessons/phase-06-rag/42-retrieval-hybrid-reranking/src/ lessons/phase-06-rag/42-retrieval-hybrid-reranking/src/
COPY lessons/phase-06-rag/43-grounded-generation-rag-evaluation-security/configs/ lessons/phase-06-rag/43-grounded-generation-rag-evaluation-security/configs/
COPY lessons/phase-06-rag/43-grounded-generation-rag-evaluation-security/src/ lessons/phase-06-rag/43-grounded-generation-rag-evaluation-security/src/
COPY lessons/phase-06-rag/44-capstone-knowledge-system/configs/ lessons/phase-06-rag/44-capstone-knowledge-system/configs/
COPY lessons/phase-06-rag/44-capstone-knowledge-system/src/ lessons/phase-06-rag/44-capstone-knowledge-system/src/

USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python3", "/opt/course/lessons/phase-06-rag/44-capstone-knowledge-system/src/service.py"]
