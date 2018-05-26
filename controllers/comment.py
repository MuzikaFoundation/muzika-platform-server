from flask import Blueprint, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from modules import database as db
from modules.login import jwt_check
from modules.response import helper
from modules.response import error_constants as ER

blueprint = Blueprint('comment', __name__, url_prefix='/api')


@blueprint.route('/board/<board_type>/<int:post_id>/comment', methods=['GET'])
def _get_board_post_comments(board_type, post_id):
    comment_table_name = db.table.comment(board_type)
    board_table_name = db.table.board(board_type)

    page = request.args.get('page', 1)

    # if unknown board type
    if not comment_table_name or not board_table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    fetch_query_str = """
        SELECT `c`.*, '!user', `u`.*
        FROM `{}` `c`
        INNER JOIN `{}` `b`
          ON (`c`.`post_id` = `b`.`post_id` AND `c`.`parent_comment_id` IS NULL)
        INNER JOIN `users` `u`
          ON (`u`.`user_id` = `c`.`user_id`)
        WHERE `c`.`post_id` = :post_id AND `c`.`status` = :post_status
    """.format(comment_table_name, board_table_name)

    count_query_str = """
        SELECT COUNT(*) AS `cnt`
        FROM `{}` `c`
        INNER JOIN `{}` `b`
          ON (`c`.`post_id` = `b`.`post_id` AND `c`.`parent_comment_id` IS NULL)
        WHERE `c`.`post_id` = :post_id AND `c`.`status` = :post_status
    """.format(comment_table_name, board_table_name)

    order_query_str = "ORDER BY `c`.`created_at` DESC"

    with db.engine_rdonly.connect() as connection:
        from modules.pagination import Pagination
        return helper.response_ok(Pagination(
            connection=connection,
            fetch=fetch_query_str,
            count=count_query_str,
            order=order_query_str,
            current_page=page,
            fetch_params={'post_id': post_id, 'post_status': 'posted'}
        ).get_result(db.to_relation_model))


@blueprint.route('/board/<board_type>/<int:post_id>/comment', methods=['POST'])
@jwt_check
def _post_board_comment(board_type, post_id):
    json_form = request.get_json(force=True, silent=True)
    content = json_form.get('content')

    user_id = request.user['user_id']

    if not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    table_name = db.table.comment(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).set(
        user_id=user_id,
        post_id=post_id,
        content=content
    )

    with db.engine_rdwr.begin() as connection:
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
    subcomments_query_str = """
        SELECT `c`.*, '!user', `u`.* FROM `{}` `c`
        INNER JOIN `users` `u`
        ON (`u`.`user_id` = `c`.`user_id`)
        WHERE `parent_comment_id` = :parent_comment_id AND `status` = :comment_status
        ORDER BY `c`.`created_at` ASC
    """.format(table_name)

    with db.engine_rdonly.connect() as connection:
        comment = statement.select(connection).fetchone()

        # if the comment does not exist
        if not comment:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)

        comment = db.to_relation_model(comment)
        subcomments = connection.execute(text(subcomments_query_str),
                                         parent_comment_id=comment['comment_id'], comment_status='posted')

        comment.update({'subcomments': db.to_relation_model_list(subcomments)})
        return helper.response_ok(comment)


@blueprint.route('/board/<board_type>/comment/<int:parent_comment_id>', methods=['POST'])
@jwt_check
def _post_board_subcomment(board_type, parent_comment_id):
    json_form = request.get_json(force=True, silent=True)
    content = json_form.get('content')

    user_id = request.user['user_id']

    if not isinstance(content, str) or not isinstance(parent_comment_id, int):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    table_name = db.table.comment(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).set(user_id=user_id, parent_comment_id=parent_comment_id, content=content)

    parent_update_statement = """
        UPDATE `{}`
        SET
          `reply_count` = `reply_count` + 1
        WHERE
          `comment_id` = :parent_comment_id
        LIMIT 1
    """.format(table_name)

    with db.engine_rdwr.begin() as connection:
        try:
            statement.insert(connection)
        except IntegrityError:
            # if failed to insert
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

        connection.execute(text(parent_update_statement), parent_comment_id=parent_comment_id)

        return helper.response_ok({'status': 'success'})


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

