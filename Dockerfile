FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN python3 -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

COPY . .
CMD ["sh", "-c", "source /app/.venv/bin/activate && python run.py"]