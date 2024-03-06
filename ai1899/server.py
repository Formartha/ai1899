# added proxy imports
from flask import Flask
from flasgger import Swagger

from env import Env
from api_routes import ai_api

app = Flask(__name__)

# -- register routes -- #
app.register_blueprint(ai_api, url_prefix='/ai')

# reference data: https://github.com/flasgger/flasgger/blob/master/flasgger/base.py
app.config["SWAGGER"] = {
    "title": "ai1899 API",
    "uiversion": 3,
    "version": "1.0.0",
    "description": "ai1899 restful api-docs interface",
    "specs_route": "/"  # if a UI will be added down the road, this should be removed.
}

swagger = Swagger(app)

if __name__ == '__main__':
    app.run(debug=True,
            host="0.0.0.0",
            port=Env.FLASK_PORT)
