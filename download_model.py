from env import Env
from sentence_transformers import SentenceTransformer
from huggingface_hub import get_session

# Set your proxy here
get_session().verify = False

# Load the model
model = SentenceTransformer(Env.LM_MODEL, cache_folder=Env.ST_HOME)
#model.save(Env.ST_HOME)