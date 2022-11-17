FROM alpine:3.16.2

COPY . /src

RUN apk add sudo py3-pip py3-psutil py3-pandas py3-matplotlib chafa imagemagick exa \
 && pip install --no-cache-dir ipykernel ipywidgets /src \
 && rm -rf /src

ENTRYPOINT ["euporie"]
