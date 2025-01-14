# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV APP_HOME /app

# Create the application directory
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install gunicorn
RUN pip install gunicorn

# Copy the requirements file and install dependencies
COPY requirements.txt $APP_HOME/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . $APP_HOME/

# Expose port 8000 for Gunicorn
EXPOSE 8000

# Start Gunicorn to run the Flask app
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:8000", "wsgi:app"]
