#FROM python:3.11.8-slim-bullseye
FROM python:3.8.18-slim-bullseye
WORKDIR /app
COPY requirements.txt .
RUN apt update && \
    apt install -y --no-install-recommends build-essential python3-dev libsasl2-dev libldap2-dev libssl-dev gettext && \
    apt clean && pip --no-cache-dir install -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

