import os

from flask import Flask
from flask_cors import CORS

from config import WebServerConfig
from controllers import (
    artist, user, file, board, comment
)
from modules.json_encoder import FlaskJSONEncoder

application = Flask(__name__)
CORS(application, max_age=31536000, supports_credentials=True)

application.json_encoder = FlaskJSONEncoder

blueprints = [
    # define blueprints for both production and development
    artist.blueprint,
    user.blueprint,
    file.blueprint,
    board.blueprint,
    comment.blueprint,
]

production_blueprints = [
    # define blueprints for only production
]

development_blueprints = [
    # define blueprints for only development
]


# ELB Health Check Route
@application.route("/")
def _status():
    return "alive"


@application.route("/alive")
def _status_alive():
    return "alive"


env = os.environ.get('ENV')

for blueprint in blueprints:
    application.register_blueprint(blueprint)

# register blueprints for development
if env != 'production':
    for blueprint in development_blueprints:
        application.register_blueprint(blueprint)

# register blueprints for production
if env == 'production':
    for blueprint in production_blueprints:
        application.register_blueprint(blueprint)

if __name__ == '__main__':
    application.run(
        host=WebServerConfig.host,
        port=WebServerConfig.port,
        threaded=True
    )
