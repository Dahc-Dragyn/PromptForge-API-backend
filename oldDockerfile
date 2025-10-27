# --- Stage 1: Build the dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# --- Stage 2: Create the final, lean image ---
FROM python:3.12-slim

WORKDIR /app

# Copy the pre-built dependencies from the 'builder' stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy the application source code into the container
COPY ./app ./app

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]