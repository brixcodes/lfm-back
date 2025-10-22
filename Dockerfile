FROM python:3.10.15-slim


RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system fastapi \
    && adduser --system --ingroup fastapi fastapi

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint
RUN chown fastapi /entrypoint

COPY ./start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start
RUN chown fastapi /start

COPY ./celery_compose/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker
RUN chown fastapi /start-celeryworker

COPY ./celery_compose/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat
RUN chown fastapi /start-celerybeat

COPY ./celery_compose/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower

# Create celerybeat-schedule directory and set permissions
RUN mkdir -p /app/celerybeat \
    && chown fastapi:fastapi /app/celerybeat

# Create uploads directory and set permissions
RUN mkdir -p /app/src/static/uploads \
    && chown fastapi:fastapi /app/src/static/uploads  \
    && chmod -R 755 /app/src/static/uploads  

RUN mkdir -p /app/src/uploads \
    && chown fastapi:fastapi /app/src/uploads  \
    && chmod -R 755 /app/src/uploads  

COPY . .
ARG DATABASE_URL DATABASE_URL="default_values"

ARG PORT
# Expose the port your FastAPI app will run on
EXPOSE 5432
EXPOSE 8000

# Command to run the application
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

RUN chown -R fastapi:fastapi /app

USER fastapi

ENTRYPOINT ["/entrypoint"]