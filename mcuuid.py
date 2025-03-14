#!/usr/bin/env python3

from dataclasses import dataclass
import enum
import functools
import hashlib
import json
import nbtlib       # foreign
import pathlib as pth
import shutil
import sys
from typing import Optional
from urllib import request
from urllib.error import HTTPError

class NotFoundError(Exception):
    pass

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
        try:
            with request.urlopen(req) as conn:
                jsondata = conn.read()
        except HTTPError as exc:
            if exc.code == 404:
                raise NotFoundError(username)
            raise exc
        
        data = json.loads(jsondata)
        uuid = data['id']
        return bytes.fromhex(uuid)
    
    def __repr__(self):
        n = type(self).__name__
        return f'<{n}: {self.hyphenated()}, offline={self.is_offline}>'


def _parse_name(username: str, *, def_is_offline=True) -> tuple[str, bool]:
    """
    Returns a tuple of a form: (username, is_online)
    is_offline defaults to def_is_offline
    """

    parts = username.split(':', maxsplit=1)
    assert all(parts)       # none of parts is empty

    if len(parts) < 2:
        return parts[0], def_is_offline
    
    kind, name = parts
    kind = kind.lower()
    assert kind in ['offline', 'online'], 'kind must be "offline" or "online"'
    is_offline = (kind == 'offline')
    return name, is_offline


class ServerJson:
    file: pth.Path
    _parsed: list

    def __init__(self, file: pth.Path | str):
        self.file = pth.Path(file)
        assert self.file.is_file()

        # load
        with open(file, 'rb') as f:
            self._parsed = json.load(f)
    
    def rename_player(self, oldname: str, newname: str, is_new_offline: bool):
        for player in self._parsed:
            if player['name'] != oldname:
                continue        # continue search
            # found
            uu = PlayerUUID(username=newname, is_offline=is_new_offline)
            player['uuid'] = uu.hyphenated()
            player['name'] = newname
            return player['uuid']
        # not found
        raise NotFoundError('Player', oldname)
    
    def write(self, is_backup: bool=True):
        if is_backup:
            bkp = self.file.with_suffix(self.file.suffix + '.bak')
            shutil.copy2(self.file, bkp)
        with open(self.file, 'w') as f:
            json.dump(self._parsed, f)


def rename_server(oldname: str, newname: str, *, server_dir: pth.Path | str, is_backup: bool=True):
    server_dir = pth.Path(server_dir)
    assert server_dir.is_dir()

    oldname, _ = _parse_name(oldname)
    newname, newoffline = _parse_name(newname)

    server_files = [server_dir.joinpath(name) for name in 
        ['whitelist.json', 'usercache.json', 'ops.json', 'banned-players.json']]
    nrenames = []
    for file in server_files:
        j = ServerJson(file)
        try:
            j.rename_player(oldname=oldname, newname=newname, is_new_offline=newoffline)
        except NotFoundError:
            pass
        else:
            j.write(is_backup=is_backup)
            nrenames.append(file)
    if not nrenames:
        raise NotFoundError('Player', oldname)
    return nrenames


def rename(oldname: str, newname: str, *, world_dir: pth.Path | str, is_backup: bool=True):
    """
    oldname and newname must have format:
        'offline:PlayerName' or
        'online:PlayerName'
    When neither 'offline' or 'online' is given, 'offline' is assumed
    """
    bkp_fmt = '{orig}.{oldname}->{newname}.{newuuid}.bak'

    world_dir = pth.Path(world_dir)     # ensure
    assert world_dir.is_dir(), 'dir must be a directory'

    oldname, oldoffline = _parse_name(oldname)
    newname, newoffline = _parse_name(newname)
    assert not (oldoffline is False and newoffline is False), 'on->on is not sane'

    olduuid = PlayerUUID(username=oldname, is_offline=oldoffline)
    newuuid = PlayerUUID(username=newname, is_offline=newoffline)

    paths = ['playerdata/{uuid}.dat', 'playerdata/{uuid}.dat_old',
             'stats/{uuid}.json', 'advancements/{uuid}.json']
    paths_dirs = [world_dir.joinpath(p).parent for p in paths]
    assert all([p.is_dir() for p in paths_dirs]), 'dir structure mismatch'

    changed = []
    for path in paths:
        filename = path.format(uuid=olduuid.hyphenated())
        file = world_dir.joinpath(filename)
        if not file.exists():
            continue
        
        if is_backup:       # backup first
            newf = bkp_fmt.format(
                orig=file.name, oldname=oldname, newname=newname,
                newuuid=newuuid.hyphenated()
            )
            shutil.copy2(file, file.with_name(newf))
        
        newfile = file.rename(file.with_stem(newuuid.hyphenated()))
        changed.append(newfile)

        if file.suffix != '.dat':
            continue

        # apply changes inside dat
        with nbtlib.load(newfile) as nbt:
            nbt['UUID'] = nbtlib.IntArray(list(newuuid.intparts()))
            nbt.save()
    return changed

