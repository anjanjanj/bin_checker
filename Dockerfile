FROM python:3.8.12-slim-bullseye

# venv setup
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONUNBUFFERED 1

# python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy the application
ADD code /usr/local/code

CMD ["python", "/usr/local/code/main.py"]