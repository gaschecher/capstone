FROM python:3.10-slim

WORKDIR /app

# Install SSL certificates and required packages
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create symlink from /app/backend to backend directory
RUN ln -s backend /app/backend

ENV MONGO_URI=mongodb://mongodb:27017/capstone

# Make the startup script executable
RUN chmod +x start.sh

EXPOSE 5000

CMD ["./start.sh"]
