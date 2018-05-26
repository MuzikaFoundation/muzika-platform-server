from flask import Blueprint, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.login import jwt_check
from modules.response import helper
from modules.response import error_constants as ER

blueprint = Blueprint('like', __name__, url_prefix='/api')


@blueprint.route('/board/<board_type>/<int:post_id>/like', methods=['POST'])
@jwt_check
def _like_post(board_type, post_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    like_table_name = db.table.like(board_type)

    if not board_table_name or not like_table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    like_statement = db.Statement(like_table_name).set(post_id=post_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        try:
            like_statement.insert(connection)
        except IntegrityError:
            return helper.response_err(ER.ALREADY_EXIST, ER.ALREADY_EXIST_MSG)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/<int:post_id>/like', methods=['DELETE'])
@jwt_check
def _cancel_like_post(board_type, post_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    like_table_name = db.table.like(board_type)

    if not board_table_name or not like_table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    like_statement = db.Statement(like_table_name).where(post_id=post_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        deleted = like_statement.delete(connection).rowcount
        if deleted:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)


@blueprint.route('/board/<board_type>/comment/<int:comment_id>/like', methods=['POST'])
@jwt_check
def _like_comment(board_type, comment_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    comment_like_table_name = db.table.comment_like(board_type)

    if not board_table_name or not comment_like_table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    like_statement = db.Statement(comment_like_table_name).set(comment_id=comment_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        try:
            like_statement.insert(connection)
        except IntegrityError:
            return helper.response_err(ER.ALREADY_EXIST, ER.ALREADY_EXIST_MSG)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/comment/<int:comment_id>/like', methods=['DELETE'])
@jwt_check
def _cancel_like_comment(board_type, comment_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    comment_like_table_name = db.table.comment_like(board_type)

    if not board_table_name or not comment_like_table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    like_statement = db.Statement(comment_like_table_name).where(comment_id=comment_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        deleted = like_statement.delete(connection).rowcount
        if deleted:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)
