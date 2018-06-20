from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.login import jwt_check
from modules.response import helper
from modules.response.error import ERR

from modules.pagination import Pagination

blueprint = Blueprint('board_me', __name__, url_prefix='/api')


@blueprint.route('/board/music/purchased', methods=['GET'])
def _get_my_upload_board():
    buyer_address = request.args.get('buyer_address')
    with db.engine_rdonly.connect() as connect:
        query_str = """
            SELECT 
              `mb`.*, 
              '!music_contract', `mc`.*,
              '!music_payment',  `mp`.*
            FROM `music_board` `mb`
            INNER JOIN `music_contracts` `mc` ON (`mc`.`post_id` = `mb`.`post_id`)
            INNER JOIN `music_payments` `mp` ON (`mp`.`contract_address` = `mc`.`contract_address`)
            WHERE `mp`.`buyer_address` = :buyer_address 
            ORDER BY `mc`.`contract_address`
        """

        query = connect.execute(text(query_str), buyer_address=buyer_address)

        return helper.response_ok([db.to_relation_model(row) for row in query])


@blueprint.route('/user/board/<board_type>', methods=['GET'])
@jwt_check
def _get_my_post(board_type):
    """
    Gets board posts for the user. If the board type is music, it also shows the posts that have un-mined contracts
    unlike the GET "/api/board/<board_type>" API.
    :param board_type: the type of posts to list.
    """
    table_name = db.table.board(board_type)
    user_id = request.user['user_id']
    page = request.args.get('page', 1)

    if not table_name:
        return helper.response_err(ERR.INVALID_REQUEST_BODY)

    from modules import board

    stmt = board.posts_query_stmt(board_type)
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
        order_query_str = "ORDER BY `{}`.`post_id` DESC".format(db.statement.get_table_alias(table_name))

        return helper.response_ok(Pagination(
            connection=connection,
            fetch=fetch_query_str,
            count=count_query_str,
            order=order_query_str,
            current_page=page,
            fetch_params=stmt.fetch_params
        ).get_result(_to_relation_model))
