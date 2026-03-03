FROM python:3.12.9-slim-bullseye

RUN apt-get update -q && apt-get install --no-install-recommends -qy python3-dev g++ gcc curl \
    && rm -rf /var/lib/apt/lists/*

# venv setup
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONUNBUFFERED=1

# python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt

# Supercronic installation (architecture-aware)
# Latest releases available at https://github.com/aptible/supercronic/releases
ARG TARGETARCH
RUN ARCH="${TARGETARCH:-amd64}" \
    && if [ "$ARCH" = "amd64" ]; then \
         SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8; \
       elif [ "$ARCH" = "arm64" ]; then \
         SUPERCRONIC_SHA1SUM=e0f0c06ebc5627e43b25475711e694450489ab00; \
       else \
         echo "Unsupported architecture: $ARCH" && exit 1; \
       fi \
    && SUPERCRONIC="supercronic-linux-${ARCH}" \
    && SUPERCRONIC_URL="https://github.com/aptible/supercronic/releases/download/v0.2.33/${SUPERCRONIC}" \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic


# clean up dependencies
RUN apt-get remove -qy python3-dev g++ gcc curl --purge \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# copy the application
ADD code /usr/local/code

# move our cron entry
ADD hello-cron /etc/crontab

# run supercronic pointed at the crontab
CMD ["/usr/local/bin/supercronic", "/etc/crontab"]