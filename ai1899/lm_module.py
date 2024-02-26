from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from env import Env

client = QdrantClient(host=Env.QDRANT, port=Env.QDRANTPORT)
model = SentenceTransformer(Env.LM_MODEL, cache_folder=Env.ST_HOME)
