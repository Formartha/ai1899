from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, UpsertOperation, PointsList
from qdrant_client.models import PointStruct
import pandas as pd
import json
from sentence_transformers import SentenceTransformer
import numpy as np
import uuid
import os

from ai1899.env import Env


client = QdrantClient(host=Env.qdrant_host, port=Env.qdrant_port)
client.recreate_collection(collection_name="srm",
                           vectors_config=VectorParams(
                               size=768,
                               distance=Distance.COSINE))


with open(os.path.join(os.path.dirname(__file__), "examples", "collection_a_example.json")) as f:
    data = json.load(f)
    df = pd.DataFrame([{"file_name": k, "_id": str(uuid.uuid4()), "text": "TEST: {}; DESCRIPTION: {}".format(k.replace('_', ' '), v)} for k, v in data.items()])
    # df.to_csv("tests.csv")
    
    
model_name = 'msmarco-distilbert-base-tas-b'
model = SentenceTransformer(model_name)


embeddings = model.encode(df.text.to_list())
np.save("embeddings.npy", embeddings)


def get_batch_points(df, batch_size):
    for i in range(0, len(df), batch_size):
        yield df.iloc[i:i+batch_size]


for batch in get_batch_points(df, 1000):
    points = [
        PointStruct(id=row['_id'], vector=embeddings[i], payload={'file_name': row['file_name']}) for i, row in batch.iterrows()
    ]

    client.batch_update_points(
        collection_name="ColTest",
        update_operations=[UpsertOperation(upsert=PointsList(points=points))]
    )
