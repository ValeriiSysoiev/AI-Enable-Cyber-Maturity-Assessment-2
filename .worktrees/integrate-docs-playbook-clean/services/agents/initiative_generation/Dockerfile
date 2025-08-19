FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# default values
ENV HOST=0.0.0.0
ENV PORT=8131

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host ${HOST} --port ${PORT}"]
