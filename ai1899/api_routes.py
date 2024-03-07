from flask import Blueprint
from flask import request
from flask import jsonify
from flasgger import swag_from
import json
from qdrant_client.models import PointStruct, Distance, VectorParams
from qdrant_client.http import models

from lm_module import client, model
from tasks import upsert_collection as uc

ai_api = Blueprint('ai', __name__)


@swag_from("swag/query.yaml")
@ai_api.route("/query", methods=["POST"])
def query():
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


@swag_from("swag/most_similar_by_id.yaml")
@ai_api.route("/most_similar_by_id", methods=["POST"])
def most_similar_by_id():
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


@swag_from("swag/most_similar_by_name.yaml")
@ai_api.route("/most_similar_by_name", methods=["POST"])
def most_similar_by_name():
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


@swag_from("swag/upsert.yaml")
@ai_api.route("/upsert", methods=["POST"])
def upsert():
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


@swag_from("swag/upsert_collection.yaml")
@ai_api.route("/upsert_collection", methods=["POST"])
async def upsert_collection():
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


@swag_from("swag/check_upsert_status.yaml")
@ai_api.route('/check_upsert_status/<task_id>', methods=["GET"])
def check_task_status(task_id):
    if request.method == "GET":
        result = uc.AsyncResult(task_id)
        return jsonify({"status": result.state}), 200  # This will return the state of the task as a string
    else:
        return jsonify({"error": "Method Not Allowed"}), 405


@swag_from("swag/collections.yaml")
@ai_api.route("/collections", methods=["GET"])
def get_collections():
    return jsonify({"collections": [col.name for col in client.get_collections().collections]}), 200


@swag_from("swag/get_item.yaml")
@ai_api.route("/get_item", methods=["POST"])
def get_item():
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


@swag_from("swag/delete_item.yaml")
@ai_api.route("/delete_item", methods=["POST"])
def delete_item():
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

