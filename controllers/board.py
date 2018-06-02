
from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.login import jwt_check
from modules.response import error_constants as ER
from modules.response import helper
from modules.youtube import parse_youtube_id

blueprint = Blueprint('board', __name__, url_prefix='/api')


@blueprint.route('/board/<board_type>', methods=['GET'])
def _get_board_posts(board_type):
    table_name = db.table.board(board_type)
    page = request.args.get('page', 1)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    from modules.pagination import Pagination

    fetch_query_str = """
        SELECT `b`.*, '!author', `u`.*, '!sheet_music', `p`.*
        FROM `{}` `b` 
        INNER JOIN `users` `u` 
          ON (`u`.`user_id` = `b`.`user_id`)
        INNER JOIN `papers` `p`
          ON `p`.`paper_id` = `b`.`paper_id`
    """.format(table_name)

    count_query_str = "SELECT COUNT(*) AS `cnt` FROM `{}`".format(table_name)
    order_query_str = "ORDER BY `post_id` DESC"

    with db.engine_rdonly.connect() as connection:
        return helper.response_ok(Pagination(
            connection=connection,
            fetch=fetch_query_str,
            count=count_query_str,
            order=order_query_str,
            current_page=page
        ).get_result(db.to_relation_model))


@blueprint.route('/board/<board_type>', methods=['POST'])
@jwt_check
def _post_to_community(board_type):
    """
    Uploads a post to the community.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')
    tags = json_form.get('tags', [])

    user_id = request.user['user_id']

    if not isinstance(title, str) or not isinstance(content, str) or not isinstance(tags, (list, type(None))):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # remove duplication
    tags = set(tags)

    # define columns that all boards have
    table_name = db.table.board(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    tag_insert_query_str = """
            INSERT INTO `{}` (`post_id`, `name`)
            VALUES(:post_id, :tag_name)
    """.format(db.table.tags(board_type))

    statement = db.Statement(table_name).set(user_id=user_id, title=title, content=content)
    paper_statement = None

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
        sheet_music = json_form.get('sheet_music')
        file_id = sheet_music.get('file_id')

        # Do not use **sheet_music for safety
        paper_statement = db.Statement(db.table.PAPERS).set(
            user_id=user_id,
            name=sheet_music.get('name'),
            file_id=sheet_music.get('file_id'),
            ipfs_file_hash=sheet_music.get('ipfs_file_hash'),
            tx_hash=sheet_music.get('tx_hash')
        )

        # if parameter is invalid or does not exist
        if not isinstance(file_id, int):
            return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)
        statement.set(file_id=file_id)

    with db.engine_rdwr.connect() as connection:
        if paper_statement is not None:
            paper_id = paper_statement.insert(connection).lastrowid
            statement.set(paper_id=paper_id)

        post_id = statement.insert(connection).lastrowid

        # if tags exist, insert tags
        if tags:
            tag_multi_params = [{'post_id': post_id, 'tag_name': tag_name} for tag_name in tags]
            connection.execute(text(tag_insert_query_str), *tag_multi_params)

        return helper.response_ok({'post_id': post_id})


@blueprint.route('/board/<board_type>/<int:post_id>', methods=['GET'])
def _get_community_post(board_type, post_id):
    table_name = db.table.board(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name).where(post_id=post_id, status='posted')
    tags_statement = db.Statement(db.table.tags(board_type)).columns('name').where(post_id=post_id)

    with db.engine_rdonly.connect() as connection:
        post = statement.select(connection).fetchone()
        tags = tags_statement.select(connection)

        # if the post does not exist,
        if post is None:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)

        post = db.to_relation_model(post)
        post.update({'tags': [tag['name'] for tag in tags]})
        return helper.response_ok(post)


@blueprint.route('/board/<board_type>/<int:post_id>', methods=['PUT'])
@jwt_check
def _modify_post(board_type, post_id):
    """
    Modify a post that the user has.
    """
    json_form = request.get_json(force=True, silent=True)
    title = json_form.get('title')
    content = json_form.get('content')
    tags = json_form.get('tags', [])

    user_id = request.user['user_id']

    # if invalid parameter type
    if not isinstance(title, str) or not isinstance(content, str) or not isinstance(tags, (type(None), list)):
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # remove duplication
    tags = set(tags)

    table_name = db.table.board(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    # construct a default column that all boards have
    statement = db.Statement(table_name)\
        .set(title=title, content=content)\
        .where(post_id=post_id, user_id=user_id, status='posted')

    # queries for inserting or deleting tags when modified
    tag_insert_query_str = """
        INSERT INTO `{}` (`post_id`, `name`)
        VALUES(:post_id, :tag_name)
    """.format(db.table.tags(board_type))

    tag_delete_query_str = """
        DELETE FROM `{}`
        WHERE `post_id` = :post_id AND `name` IN :delete_tags
    """.format(db.table.tags(board_type))

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

    with db.engine_rdwr.connect() as connection:
        modified = statement.update(connection).rowcount

        # if the post does not exist or is not the user's post
        if not modified:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        current_tags = db.Statement(db.table.tags(board_type)).columns('name')\
            .where(post_id=post_id).select(connection)
        current_tags = set([tag['name'] for tag in current_tags])

        # get tags for deletion
        delete_tags = current_tags - tags

        # get tags for insert
        insert_tags = tags - current_tags

        # insert new tags
        if insert_tags:
            tag_multi_params = [{'post_id': post_id, 'tag_name': tag_name} for tag_name in insert_tags]
            connection.execute(text(tag_insert_query_str), *tag_multi_params)

        # remove tags for deletion
        if delete_tags:
            connection.execute(text(tag_delete_query_str), post_id=post_id, delete_tags=delete_tags)

        return helper.response_ok({'status': 'success'})


@blueprint.route('/board/<board_type>/<int:post_id>', methods=['DELETE'])
@jwt_check
def _delete_post(board_type, post_id):
    """
    Delete a post that user has.
    """
    user_id = request.user['user_id']

    table_name = db.table.board(board_type)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    statement = db.Statement(table_name)\
        .set(status='deleted')\
        .where(post_id=post_id, user_id=user_id, status='posted')

    with db.engine_rdwr.connect() as connection:
        deleted = statement.update(connection).rowcount

        # if the post does not exist or is not the user's post
        if not deleted:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})

