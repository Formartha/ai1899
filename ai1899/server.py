# added proxy imports
from flask import Flask

from env import Env
from api_routes import ai_api

app = Flask(__name__)

# -- register routes -- #
app.register_blueprint(ai_api, url_prefix='/ai')

if __name__ == '__main__':
    app.run(debug=True,
            host="0.0.0.0",
            port=Env.FLASK_PORT)