def _get_world_name(serverprops):
    with open(serverprops) as f:
        props = list(f)
    for prop in props:
        prop = prop.strip()
        if not prop.startswith('level-name='):
            continue
        name = prop[len('level-name='):]
        return name

def full_rename(oldname: str, newname: str, *,
                server_root: pth.Path | str,
                world_name: Optional[str]=None,
                is_backup: bool=True):
    server_root = pth.Path(server_root)
    assert server_root.is_dir()

    if world_name is None:
        world_name = _get_world_name(server_root.joinpath('server.properties'))

    world_dir = server_root.joinpath(world_name)    # type: ignore

    # TODO: output files after rename
    changed = rename(oldname=oldname, newname=newname, world_dir=world_dir, is_backup=is_backup)
    try:
        changed += rename_server(oldname=oldname, newname=newname, server_dir=server_root, is_backup=is_backup)
    except NotFoundError:
        pass
    return changed


def cleanup(server_dir: str | pth.Path, worldname: Optional[str]=None):
    server_dir = pth.Path(server_dir)
    assert server_dir.is_dir()

    if worldname is None:
        worldname = _get_world_name(server_dir.joinpath('server.properties'))
    
    world_dir = server_dir.joinpath(worldname)  # type: ignore

    subdirs = [server_dir]
    subdirs += [world_dir.joinpath(i) for i in [
        'playerdata', 'stats', 'advancements']]

    removed = []
    for subdir in subdirs:
        for file in subdir.glob('*.bak'):
            removed.append(file)
            file.unlink()
    
    return removed


def _main_process(parsed_args):
    opt = parsed_args
    if not opt.cleanup:     # make: rename player
        processed = full_rename(
            oldname=opt.oldname, newname=opt.newname,
            server_root=opt.server_dir,
            world_name=opt.world,
            is_backup=opt.backup
        )
        sup = ' (everything backed up)' if opt.backup else ''
        msg = f'Affected files{sup}:\n\t'
    else:                   # make: cleanup
        processed = cleanup(server_dir=opt.server_dir, worldname=opt.world)
        msg = 'Removed backups:\n\t'
    
    if not opt.quiet:
        print(processed)
        processed = [file.relative_to(opt.server_dir.parent) for file in processed]
        msg += '\n\t'.join(map(str, processed))
        print(msg)


def main(progname: str, *args):
    progname = pth.Path(progname).name

    import argparse
    import errno

    parser = argparse.ArgumentParser(
        prog=progname,
    )

    world_group = parser.add_mutually_exclusive_group()
    world_group.add_argument('-w', '--world',
        action='store', default=None,
        help='Name of the world directory (leave empty to retreive from server.properties)'
    )

    # world_group.add_argument('-W', '--world-dir',
    #     action='store', default=None, type=pth.Path,
    #     help='Absolute path to the world directory'
    # )

    parser.add_argument('-q', '--quiet',
        action='store', default='.', type=pth.Path,
        help='Do not show any messages'
    )

    parser.add_argument('-s', '--server-dir',
        action='store', default='.', type=pth.Path,
        help='Absolute path to server root directory'
    )

    parser.add_argument('--no-backup', dest='backup',
        action='store_false',
        help='Flag indicating no backups should be done'
    )

    parser.add_argument('-C', '--clear-backups', dest='cleanup',
        action='store_true',
        help='Clean directories, removing all backups'
    )

    _form = 'offline:PlayerName or online:PlayerName or just PlayerName (offline is assumed)'
    parser.add_argument('oldname', nargs='?',
        default=None,
        help=f'Current player name in form of {_form}'
    )

    parser.add_argument('newname', nargs='?',
        default=None,
        help=f'New player name in form of {_form}'
    )

    
    opt = parser.parse_args(args)
    #print('Parsed', vars(opt))

    err = None
    errnum = None
    if opt.cleanup and ((opt.oldname is not None) or (opt.newname is not None)):
        err, errnum = 'For cleanup action no names must be provided', errno.EINVAL
    if not opt.cleanup and (opt.oldname is None or opt.newname is None):
        err, errnum = 'Both names must be provided', errno.EINVAL
    

    try:
        _main_process(parsed_args=opt)
    except Exception as exc:
        err, errnum = f'{type(exc).__name__}: {str(exc)}', 1


    if err:
        msg = f'ERROR: {err}\nSee {progname} --help for details'
        raise Exception(msg, errnum)
    
    

if __name__ == '__main__':
    main(*sys.argv)