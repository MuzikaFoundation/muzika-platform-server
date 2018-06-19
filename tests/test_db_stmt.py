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
        stmt = db.statement(db.table.USERS) \
            .inner_join(db.table.board('music'), 'user_id') \
            .where(user_id='3')
        self.assertDictEqual(stmt.fetch_params, {
            'where_u_user_id': '3'
        })

        query = pretty_sql(stmt.select(None, False))
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

    def test_update_with_where(self):
        stmt = db.statement(db.table.USERS) \
            .where(address='address') \
            .set(name='name')
        self.assertDictEqual(stmt.fetch_params, {
            'set_name': 'name',
            'where_address': 'address'
        })

        query = pretty_sql(stmt.update(None, False))
        self.assertEqual(query.strip(), pretty_sql("""
            UPDATE `users` SET name = :set_name WHERE address = :where_address
        """))

    def test_multiple_where_advanced(self):
        stmt = db.statement(db.table.USERS) \
            .inner_join(db.table.board('music'), 'user_id') \
            .inner_join(db.table.board('video'), 'user_id') \
            .where_advanced(db.table.board('music'), post_id=3) \
            .where_advanced(db.table.board('video'), post_id=5)
        self.assertDictEqual(stmt.fetch_params, {
            'where_mb_post_id': 3,
            'where_vb_post_id': 5
        })

        query = pretty_sql(stmt.select(None, False))
        self.assertEqual(query.strip(), pretty_sql("""
            SELECT `u`.* FROM `users` `u` 
            INNER JOIN `music_board` `mb` ON (`mb`.user_id = `u`.user_id) 
            INNER JOIN `video_board` `vb` ON (`vb`.user_id = `u`.user_id) 
            WHERE `mb`.post_id = :where_mb_post_id   AND `vb`.post_id = :where_vb_post_id
        """))
