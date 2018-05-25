
from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
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


@blueprint.route('/board/<board_type>', methods=['POST'])
@jwt_check
def _post_to_community(board_type):
    """
    Uploads a post to the community.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')

    user_id = request.user['user_id']

    if not isinstance(title, str) or not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # define columns that all boards have
    statement = db.Statement('{}_board'.format(board_type)).set(user_id=user_id, title=title, content=content)

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

        statement.set(genre=genre, youtube_video_id=youtube_video_id)
    elif board_type == 'sheet':
        # sheet needs additional columns for file
        file_id = json_form.get('file_id')

        # if parameter is invalid or does not exist
        if not isinstance(file_id, int):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)
        statement.set(file_id=file_id)
    else:
        # if wrong type, response with invalid request message
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    with db.engine_rdwr.connect() as connection:
        connection.execute(text(statement.insert()), **statement.fetch_params)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/<int:post_id>', methods=['GET'])
def _get_community_post(board_type, post_id):
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


@blueprint.route('/board/<board_type>/<int:post_id>', methods=['PUT'])
@jwt_check
def _modify_post(board_type, post_id):
    """
    Modify a post that the user has.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')

    user_id = request.user['user_id']

    # if invalid parameter type
    if not isinstance(title, str) or not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # construct a default column that all boards have
    statement = db.Statement('{}_board'.format(board_type))\
        .set(title=title, content=content)\
        .where(post_id=post_id, user_id=user_id)

    if board_type == 'community':
        # community needs no additional columns
        pass
    elif board_type == 'video':
        # video needs additional columns (youtube video id and genre)
        genre = json_form.get('genre')
        youtube_video_id = parse_youtube_id(json_form.get('youtube_url'))

        if not isinstance(genre, str) or not isinstance(youtube_video_id, str):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

        statement.set(youtube_video_id=youtube_video_id, genre=genre)
    elif board_type == 'sheet':
        # sheet needs additional columns for file
        file_id = json_form.get('file_id')

        if not isinstance(file_id, int):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

        statement.set(file_id=file_id)
    else:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    with db.engine_rdwr.connect() as connection:
        modified = connection.execute(text(statement.update()), **statement.fetch_params).rowcount

        # if the post does not exist or is not the user's post
        if not modified:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/<int:post_id>', methods=['DELETE'])
@jwt_check
def _delete_post(board_type, post_id):
    """
    Delete a post that user has.
    """
    user_id = request.user['user_id']

    # if unknown board type,
    if board_type not in BOARD_TYPE_LIST:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement('{}_board'.format(board_type))\
        .set(status='deleted')\
        .where(post_id=post_id, user_id=user_id)

    with db.engine_rdwr.connect() as connection:
        deleted = connection.execute(text(statement.update()), statement.fetch_params).rowcount

        # if the post does not exist or is not the user's post
        if not deleted:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})

