# Build context is the repository root.
FROM python:3.11-slim

WORKDIR /app

COPY skills ./skills
COPY core ./core
COPY backend ./backend

RUN pip install --no-cache-dir ./core \
 && pip install --no-cache-dir -r backend/requirements.txt \
 && pip install --no-cache-dir dingtalk-stream pycryptodome

ENV IFLY_SKILLS_ROOT=/app
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
