FROM python:3.13.5

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD fastapi dev --host 0.0.0.0 main.py
