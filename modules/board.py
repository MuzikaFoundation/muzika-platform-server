
from modules import database as db


def posts_query_stmt(board_type, **kwargs):
    """
    Returns a statement for querying board posts.
    :param board_type: the type of the posts for querying.
    :return: a statement instance for querying board posts.
    """
    table_name = db.table.board(board_type)
    user_id = kwargs.get('user_id')

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

    if user_id and isinstance(user_id, int):
        stmt.where(user_id=user_id)

    return stmt
