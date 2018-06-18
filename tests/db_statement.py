import unittest

import sqlparse

from modules import database as db


def pretty_sql(sql):
    sql = sqlparse.format(sql.replace('\n', '').replace('  ', ' ').strip(),
                          reindent=True, keyword_case='upper').replace('\n', ' ')
    return sql


class DBStatementTest(unittest.TestCase):
    def test_select(self):
        """
        Test that db.statement test in select query
        """
        query = pretty_sql(
            db.statement(db.table.USERS)
                .where(user_id='3')
                .select(None, False)
        )
        self.assertEqual(query.strip(), 'SELECT * FROM `users` WHERE user_id = :where_user_id')

    def test_select_with_inner_join(self):
        """
        Test that db.statement inner join test in select query
        """
        query = pretty_sql(
            db.statement(db.table.USERS)
                .inner_join(db.table.board('music'), 'user_id')
                .where(user_id='3')
                .select(None, False)
        )
        self.assertEqual(query.strip(), pretty_sql("""
            SELECT `u`.* 
            FROM `users` `u` 
            INNER JOIN `music_board` `mb` ON (`mb`.user_id = `u`.user_id)
            WHERE `u`.user_id = :where_u_user_id
        """))

    def test_select_with_inner_join_and_columns(self):
        """
        Test that db.statement joined column in select query
        """
        query = pretty_sql(
            db.statement(db.table.USERS)
                .columns((db.table.board('music'), 'post_id'))
                .inner_join(db.table.board('music'), 'user_id')
                .where(user_id='3')
                .select(None, False)
        )
        self.assertEqual(query.strip(), pretty_sql("""
            SELECT `mb`.post_id
            FROM `users` `u` 
            INNER JOIN `music_board` `mb` ON (`mb`.user_id = `u`.user_id)
            WHERE `u`.user_id = :where_u_user_id
        """))

    def test_select_multiple_inner_join(self):
        query = pretty_sql(
            db.statement(db.table.board('music'))
                .columns('*', '!music_contract', (db.table.MUSIC_CONTRACTS, '*'))
                .inner_join(db.table.MUSIC_CONTRACTS, 'post_id')
                .left_join((db.table.MUSIC_PAYMENTS, db.table.MUSIC_CONTRACTS), 'contract_address')
                .where(post_id='5')
                .select(None, False)
        )

        self.assertEqual(query.strip(), pretty_sql("""
            SELECT `mb`.*, '!music_contract', `mc`.* 
            FROM `music_board` `mb` 
            INNER JOIN `music_contracts` `mc` ON (`mc`.post_id = `mb`.post_id) 
            LEFT JOIN `music_payments` `mp` ON (`mp`.contract_address = `mc`.contract_address) 
            WHERE `mb`.post_id = :where_mb_post_id 
        """))

    # def _db_orm_statement():
    #     """
    #         @example
    #
    #         :SQL
    #         SELECT
    #           `mb`.*,
    #           '!music_contract', `mc`.*,
    #           '!music_payment',  `mp`.*
    #         FROM `music_board` `mb`
    #         INNER JOIN `music_contracts` `mc` ON (`mc`.`post_id` = `mb`.`post_id`)
    #         INNER JOIN `music_payments` `mp` ON (`mp`.`contract_address` = `mc`.`contract_address`)
    #         WHERE `mp`.`buyer_address` = :buyer_address
    #         ORDER BY `mc`.`contract_address`
    #
    #         :ORM
    #         query = db.statement(db.table.board('music')) \
    #         .columns('*',
    #                  '!music_contract', (db.table.MUSIC_CONTRACTS, '*'),
    #                  '!music_payment', (db.table.MUSIC_PAYMENTS, '*')) \
    #         .inner_join(db.table.MUSIC_CONTRACTS, 'post_id') \
    #         .inner_join((db.table.MUSIC_PAYMENTS, db.table.MUSIC_CONTRACTS), 'contract_address')
    #         .where_advanced(db.table.MUSIC_PAYMENTS, 'buyer_address')
    #         .select(connect)
    #     """
    #
    #     return helper.response_ok({
    #         'user_select': pretty_sql(
    #             db.statement(db.table.USERS)
    #                 .set(user_id='5')
    #                 .where(user_id='3')
    #                 .select(None, False)
    #         ),
    #
    #         'user_select_with_join_and_order': pretty_sql(
    #             db.statement(db.table.board('music'))
    #                 .where(post_id='5')
    #                 .inner_join(db.table.USERS, 'user_id')
    #                 .order((db.table.USERS, 'contract_address'), 'desc')
    #                 .select(None, False)
    #         ),
    #
    # 'multiple_join_with_cross_table': pretty_sql(
    #     db.statement(db.table.board('music'))
    #         .columns('*', '!music_contract', (db.table.MUSIC_CONTRACTS, '*'))
    #         .inner_join(db.table.MUSIC_CONTRACTS, 'post_id')
    #         .left_join((db.table.MUSIC_CONTRACTS, db.table.MUSIC_PAYMENTS), 'contract_address')
    #         .where(post_id='5')
    #         .order((db.table.USERS, 'address'), 'desc')
    #         .select(None, False)
    # )

# })
