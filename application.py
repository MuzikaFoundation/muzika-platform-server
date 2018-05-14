import os

from config import WebServerConfig
from controllers import artist
from flask import Flask

application = Flask(__name__)


blueprints = [
    # define blueprints for both production and development
    artist.blueprint
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

# register blueprints for producvtion
if env == 'production':
    for blueprint in production_blueprints:
        application.register_blueprint(blueprint)

if __name__ == '__main__':
    application.run(
        host=WebServerConfig.host,
        port=WebServerConfig.port,
        threaded=True
    )
