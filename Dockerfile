FROM python:3.13 as backend
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID myuser && useradd -m -u $UID -g $GID myuser

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY .python-version .
COPY uv.lock .
COPY pyproject.toml .
RUN uv sync

CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]