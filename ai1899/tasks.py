from celery import Celery
import itertools
from qdrant_client.models import PointStruct
import uuid

from env import Env
from lm_module import client, model

celery = Celery('ai',
                broker=Env.REDDIS_CELERY,
                backend=Env.REDDIS_CELERY)

celery.conf.task_track_started = True
celery.conf.task_ignore_result = False


@celery.task
def upsert_collection(json_data, collection, slices=100):

    for _, chunk in itertools.groupby(enumerate(sorted(json_data.items())), key=lambda x: x[0] // slices):
        points = []
        for _, (k, v) in chunk:
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=model.encode(v).tolist(),
                payload={'file_name': k}
            ))

        # Perform the upsert operation for the current chunk
        client.upsert(
            collection_name=collection,
            points=points,
        )
