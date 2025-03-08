import enum
import functools
import hashlib
import json
from typing import Optional
from urllib import request

class HashVariant(enum.IntEnum):
    """
    0xx is the "variant 0" of Apollo NCS 1.5, an old type of UUID.
    10x is the "variant 1" of IETF RFC 4122 (Leach-Salz). It's referred to as "variant 2" by Java.
    110 is the "variant 2" of old Microsoft products. It's referred to as "variant 6" by Java.
    111 is the "reserved variant". It's referred to as "variant 7" by Java.
    """

    VAR0 = 0
    VAR1 = 1
    VAR2 = 2
    VAR_RESERVED = 3


class MCUUID:
    __slots__ = ('hash', )

    def __init__(self, data: str, *, scope: Optional[str]=None):
        if scope is not None:
            data = f'{scope}:{data}'
        
        d = data.encode('utf-8')
        hash = hashlib.md5(d).digest()
        hash = self.fix_hash(hash)
        self.hash = hash

    @staticmethod
    def fix_hash(hash: bytes, version: int=4, variant: HashVariant | int=HashVariant.VAR1):
        variant = HashVariant(variant)
        assert 1 <= version <= 4, 'Version mismatch'

        # patch hash with A & B, per https://minecraft.fandom.com/wiki/Universally_unique_identifier#Hyphenated_hexadecimal_format_section_names
        #   A in position of 12th symbol = 12/2 = 6th byte
        #   B in position of 16th symbol = 16/2 = 8th byte
        data = bytearray(hash)      # make it mutable for easier changes
        data[6] = (data[6] & (0xFF >> 4)) | ((version - 1)  << 4)

        # tonull = [0x7f, 0x3f, 0x1f, 0x1f][variant]
        # tonull = [0b01111111, 0b00111111, 0b00011111, 0b00011111][variant]
        tonull = (0xFF >> variant + 1) | 0xFF >> 3
        # toset = [0b00000000, 0b10000000, 0b11000000, 0b11100000][variant]
        # toset = [0x0, 0x80, 0xc0, 0xe0][variant]
        toset = ~(0xFF >> variant) & 0xFF

        data[8] = (data[8] & tonull) | toset 

        return bytes(data)
    
    def digest(self):
        return self.hash
    
    def hexdigest(self, hyphenated: bool=False):
        hex = self.digest().hex()
        if hyphenated:
            parts = hex[:8], hex[8:12], hex[12:16], hex[16:20], hex[20:]
            hex = '-'.join(parts)
        
        return hex
    
    def hyphenated(self):
        return self.hexdigest(hyphenated=True)
    
    def intparts(self):
        digest = self.digest()

        for i in range(len(digest) // 4):
            part, digest = digest[:4], digest[4:]
            intpart = int.from_bytes(part, byteorder='big', signed=True)
            yield intpart
    
    def __repr__(self):
        # TODO: refactor
        n = type(self).__name__
        return f'<{n}: {self.hyphenated()}>'


class PlayerUUID(MCUUID):
    # format-string
    API_ENDPOINT = 'https://api.minecraftservices.com/minecraft/profile/lookup/name/{username}'
    
    __slots__ = MCUUID.__slots__ + ('is_offline', )     # slots not inherited

    def __init__(self, username: str, *, is_offline: bool=True):
        if is_offline:
            super().__init__(data=username, scope='OfflinePlayer')
        else:
            uuid = self.request_uuid(username=username)
            self.hash = uuid

        self.is_offline = is_offline

    @classmethod
    @functools.lru_cache()
    def request_uuid(cls, username: str):
        url = cls.API_ENDPOINT.format(username=username)

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0',
        }

        req = request.Request(url=url, headers=headers)
        with request.urlopen(req) as conn:
            jsondata = conn.read()
        
        data = json.loads(jsondata)
        uuid = data['id']
        return bytes.fromhex(uuid)
    
    def __repr__(self):
        n = type(self).__name__
        return f'<{n}: {self.hyphenated()}, offline={self.is_offline}>'



if __name__ == '__main__':
    val = 0b11001110

    # for variant in list(HashVariant):
    #     tonull = (0xFF >> variant + 1) | 0xFF >> 3
    #     print(variant, '{:0>8}'.format(bin(tonull)[2:]))