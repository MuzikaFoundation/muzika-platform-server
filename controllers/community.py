
from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.login import jwt_check
from modules.response import helper
from modules.response import error_constants as ER

blueprint = Blueprint('community', __name__, url_prefix='/api')


@blueprint.route('/community', methods=['POST'])
@jwt_check
def _post_to_community():
    """
    Uploads a post to the community.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')

    user_id = request.user['user_id']

    if not isinstance(title, str) or not isinstance(content, str):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    upload_query_str = """
        INSERT INTO `community_board`
        SET 
          `user_id` = :user_id,
          `title` = :title,
          `content` = :content
    """

    with db.engine_rdwr.connect() as connection:
        connection.execute(text(upload_query_str), user_id=user_id, title=title, content=content)
        return helper.response_ok({'status': 'success'})


@blueprint.route('/community/<int:post_id>', methods=['GET'])
def _get_community_post(post_id):
    community_post_query_str = """
        SELECT * FROM `community_board`
        WHERE `post_id` = :post_id
        LIMIT 1
    """

    with db.engine_rdonly.connect() as connection:
        post = connection.execute(text(community_post_query_str), post_id=post_id).fetchone()

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

    user_id = request.user['user_id']

    post_modify_query_str = """
        UPDATE `community_board`
        SET
          `title` = :title,
          `content` = :content
        WHERE
          `post_id` = :post_id AND
          `user_id` = :user_id
    """

    with db.engine_rdwr.connect() as connection:
        modified = connection.execute(text(post_modify_query_str),
                                      title=title,
                                      content=content,
                                      post_id=post_id,
                                      user_id=user_id).rowcount

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

    delete_query_str = """
        UPDATE `community_board`
        SET
          `status` = :post_status
        WHERE
          `post_id` = :post_id AND
          `user_id` = :user_id
    """

    with db.engine_rdwr.connect() as connection:
        deleted = connection.execute(text(delete_query_str),
                                     post_status='deleted',
                                     post_id=post_id,
                                     user_id=user_id).rowcount

        # if the post does not exist or is not the user's post
        if not deleted:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})

