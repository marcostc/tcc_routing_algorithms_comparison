# proj/app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

# Instalar o cliente PostgreSQL
RUN apt-get update && apt-get install -y postgresql-client

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py

COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

CMD ["/wait-for-db.sh", "flask", "run", "--host=0.0.0.0"]
