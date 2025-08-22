# Use official Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Run Django with gunicorn (better than runserver in Docker)
CMD ["gunicorn", "stripe_project.wsgi:application", "--bind", "0.0.0.0:8000"]
