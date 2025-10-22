FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .
CMD python run.py