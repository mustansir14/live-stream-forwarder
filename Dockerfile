# Use the official Python 3.11.5 image as a base
FROM python:3.11.5-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gnupg \
    wget \
    ffmpeg \
    xvfb \
    pulseaudio \
    pulseaudio-utils \
    dbus \
    x11-utils \
    x11-xserver-utils && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update -y && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# add root user to group for pulseaudio access
RUN adduser root pulse-access

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files and shared code into the container
COPY . /app/


# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
