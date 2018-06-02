
"""
 These APIs are only for developing conveniently, so are not produced in production mode.
 The server for production should execute these jobs by crontab.
"""

from flask import Blueprint
from works.update_contracts import update_contracts
from modules.response import helper


blueprint = Blueprint('job', __name__, url_prefix='/api/job')


@blueprint.route('/contracts', methods=['POST'])
def _update_contracts():
    update_contracts()
    return helper.response_ok({'status': 'success'})
