FROM python:3.11-slim
WORKDIR /app
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt
COPY app.py .
COPY youtube_model.joblib .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
