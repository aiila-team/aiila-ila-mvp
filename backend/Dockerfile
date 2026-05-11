<<<<<<< HEAD
FROM python:3.12
=======
FROM python:3.11-slim
>>>>>>> origin/frontend

WORKDIR /app

COPY requirements.txt .

<<<<<<< HEAD
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
=======
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
>>>>>>> origin/frontend
