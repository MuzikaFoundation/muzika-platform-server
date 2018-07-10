from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.login import jwt_check
from modules.response import helper
from modules.response.error import ERR

blueprint = Blueprint('like', __name__, url_prefix='/api')


@blueprint.route('/user/<user_id>/board/<board_type>/likes', methods=['GET'])
def _get_board_likes(user_id, board_type):
    """
    Gets an user's board likes list
    """
    table_name = db.table.like(board_type)

    if not table_name:
        return helper.response_err(ERR.COMMON.INVALID_REQUEST_BODY)

    with db.engine_rdonly.connect() as connection:
        board_like_statement = db.Statement(table_name).where(user_id=user_id)

        return helper.response_ok(db.to_relation_model_list(board_like_statement.select(connection)))


@blueprint.route('/user/<user_id>/board/<board_type>/comment/likes', methods=['GET'])
def _get_comments_likes(user_id, board_type):
    """
    Gets an user's comment likes list
    """
    table_name = db.table.comment_like(board_type)

    if not table_name:
        return helper.response_err(ERR.COMMON.INVALID_REQUEST_BODY)

    with db.engine_rdonly.connect() as connection:
        comment_like_statement = db.Statement(table_name).where(user_id=user_id)

        return helper.response_ok(db.to_relation_model_list(comment_like_statement.select(connection)))


@blueprint.route('/board/<board_type>/<int:post_id>/like', methods=['POST'])
@jwt_check
def _like_post(board_type, post_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    like_table_name = db.table.like(board_type)

    if not board_table_name or not like_table_name:
        return helper.response_err(ERR.COMMON.INVALID_REQUEST_BODY)

    like_statement = db.Statement(like_table_name).set(post_id=post_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        try:
            like_statement.insert(connection)
        except IntegrityError:
            return helper.response_err(ERR.COMMON.ALREADY_EXIST)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/<int:post_id>/like', methods=['DELETE'])
@jwt_check
def _cancel_like_post(board_type, post_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    like_table_name = db.table.like(board_type)

    if not board_table_name or not like_table_name:
        return helper.response_err(ERR.COMMON.INVALID_REQUEST_BODY)

    like_statement = db.Statement(like_table_name).where(post_id=post_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        deleted = like_statement.delete(connection).rowcount
        if deleted:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ERR.COMMON.NOT_EXIST)


@blueprint.route('/board/<board_type>/comment/<int:comment_id>/like', methods=['POST'])
@jwt_check
def _like_comment(board_type, comment_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    comment_like_table_name = db.table.comment_like(board_type)

    if not board_table_name or not comment_like_table_name:
        return helper.response_err(ERR.COMMON.INVALID_REQUEST_BODY)

    like_statement = db.Statement(comment_like_table_name).set(comment_id=comment_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        try:
            like_statement.insert(connection)
        except IntegrityError:
            return helper.response_err(ERR.COMMON.ALREADY_EXIST)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/comment/<int:comment_id>/like', methods=['DELETE'])
@jwt_check
def _cancel_like_comment(board_type, comment_id):
    user_id = request.user['user_id']

    board_table_name = db.table.board(board_type)
    comment_like_table_name = db.table.comment_like(board_type)

    if not board_table_name or not comment_like_table_name:
        return helper.response_err(ERR.COMMON.INVALID_REQUEST_BODY)

    like_statement = db.Statement(comment_like_table_name).where(comment_id=comment_id, user_id=user_id)

    with db.engine_rdwr.begin() as connection:
        deleted = like_statement.delete(connection).rowcount
        if deleted:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ERR.COMMON.NOT_EXIST)
