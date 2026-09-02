FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

# Set work directory
WORKDIR /app

# Install system dependencies including GDAL, GEOS, and PostgreSQL client libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    binutils \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8000

# Default command: run development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
