FROM python:3.12.9-slim-bullseye

RUN apt-get update -q && apt-get install --no-install-recommends -qy python3-dev g++ gcc inetutils-ping curl

# Install Chromedriver dependencies and Chromium
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg ca-certificates fonts-liberation \
    libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libasound2 libxss1 libxtst6 libappindicator3-1 libgtk-3-0 \
    chromium && \
    rm -rf /var/lib/apt/lists/*

# Download matching ChromeDriver v120 (new Chrome for Testing location)
RUN wget -O /tmp/chromedriver.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.71/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver



# venv setup
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONUNBUFFERED=1

# python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt


#
# ::: UNCOMMENT FOR AMD64 :::
#
# # Latest releases available at https://github.com/aptible/supercronic/releases
# ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 \
#     SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8 \
#     SUPERCRONIC=supercronic-linux-amd64

# RUN curl -fsSLO "$SUPERCRONIC_URL" \
#  && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
#  && chmod +x "$SUPERCRONIC" \
#  && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
#  && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic
#
# :::
#

#
# ::: ARM64 (RPI4) :::
#
# Latest releases available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-arm64 \
SUPERCRONIC_SHA1SUM=e0f0c06ebc5627e43b25475711e694450489ab00 \
SUPERCRONIC=supercronic-linux-arm64

RUN curl -fsSLO "$SUPERCRONIC_URL" \
&& echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
&& chmod +x "$SUPERCRONIC" \
&& mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
&& ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic
#
# :::
#


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