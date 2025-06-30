FROM cgr.dev/chainguard/python:latest-dev AS base

WORKDIR /app

# Copy requirements and install dependencies using pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY templates/ templates/
COPY static/ static/

# Expose port
EXPOSE 80

# Run the app using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
