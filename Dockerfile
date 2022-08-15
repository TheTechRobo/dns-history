FROM python:3.9-slim-bullseye
RUN pip install --no-cache-dir gunicorn flask[async] requests rethinkdb tblib
RUN apt update
RUN apt install -y openssl dnsutils

ENV YES_WE_ARE_IN_DOCKER YES

COPY . /app
EXPOSE 8000
WORKDIR /app
ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:8000", "--config", "gunicorn.conf", "app:app"]
