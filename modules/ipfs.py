
import ipfsapi
from sqlalchemy import text

from config import IPFSConfig
from modules import database as db


class RelayIpfs:
    """
    Relay IPFS is a IPFS node that spreads the artists' papers. Since IPFS node in the browser doesn't spread the file
    itself, this helps the clients(artists) uploaded files to be spread out more rapidly.
    """
    def __init__(self):
        self.api = ipfsapi.connect(IPFSConfig.node_address, IPFSConfig.port)

    def get_connection(self):
        return self.api


def register_object(connection, ipfs_hash, file_type, aes_key=None, name=None, tracking=False, **kwargs):
    ipfs_object = {
        'file_type': file_type,
        'ipfs_hash': ipfs_hash,
        'encrypted': True if aes_key else False,
        'name': name,
        'status': 'pending'
    }

    ipfs_file_id = db.Statement(db.table.IPFS_FILES).set(
        file_type=file_type,
        ipfs_hash=ipfs_hash,
        encrypted=True if aes_key else False,
        name=name,
        status='pending'
    ).insert(connection).lastrowid

    # if encrypted, add AES key to the private table
    if aes_key:
        db.Statement(db.table.IPFS_FILES_PRIVATE).set(
            file_id=ipfs_file_id,
            aes_key=aes_key
        ).insert(connection)

    if tracking:
        ipfs_object.update({'file_id': ipfs_file_id})
        if aes_key:
            ipfs_object.update({'aes_key': aes_key})
        track_object(connection, ipfs_object=ipfs_object, **kwargs)

    return ipfs_file_id


def track_object(connection, ipfs_file_id=None, ipfs_object=None, **kwargs):
    if ipfs_file_id:
        object_query = """
            SELECT `f`.*, `p`.`aes_key`  FROM `{}` `f`
            INNER JOIN `{}` `p`
            ON (`f`.`file_id` = `p`.`file_id`)
            WHERE `f`.`file_id` = :ipfs_file_id
            LIMIT 1
        """.format(db.table.IPFS_FILES, db.table.IPFS_FILES_PRIVATE)

        ipfs_object = connection.execute(text(object_query), ipfs_file_id=ipfs_file_id).fetchone()

        # if object does not exist
        if not ipfs_object:
            return

        ipfs_object = db.to_relation_model(ipfs_object)

    ipfs_file_id = ipfs_object['file_id']
    root_ipfs_hash = ipfs_object['ipfs_hash']
    file_type = ipfs_object['file_type']
    aes_key = ipfs_object.get('aes_key')
    name = ipfs_object.get('name', '')
    root_id = kwargs.get('root_id') or ipfs_file_id

    if name == '/' or name is None:
        name = ''

    ipfs = RelayIpfs().get_connection()

    try:
        # query object links. If timeout, it will raise Timeout Error
        object_links = ipfs.ls(root_ipfs_hash, opts={
            'timeout': kwargs.get('timeout', '30s')
        })['Objects'][0]['Links']
    except ipfsapi.exceptions.ErrorResponse:
        # if timeout error, set status to "disabled"
        db.Statement(db.table.IPFS_FILES)\
            .set(status='disabled')\
            .where(file_id=ipfs_file_id)\
            .update(connection)
        return

    # if no object links, this object is just a file
    if not len(object_links):
        db.Statement(db.table.IPFS_FILES)\
            .set(ipfs_object_type='file', root_id=root_id, status='success')\
            .where(file_id=ipfs_file_id)\
            .update(connection)

    # if having object links, this object is a directory and insert files
    else:
        db.Statement(db.table.IPFS_FILES)\
            .set(ipfs_object_type='directory', root_id=root_id, name=name if name else '/', status='success')\
            .where(file_id=ipfs_file_id)\
            .update(connection)

        for link in object_links:
            link_object = {
                'parent_id': ipfs_file_id,
                'file_type': file_type,
                'ipfs_hash': link['Hash'],
                'encrypted': True if aes_key else False,
                'name': '/'.join([name, link['Name']]),
                'root_id': root_id
            }

            # if the linked object is directory
            if link['Type'] == 1:
                link_object.update({
                    'ipfs_object_type': 'directory',
                    'status': 'pending'
                })

                # track recursively
                # track_object(connection, ipfs_object=link_object, **kwargs)

            # if the linked object is file (Type == 2)
            else:
                link_object.update({
                    'file_size': link['Size'],
                    'ipfs_object_type': 'file',
                    'status': 'success'
                })

                # db.Statement(db.table.IPFS_FILES).set(**link_object).insert(connection)

            # insert an directory object in this IPFS object
            link_object.update({
                'file_id': db.Statement(db.table.IPFS_FILES).set(**link_object).insert(connection).lastrowid
            })

            # if aes_key exists, insert AES KEY into the private table
            if aes_key:
                db.Statement(db.table.IPFS_FILES_PRIVATE)\
                    .set(file_id=link_object['file_id'], aes_key=aes_key)\
                    .insert(connection)
                link_object.update({'aes_key': aes_key})

            # if directory, track recursively
            if link['Type'] == 1:
                kwargs.update({'root_id': root_id})
                track_object(connection, ipfs_object=link_object, **kwargs)


def translate_contract(connection, contract_id=None):
    """
    Reads the meta.json file in the contract file and translate it.
    """
    ipfs_object_stmt = """
        SELECT `if`.* FROM `ipfs_files` `if`
        INNER JOIN `music_contracts` `mc`
          ON (`if`.`file_id` = `mc`.`ipfs_file_id`)
        WHERE `mc`.`contract_id` = :contract_id
        LIMIT 1
    """

    ipfs_object = connection.execute(text(ipfs_object_stmt), contract_id=contract_id).fetchone()

    if not ipfs_object:
        raise ValueError('ipfs object does not exist.')

    import requests

    root_hash = ipfs_object['ipfs_hash']
    meta_query_url = 'https://ipfs.io/ipfs/{root_hash}/meta.json'.format(root_hash=root_hash)
    req = requests.get(meta_query_url)

    if req.status_code != 200:
        raise ValueError('cannot find meta file')

    db.statement(db.table.MUSIC_CONTRACTS).set(meta=req.text).where(contract_id=contract_id).update(connection)