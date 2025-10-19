FROM python:3.12-alpine
WORKDIR /app
COPY . .
RUN apk add --no-cache --update bash tzdata ffmpeg curl su-exec && \
    apk add --no-cache --virtual builddeps gcc musl-dev python3-dev libffi-dev openssl-dev cargo && \
    pip3 install -r requirements.txt --no-cache-dir && \
    apk del builddeps && \
    touch /app/is_container && \
    mv Docker_entrypoint.sh /usr/local/bin && \
    rm -rf /tmp/* $HOME/.cache $HOME/.cargo

VOLUME /app/data /app/plugins_ext /app/.cabernet
EXPOSE 6077 5004
ENTRYPOINT ["Docker_entrypoint.sh"]
