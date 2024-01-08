FROM python:3.8-alpine
WORKDIR /app
COPY . .
RUN apk add --no-cache --update bash tzdata ffmpeg curl su-exec tini && \
    apk add --no-cache --virtual builddeps gcc musl-dev python3-dev libffi-dev openssl-dev cargo && \
    pip3 install -r requirements.txt --no-cache-dir && \
    apk del builddeps && \
    touch /app/is_container && \
    mv Docker_entrypoint.sh / && \
    rm -rf /tmp/* $HOME/.cache $HOME/.cargo

VOLUME /app/data /app/plugins_ext /app/.cabernet
EXPOSE 6077 5004
ENTRYPOINT ["tini", "--"]
CMD ["/Docker_entrypoint.sh"]
