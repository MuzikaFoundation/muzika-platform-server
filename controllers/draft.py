import json

from flask import Blueprint, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.ethereum_address import check_address_format
from modules.login import jwt_check, PLATFORM_TYPES
from modules.response.error import ERR
from modules.response import helper
from modules.secret import load_secret_json
from modules.sign_message import get_message_for_user
from modules.web3 import get_web3

blueprint = Blueprint('draft', __name__, url_prefix='/api')


@blueprint.route('/draft', methods=['GET'])
@jwt_check
def _get_draft():
    user_id = request.user['user_id']
    board_type = request.args.get('boardType')

    with db.engine_rdonly.connect() as connect:
        draft_list = db.statement(db.table.POST_DRAFTS) \
            .where(user_id=user_id, board_type=board_type) \
            .select(connect)

        return helper.response_ok([dict(draft_row) for draft_row in draft_list])


@blueprint.route('/draft', methods=['POST'])
@jwt_check
def _post_draft():
    user_id = request.user['user_id']
    board_type = request.args.get('boardType')
    data = request.get_json(force=True, silent=True)

    with db.engine_rdwr.connect() as connect:
        draft_id = db.statement(db.table.POST_DRAFTS).set(
            type=board_type,
            user_id=user_id,
            data=json.dumps(data),
            version=1
        ).insert(connect).lastrowid

        return helper.response_ok(draft_id)


@blueprint.route('/draft/<draft_id>', methods=['PUT'])
@jwt_check
def _put_draft(draft_id):
    user_id = request.user['user_id']
    data = request.get_json(force=True, silent=True)

    with db.engine_rdwr.connect() as connect:
        draft_row = db.statement(db.table.POST_DRAFTS) \
            .where(user_id=user_id, draft_id=draft_id).select(connect).fetchone()

        if draft_row is None:
            return helper.response_err(ERR.DRAFT.NOT_EXISTS)

        db.statement(db.table.POST_DRAFTS).set(data=json.dumps(data)).where(draft_id=draft_id).update(connect)

        return helper.response_ok("OK")


@blueprint.route('/draft/<draft_id>', methods=['DELETE'])
@jwt_check
def _delete_draft(draft_id):
    user_id = request.user['user_id']

    with db.engine_rdwr.connect() as connect:
        draft_row = db.statement(db.table.POST_DRAFTS) \
            .where(user_id=user_id, draft_id=draft_id) \
            .select(connect).fetchone()

        if draft_row is None:
            return helper.response_err(ERR.DRAFT.NOT_EXISTS)
        elif draft_row['is_uploaded'] == 1:
            return helper.response_err(ERR.DRAFT.ALREADY_UPLOADED)
        else:
            db.statement(db.table.POST_DRAFTS).where(draft_id=draft_id).delete(connect)

            return helper.response_ok("OK")
