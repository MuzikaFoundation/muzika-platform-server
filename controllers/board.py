
from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules import sql
from modules.login import jwt_check
from modules.response import error_constants as ER
from modules.response import helper
from modules.youtube import parse_youtube_id

blueprint = Blueprint('board', __name__, url_prefix='/api')

BOARD_TYPE_LIST = (
    'community',
    'video',
    'sheet',
)


@blueprint.route('/board', methods=['POST'])
@jwt_check
def _post_to_community():
    """
    Uploads a post to the community.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')
    board_type = json_form.get('type')

    user_id = request.user['user_id']

    if not isinstance(title, str) or not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # define columns that all boards have
    columns = sql.Columns(user_id=user_id, title=title, content=content)

    if board_type == 'community':
        # community needs no additional columns
        pass
    elif board_type == 'video':
        # video needs additional columns (youtube video id and genre)
        genre = json_form.get('genre')
        youtube_video_id = parse_youtube_id(json_form.get('youtube_url'))

        # if parameter is invalid or does not exist
        if not isinstance(genre, str) or not isinstance(youtube_video_id, str):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

        columns(genre=genre, youtube_video_id=youtube_video_id)
    elif board_type == 'sheet':
        # sheet needs additional columns for file
        file_id = json_form.get('file_id')

        # if parameter is invalid or does not exist
        if not isinstance(file_id, int):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)
        columns(file_id=file_id)
    else:
        # if wrong type, response with invalid request message
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # construct a query
    upload_query_str = """
        INSERT INTO `{board_type}_board`
        SET 
          {columns_set_statement}
    """.format(board_type=board_type, columns_set_statement=columns.set_statement)

    with db.engine_rdwr.connect() as connection:
        connection.execute(text(upload_query_str), **columns.fetch_params)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/community/<int:post_id>', methods=['GET'])
def _get_community_post(post_id):
    board_type = request.args.get('type')

    community_post_query_str = """
        SELECT * FROM `{}_board`
        WHERE `post_id` = :post_id
        LIMIT 1
    """

    # if unknown board type,
    if board_type not in BOARD_TYPE_LIST:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    with db.engine_rdonly.connect() as connection:
        post = connection.execute(text(community_post_query_str), post_id=post_id).fetchone()

        # if the post does not exist,
        if post is None:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)

        return helper.response_ok(db.to_relation_model(post))


@blueprint.route('/community/<int:post_id>', methods=['PUT'])
@jwt_check
def _modify_post(post_id):
    """
    Modify a post that the user has.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')
    board_type = json_form.get('type')

    user_id = request.user['user_id']

    # if invalid parameter type
    if not isinstance(title, str) or not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # construct a default column that all boards have
    set_columns = sql.Columns(title=title, content=content)
    where_columns = sql.Columns(post_id=post_id, user_id=user_id)

    if board_type == 'community':
        # community needs no additional columns
        pass
    elif board_type == 'video':
        # video needs additional columns (youtube video id and genre)
        genre = json_form.get('genre')
        youtube_video_id = parse_youtube_id(json_form.get('youtube_url'))

        if not isinstance(genre, str) or not isinstance(youtube_video_id, str):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

        set_columns(youtube_video_id=youtube_video_id, genre=genre)
    elif board_type == 'sheet':
        # sheet needs additional columns for file
        file_id = json_form.get('file_id')

        if not isinstance(file_id, int):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

        set_columns(file_id=file_id)
    else:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    post_modify_query_str = """
        UPDATE `{board_type}_board`
        SET
          {set_statement}
          {where_statement}
    """.format(board_type=board_type,
               set_statement=set_columns.set_statement,
               where_statement=where_columns.where_statement)

    with db.engine_rdwr.connect() as connection:
        modified = connection.execute(text(post_modify_query_str),
                                      **set_columns.fetch_params,
                                      **where_columns.fetch_params).rowcount

        # if the post does not exist or is not the user's post
        if not modified:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})


@blueprint.route('/community/<int:post_id>', methods=['DELETE'])
@jwt_check
def _delete_post(post_id):
    """
    Delete a post that user has.
    """
    user_id = request.user['user_id']
    board_type = request.args.get('type')

    # if unknown board type,
    if board_type not in BOARD_TYPE_LIST:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    delete_query_str = """
        UPDATE `{board_type}_board`
        SET
          `status` = :post_status
        WHERE
          `post_id` = :post_id AND
          `user_id` = :user_id
    """.format(board_type=board_type)

    with db.engine_rdwr.connect() as connection:
        deleted = connection.execute(text(delete_query_str),
                                     post_status='deleted',
                                     post_id=post_id,
                                     user_id=user_id).rowcount

        # if the post does not exist or is not the user's post
        if not deleted:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})

