# Build context is the repository root (see smithery.yaml: dockerBuildPath).
FROM python:3.11-slim

WORKDIR /app

# Skill scripts + shared core + this server.
COPY skills ./skills
COPY core ./core
COPY mcp-server ./mcp-server

# Dependencies the skill scripts import at runtime, plus the packages.
RUN pip install --no-cache-dir -r mcp-server/requirements-skills.txt \
 && pip install --no-cache-dir ./core \
 && pip install --no-cache-dir ./mcp-server

# Skill scripts are located relative to this root.
ENV IFLY_SKILLS_ROOT=/app

ENTRYPOINT ["iflyskills-mcp"]
