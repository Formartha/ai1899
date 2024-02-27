FROM python:3.9

WORKDIR /ai

# Copy just the requirements.txt file and install dependencies
COPY ai1899/requirements.txt requirements.txt

RUN apt-get update && \
    apt-get install -y git curl && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project directory into the container
COPY ai1899/ .

# Expose port 5000
EXPOSE 5000