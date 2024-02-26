# docker build -t aiagent:aiagent -f Dockerfile .

FROM python:3.9

WORKDIR /ai

COPY ai1899/requirements.txt requirements.txt

RUN apt-get update && apt-get install -y git curl
RUN pip3 install -r requirements.txt
EXPOSE 5000

COPY ai1899/ .

# -- downloading LM model -- #
#ENV SENTENCE_TRANSFORMERS_HOME=/ai/.model/
#RUN python3 download_model.py

# -- starting program -- #
#CMD ["python3", "server.py"]