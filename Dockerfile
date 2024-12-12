# Gunakan base image Python
FROM python:3.10-slim

# Set working directory di dalam container
WORKDIR /app

# Install dependensi sistem yang dibutuhkan
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy file requirements.txt ke dalam container
COPY requirements.txt /app/

# Install dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code ke dalam container
COPY . /app/

# Ekspos port Flask
EXPOSE 8080

# Jalankan aplikasi menggunakan gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
