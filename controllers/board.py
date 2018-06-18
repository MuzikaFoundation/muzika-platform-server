from flask import Blueprint, request
from sqlalchemy import text

import tasks
from modules import database as db
from modules import ipfs
from modules.login import jwt_check
from modules.response import error_constants as ER
from modules.response import helper
from modules.youtube import parse_youtube_id

blueprint = Blueprint('board', __name__, url_prefix='/api')


@blueprint.route('/board/<board_type>', methods=['GET'])
def _get_board_posts(board_type):
    table_name = db.table.board(board_type)
    user_id = request.args.get('user_id')
    page = request.args.get('page', 1)

    # if unknown board type
    if not table_name:
        return helper.response_err(ER.INVALID_REQUEST_BODY, ER.INVALID_REQUEST_BODY_MSG)

    from modules.pagination import Pagination

    stmt = db.statement(table_name).columns('*')

    if board_type == 'music':
        # If the board type is music, only returns the root IPFS file hash, not recursively since the contract and
        # IPFS files are 1:N relationship, but if only returning the root IPFS file, it can be 1:1 relationship.
        stmt.columns('!music_contract', (db.table.MUSIC_CONTRACTS, '*'))
        stmt.columns('!ipfs_file', (db.table.IPFS_FILES, '*'))
        stmt.inner_join(db.table.MUSIC_CONTRACTS, 'post_id')
        stmt.inner_join((db.table.IPFS_FILES, db.table.MUSIC_CONTRACTS), ('file_id', 'ipfs_file_id'))

    stmt.inner_join(db.table.USERS, 'user_id').columns('!author', (db.table.USERS, '*'))
    stmt.where(status='posted')

    if user_id:
        stmt.where(user_id=user_id)

    def _to_relation_model(row):
        row = db.to_relation_model(row)
        if board_type == 'music':
            # since ipfs_file is related with music contracts, move ipfs_file row into music_contracts row.
            row['music_contract']['ipfs_file'] = [row['ipfs_file']]
            del row['ipfs_file']
        return row

    with db.engine_rdonly.connect() as connection:
        fetch_query_str = stmt.select(connection, execute=False, is_count_query=False)
        count_query_str = stmt.select(connection, execute=False, is_count_query=True)
        order_query_str = "ORDER BY `{}`.`post_id` DESC".format(db.statement._get_table_alias(table_name))

        return helper.response_ok(Pagination(
            connection=connection,
            fetch=fetch_query_str,
            count=count_query_str,
            order=order_query_str,
            current_page=page,
            fetch_params=stmt.fetch_params
        ).get_result(_to_relation_model))


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

    post_statement = db.Statement(table_name).set(user_id=user_id, title=title, content=content)
    contract_statement = None

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

        post_statement.set(genre=genre, youtube_video_id=youtube_video_id)
    elif board_type == 'music':
        pass

    with db.engine_rdwr.connect() as connection:
        post_id = post_statement.insert(connection).lastrowid

        if board_type == 'music':
            music_contract = json_form.get('music_contract')
            tx_hash = music_contract.get('tx_hash')

            # if tx_hash already in music contracts,
            tx_hash_exists = db.Statement(db.table.MUSIC_CONTRACTS).columns('"_"') \
                .where(tx_hash=tx_hash).limit(1).select(connection).fetchone()

            if tx_hash_exists:
                return helper.response_err(ER.TX_HASH_DUPLICATED, ER.TX_HASH_DUPLICATED_MSG)

            # if the board type is music, register IPFS files and contracts
            ipfs_file_id = ipfs.register_object(
                connection=connection,
                ipfs_hash=music_contract.get('ipfs_file_hash'),
                file_type=music_contract.get('file_type', 'music'),
                aes_key=music_contract.get('aes_key')
            )

            # update IPFS file info later
            tasks.ipfs_objects_update.delay(ipfs_file_id)

            contract_statement = db.Statement(db.table.MUSIC_CONTRACTS).set(
                ipfs_file_id=ipfs_file_id,
                tx_hash=tx_hash,
                post_id=post_id
            )

        if contract_statement is not None:
            contract_id = contract_statement.insert(connection).lastrowid

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

    if board_type == 'music':
        # if board type is music, show with related music contracts and IPFS file.
        additional_columns = """
            , '!music_contract', `mc`.*
        """
        inner_join = """
            LEFT JOIN `{}` `mc`
              ON (`mc`.`post_id` = `b`.`post_id`)
        """.format(db.table.MUSIC_CONTRACTS, db.table.IPFS_FILES)
    else:
        additional_columns = ''
        inner_join = ''

    post_query_statement = """
        SELECT `b`.* {} FROM `{}` `b`
        {}
        WHERE `b`.`post_id` = :post_id AND `b`.`status` = :status
    """.format(additional_columns, table_name, inner_join)

    ipfs_files_query_statement = """
        SELECT * FROM `ipfs_files` `if`
        INNER JOIN `music_contracts` `mc`
          ON (`mc`.`ipfs_file_id` = `if`.`file_id` OR `mc`.`ipfs_file_id` = `if`.`root_id`)
        WHERE `mc`.`post_id` = :post_id
    """

    tags_statement = db.Statement(db.table.tags(board_type)).columns('name').where(post_id=post_id)

    with db.engine_rdonly.connect() as connection:
        post = connection.execute(text(post_query_statement), post_id=post_id, status='posted').fetchone()

        # if the post does not exist,
        if post is None:
            return helper.response_err(ER.NOT_EXIST, ER.NOT_EXIST_MSG)
        post = db.to_relation_model(post)

        if board_type == 'music':
            ipfs_files = db.to_relation_model_list(
                connection.execute(text(ipfs_files_query_statement), post_id=post_id)
            )
            post['music_contract'].update({'ipfs_file': ipfs_files})

        tags = tags_statement.select(connection)

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
    statement = db.Statement(table_name) \
        .set(title=title, content=content) \
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
    elif board_type == 'music':
        # music post cannot change IPFS files since it already posted on the network.
        pass

    with db.engine_rdwr.connect() as connection:
        modified = statement.update(connection).rowcount

        # if the post does not exist or is not the user's post
        if not modified:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        current_tags = db.Statement(db.table.tags(board_type)).columns('name') \
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

    statement = db.Statement(table_name) \
        .set(status='deleted') \
        .where(post_id=post_id, user_id=user_id, status='posted')

    with db.engine_rdwr.connect() as connection:
        deleted = statement.update(connection).rowcount

        # if the post does not exist or is not the user's post
        if not deleted:
            return helper.response_err(ER.AUTHENTICATION_FAILED, ER.AUTHENTICATION_FAILED_MSG)

        return helper.response_ok({'status': 'success'})
