# Use the official Python 3.11.5 image as a base
FROM python:3.11.5-slim

# Define Google Chrome version as a build argument (change this if needed)
# Check available versions here: https://www.ubuntuupdates.org/package/google_chrome/stable/main/base/google-chrome-stable
ARG CHROME_VERSION=131.0.6778.204  # Set the specific Chrome version

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
    x11-xserver-utils \
    libasound2 \
    fonts-liberation \
    libgbm1 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libnss3 \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

RUN wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb \
  && apt install -y /tmp/chrome.deb \
  && rm /tmp/chrome.deb

# Add root user to group for pulseaudio access
RUN adduser root pulse-access

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the container
COPY . /app/

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
