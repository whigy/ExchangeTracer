FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY boc_api.py .

ENTRYPOINT [ "python", "boc_api.py" ]