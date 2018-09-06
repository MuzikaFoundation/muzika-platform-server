import os

from flask import Flask
from flask_cors import CORS

from config import AppConfig
from controllers import (
    music_contract, user, file, board, comment, like, seed,
    board_me, price)
from controllers.test import (
    paper_test
)
from modules.json_encoder import FlaskJSONEncoder

application = Flask(__name__)
CORS(application, max_age=31536000, supports_credentials=True)

application.json_encoder = FlaskJSONEncoder

blueprints = [
    # define blueprints for both production and development
    music_contract.blueprint,
    user.blueprint,
    file.blueprint,
    board.blueprint,
    board_me.blueprint,
    comment.blueprint,
    like.blueprint,
    seed.blueprint,
    price.blueprint,
]

production_blueprints = [
    # define blueprints for only production
]

development_blueprints = [
    # define blueprints for only development
    paper_test.blueprint
]


# application configuration
application.config.update(
    MAX_CONTENT_LENGTH=AppConfig.max_content_length
)


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
    # execute celery process
    import subprocess
    import argparse

    args = argparse.ArgumentParser()
    args.add_argument('-b', '--beat', help='Do periodical tasks.', default=False, action='store_true')

    args = args.parse_args()

    current_directory = os.path.dirname(os.path.abspath(__file__))

    # run celery for periodical or asynchronous tasks.
    # the application runs celery only in local, so need to run separately in production or stage environment.
    celery_env = os.environ.copy()
    celery_env['PYTHONPATH'] = current_directory
    celery_process_params = ['celery', '-A', 'tasks', 'worker', '--loglevel=info']
    if args.beat:
        celery_process_params.append('-B')

    celery_process = subprocess.Popen(celery_process_params, env=celery_env)

    # run web application
    try:
        application.run(
            host=AppConfig.host,
            port=AppConfig.port,
            threaded=True
        )
    except Exception as e:
        print(e)
    finally:
        # before exit, kill celery process and remove its files.
        celery_process.kill()
        os.remove(os.path.join(current_directory, 'celery.sqlite'))
        if args.beat:
            os.remove(os.path.join(current_directory, 'celerybeat-schedule.db'))
