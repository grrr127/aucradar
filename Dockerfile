FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

# Poetry 설치
ENV POETRY_VERSION=1.8.3
RUN pip install --upgrade pip && pip install "poetry==${POETRY_VERSION}"

# 의존성 먼저 복사 (캐시 최적화)
COPY pyproject.toml poetry.lock* /app/

# Poetry가 venv를 컨테이너 내부에 만들지 않게
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --only main

# 소스 복사
COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

