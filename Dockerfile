FROM python:3.12.9-slim-bullseye

RUN apt-get update -q && apt-get install --no-install-recommends -qy python3-dev g++ gcc inetutils-ping cron

# venv setup
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONUNBUFFERED 1

# python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt

RUN apt-get remove -qy python3-dev g++ gcc --purge

# copy the application
ADD code /usr/local/code

# Copy hello-cron file to the cron.d directory
COPY hello-cron /etc/cron.d/hello-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/hello-cron

# Apply cron job
RUN crontab /etc/cron.d/hello-cron
 
# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# # Run the command on container startup
# CMD cron && tail -f /var/log/cron.log

CMD ["/bin/bash", "-c", "printenv > /etc/environment && cron && tail -f /var/log/cron.log"]