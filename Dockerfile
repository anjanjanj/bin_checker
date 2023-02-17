FROM python:3.8.12-slim-bullseye

RUN apt-get update -q && apt-get install --no-install-recommends -qy python3-dev g++ gcc inetutils-ping

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

CMD ["python", "/usr/local/code/main.py"]