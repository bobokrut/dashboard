FROM python:3.9.16-slim as base

ARG geocode_key
ARG secret


ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

ENV GEOCODING_KEY=$geocode_key
ENV SECRET_KEY=$secret

WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends libtiff5-dev libjpeg62-turbo-dev libopenjp2-7-dev zlib1g-dev \
#     libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk \
#     libharfbuzz-dev libfribidi-dev libxcb1-dev libpq-dev && rm -rf /var/lib/apt/lists/*

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /venv

COPY requirements.txt .
RUN . /venv/bin/activate && pip install -r requirements.txt

FROM base as final

# RUN apt-get update && apt-get -y --no-install-recommends watchexec && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends inotify-tools && rm -rf /var/lib/apt/lists/*

COPY . .

COPY --from=builder /venv /venv

EXPOSE 8000

ENTRYPOINT ["/venv/bin/uvicorn"]
CMD ["--factory", "src.main:create_server", "--host", "0.0.0.0"]
# CMD ["--bind", "0.0.0.0:8000", "-w", "4", "main:create_server()", "--reload", "--reload-extra-file", "config.json"]
# CMD ["main:create_server()"]

