from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.login import jwt_check
from modules.response import helper
from modules.response import error_constants as ER

blueprint = Blueprint('comment', __name__, url_prefix='/api')


@blueprint.route('/board/<board_type>/<int:post_id>/comment', methods=['GET'])
def _get_board_post_comments(board_type, post_id):
    # TODO : add pagination and add board comments GET API
    raise NotImplementedError


@blueprint.route('/board/<board_type>/<int:post_id>/comment', methods=['POST'])
@jwt_check
def _post_board_comment(board_type, post_id):
    json_form = request.get_json(force=True, silent=True)
    parent_comment_id = json_form.get('parent_comment_id')
    content = json_form.get('content')

    user_id = request.user['user_id']

    if not isinstance(content, str) or not isinstance(parent_comment_id, (int, type(None))):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    table_name = db.table.comment(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).set(
        user_id=user_id,
        post_id=post_id,
        parent_comment_id=parent_comment_id,
        content=content
    )

    with db.engine_rdwr.connect() as connection:
        try:
            statement.insert(connection)
        except IntegrityError:
            # if failed to insert
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/comment/<int:comment_id>', methods=['GET'])
def _get_board_comment(board_type, comment_id):
    table_name = db.table.comment(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).where(comment_id=comment_id, status='posted')

    with db.engine_rdonly.connect() as connection:
        comment = statement.select(connection).fetchone()

        # if the comment does not exist
        if not comment:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)

        return helper.response_ok(db.to_relation_model(comment))


@blueprint.route('/board/<board_type>/comment/<int:comment_id>', methods=['PUT'])
@jwt_check
def _modify_board_comment(board_type, comment_id):
    json_form = request.get_json(force=True, silent=True)
    content = json_form.get('content')

    user_id = request.user['user_id']

    if not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    table_name = db.table.comment(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).set(content=content)\
        .where(user_id=user_id, comment_id=comment_id, status='posted')

    with db.engine_rdwr.connect() as connection:
        updated = statement.update(connection).rowcount
        if updated:
            return helper.response_ok({'status': 'success'})
        else:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)


@blueprint.route('/board/<board_type>/comment/<int:comment_id>', methods=['DELETE'])
@jwt_check
def _delete_board_comment(board_type, comment_id):
    user_id = request.user['user_id']

    table_name = db.table.comment(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).set(status='deleted')\
        .where(user_id=user_id, comment_id=comment_id, status='posted')

    with db.engine_rdwr.connect() as connection:
        deleted = statement.update(connection).rowcount

        if not deleted:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})

