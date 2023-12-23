FROM python:3.8-alpine
WORKDIR /app
COPY . .
RUN apk add --no-cache --update bash tzdata ffmpeg curl su-exec && \
    apk add --no-cache --virtual builddeps gcc musl-dev python3-dev libffi-dev openssl-dev cargo && \
    pip3 install --no-cache-dir httpx[http2] streamlink cryptography && \
    apk del builddeps && \
    touch /app/is_container && \
    mv entrypoint.sh /usr/local/bin && \
    rm -rf /tmp/* $HOME/.cache $HOME/.cargo

EXPOSE 6077 5004
ENTRYPOINT ["entrypoint.sh"]
