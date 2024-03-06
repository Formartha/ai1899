from flask import Blueprint
from flask import request
from flask import jsonify
import json
from qdrant_client.models import PointStruct, Distance, VectorParams
from qdrant_client.http import models

from lm_module import client, model
from tasks import upsert_collection as uc

ai_api = Blueprint('ai', __name__)


@ai_api.route("/query", methods=["POST"])
def query():
    """
    This API is used to query the AI module and return proper response back
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - query
            - collection
          properties:
            query:
              type: string
              description: Query term
              default: ""
            collection:
              type: string
              description: Collection to query from
              default: ""
            limit:
              type: integer
              description: Amount of response back
              default: 5
    responses:
      200:
        description: A response of available resources
    """
    post_data = request.json
    query_set = post_data["query"]
    query_collection = post_data.get("collection")

    limit = 5 if not post_data.get("limit") else post_data.get("limit")
    qvector = model.encode(query_set)

    collections = []
    data = []

    if not query_collection:
        _collections = client.get_collections()
        for collection in _collections.collections:
            collections.append(collection.name)
    else:
        collections.append(query_collection)

    for col in collections:
        hits = client.search(
            collection_name=col,
            query_vector=qvector,
            limit=limit)

        data.extend(hits)

    result = sorted(data, key=lambda data: data.score, reverse=True)[:limit]

    return jsonify({
            "hits": [hit.payload['file_name'] for hit in result],
            "score": [hit.score for hit in result]
    }), 200


@ai_api.route("/most_similar_by_id", methods=["POST"])
def most_similar_by_id():
    """
    This API is used to return most similar vectors by ID
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - _id
            - collection
          properties:
            _id:
              type: string
              description: id of the vector
              default: ""
            collection:
              type: string
              description: collection to query from
              default: ""
            limit:
              type: integer
              description: amount of response back
              default: 5
    responses:
      200:
        description: A response of available resources
      404:
        description: Resource not found
    """
    post_data = request.json
    collection = post_data.get("collection")
    _id = post_data.get('_id')
    limit = 5 if not post_data.get('limit') else post_data.get('limit')

    result = client.retrieve(
            collection_name=collection,
            ids=[_id],
            with_vectors=True
        )
    if not result:
        return jsonify({
            "status": "not found"
        }), 404
        
    hits = client.search(
        collection_name=collection,
        query_vector=result[0].vector,
        limit=limit)

    return jsonify({
            "hits": [hit.payload['file_name'] for hit in hits],
            "score": [hit.score for hit in hits],
    }), 200


@ai_api.route("/most_similar_by_name", methods=["POST"])
def most_similar_by_name():
    """
    This API is used to return most similar vectors by name
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - collection
          properties:
            name:
              type: string
              description: name of the item
              default: ""
            collection:
              type: string
              description: collection to query from
              default: ""
            limit:
              type: integer
              description: amount of response back
              default: 5
    responses:
      200:
        description: A response of available resources
      404:
        description: Name not found
    """
    post_data = request.json
    collection = post_data.get("collection")
    name = post_data.get('name')
    limit = 5 if not post_data.get('limit') else post_data.get('limit')

    result = client.scroll(
        collection_name=collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(key="file_name", match=models.MatchValue(value=name)),
            ]
        ),
        limit=1,
        with_payload=True,
        with_vectors=True,
    )

    if not result:
        return jsonify({"status": "not found"}), 404

    hits = client.search(
        collection_name=collection,
        query_vector=result[0][0].vector,
        limit=limit+1)

    return jsonify({
        "hits": [hit.payload['file_name'] for hit in hits[-limit:]],
        "score": [hit.score for hit in hits[-limit:]],
    }), 200


