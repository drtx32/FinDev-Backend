FROM python:3.11.7-slim

WORKDIR /app

COPY /requirements.txt .
COPY /local_packages/ ./local_packages/
RUN pip3 install -r requirements.txt --no-cache-dir

RUN apt-get update \
    && apt-get install -y curl gnupg2 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

COPY app/ .

# EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
