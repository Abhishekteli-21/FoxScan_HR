# Free deployment: works as-is on Hugging Face Spaces (Docker Space) or Render.
# HF Spaces expects the app on port 7860.
FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /code/data && chmod 777 /code/data
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
