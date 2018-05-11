
from flask import Flask

application = Flask(__name__)


# ELB Health Check Route
@application.route("/")
def _status():
    return "alive"


@application.route("/alive")
def _status_alive():
    return "alive"


