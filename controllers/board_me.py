from flask import Blueprint, request
from sqlalchemy import text

from modules import database as db
from modules.response import helper

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
