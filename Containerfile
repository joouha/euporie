FROM alpine:3.23
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_SYSTEM_PYTHON=1
ENV UV_COMPILE_BYTECODE=1

RUN apk add sudo py3-pip py3-psutil py3-pandas py3-matplotlib chafa imagemagick exa

# Install unspecified dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --break-system-packages --no-cache-dir ipykernel ipywidgets

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.,target=/src \
    uv pip install --link-mode=copy --break-system-packages /src

ENTRYPOINT ["euporie"]