@ai_api.route("/upsert", methods=["POST"])
def upsert():
    """
    This API is used to upload a single item and push it to the QDRANT
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - desc
            - collection
          properties:
            desc:
              type: object
              description: Description of the item and the item name
              default: ""
            collection:
              type: string
              description: Collection to query from
              default: ""
    responses:
      200:
        description: Upsert collection succeeded
    """
    post_data = request.json
    vector = model.encode(post_data['desc'])
    collection = post_data.get("collection")

    client.upsert(
            collection_name=collection,
            points=[PointStruct(
                id=post_data['_id'],
                vector=vector.tolist(),
                payload=post_data['payload']
            )],
        )
    return jsonify({"status": "OK"}), 200


@ai_api.route("/upsert_collection", methods=["POST"])
async def upsert_collection():
    """
    Async upsert collection to QDRANT using remote Celery workers
    ---
    tags:
      - AI
    parameters:
      - name: file
        in: formData
        required: true
        type: file
      - name: collection
        required: true
        in: formData
        type: string
    content:
      multipart/form-data:
        schema:
          properties:
            file:
              type: file
              format: binary
              in: formData
              description: The JSON file to be uploaded
            collection:
              in: formData
              type: formData
              description: The name of the collection
    responses:
      200:
        description: Returns task ID
    """
    try:
        # Check if a file is present in the request
        collection = request.form["collection"]
        if 'file' in request.files:
            file = request.files['file']

            # Check if the file has a name
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400

            # Check if the file is a JSON file
            if file.filename.endswith('.json'):
                json_data = json.loads(file.read())
            else:
                return jsonify({'error': 'File format not supported, only JSON supported'}), 400

            try:  # as client returns raw string, we are treating it as try, except block
                client.get_collection(collection)
            except:
                client.recreate_collection(collection_name=collection,
                                           vectors_config=VectorParams(
                                               size=768,
                                               distance=Distance.COSINE))

            resp = uc.delay(json_data, collection, slices=50)

            return jsonify({"id": resp.task_id}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_api.route('/check_upsert_status/<task_id>', methods=["GET"])
def check_task_status(task_id):
    """
    This API is used to return a task status based on ID
    ---
    tags:
      - AI
    parameters:
      - name: task_id
        in: path
        required: true
    responses:
      200:
        description: A response of available resources
      405:
        description: Method not allowed
    """
    if request.method == "GET":
        result = uc.AsyncResult(task_id)
        return jsonify({"status": result.state}), 200  # This will return the state of the task as a string
    else:
        return jsonify({"error": "Method Not Allowed"}), 405


@ai_api.route("/collections", methods=["GET"])
def get_collections():
    """
    This API is used to return all the collections in QDRANT
    ---
    tags:
      - AI
    responses:
      200:
        description: A response of available resources
    """
    return jsonify({"collections": [col.name for col in client.get_collections().collections]}), 200


@ai_api.route("/get_item", methods=["POST"])
def get_item():
    """
    This api is used to upload single item and push it to the QDRANT
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - item
            - collection
          properties:
            item:
              type: string
              description: an item which to query
              default: ""
            collection:
              type: string
              description: collection to query from
              default: ""
    responses:
      200:
        description: return the id
      404:
        description: item not found
    """
    post_data = request.json
    payload = post_data.get("item")
    collection = post_data.get("collection")

    hit = client.scroll(
        collection_name=collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(key="file_name", match=models.MatchValue(value=payload)),
            ]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )

    try:
        return jsonify({"id": hit[0][0].id}), 200
    except:
        return jsonify({"status": "No item found"}), 404


@ai_api.route("/delete_item", methods=["POST"])
def delete_item():
    """
    This api is used to delete an item or items from QDRANT
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - item
            - collection
          properties:
            items:
              type: string
              description: an item to delete. could be a string or a list
              default: ""
            collection:
              type: string
              description: collection to query from
              default: ""
    responses:
      201:
        description: operation completed
    """
    post_data = request.json
    payload = post_data.get("items")
    collection = post_data.get("collection")

    points = []
    if isinstance(payload, list):
        points.extend(payload)
    else:
        points.append(payload)

    client.delete(
        collection_name=collection,
        points_selector=models.PointIdsList(
            points=points,
        ),
    )

    return jsonify({"status": "OK"}), 201

