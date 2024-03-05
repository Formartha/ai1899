FROM python:3.9-slim-bullseye

WORKDIR /ai

# Copy just the requirements.txt file and install dependencies
COPY ai1899/requirements.txt requirements.txt

RUN apt-get update && \
    apt-get install -y git curl

# As the processing power of NVIDIA CUDA isn't always available, the incentive is to trim down the image size.
# By installing the cpu torch first, it will avoid installing the GPU related to NVIDIA CUDA.
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project directory into the container
COPY ai1899/ .

# Expose port 5000
EXPOSE 5000