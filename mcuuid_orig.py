import hashlib

def hyphenate_uuid(uuid: str):
    hyphenated_uuid = uuid[:8] + '-' + uuid[8:12] + '-' + uuid[12:16] + '-' + uuid[16:20] + '-' + uuid[20:]
    return hyphenated_uuid


def uuid_to_array(uuid: str):
    if '-' in uuid:
        uuid = uuid.replace('-', '')
    
    res = list(range(4))

    for i in range(4):
        new_uuid = uuid[(i*8):((i+1)*8)]
        new_uuid = bytes.fromhex(new_uuid)
        new_uuid = int.from_bytes(bytes=new_uuid, byteorder='big', signed=True)
        res[i] = new_uuid

    return res

def get_offline_uuid(player: str, *, hyphenated: bool = True):
    base = f'OfflinePlayer:{player}'
    uuid = base.encode('utf-8')
    uuid = hashlib.md5(uuid)
    uuid = uuid.hexdigest()
    if hyphenated == True:
        uuid = hyphenate_uuid(uuid)
    return uuid

