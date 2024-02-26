What?
------
this project intended for whoever wants to use humanized queries to select test cases.
The idea is to have a test and it's description and test steps, then a system or initiator could query it.

How to run?
----------
to improve performance and reduce footprint, the idea is to have the model loaded on a shared volume using:
download_model.py. After running it, please provide proper path to the docker-compose.yaml file.

To start the stack
--------------------
DEVICE=/path/to/downloaded/model LM_MODEL=model-name docker compose up -d

Troubleshoot
------------
There is a known issue to install docker-compose on Mx processors (Mac), to fix it you should.
1. pip3 install "cython<3.0.0" wheel && pip3 install pyyaml==5.4.1 --no-build-isolation
2. pip3 install docker-compose