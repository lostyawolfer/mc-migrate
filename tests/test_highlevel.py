import unittest
import pathlib as pth
import subprocess as sp
from types import SimpleNamespace
import mcuuid
from mcuuid import _main_process
# from mcuuid import main as mcmain

import os
import re

REGEX_BACKUP = r".*\.bak$"
TEST_PATH = '/home/lostya/projects/test-mc-server'
TEST_WRONG_PATH = TEST_PATH + '/world'

TEST_USERNAMES_UNSPECIF = ['Lostya', 'test1', 'test2', 'test3']
TEST_USERNAMES_ONLINE = ['online:Lostya', 'online:Provektork', 'online:SNOWMAN_HELLO', 'online:Diamond_Penguin_']
TEST_USERNAMES_ONLINE_NO = ['online:test1343r43rq4ewf', 'online:niufrwauifnu32iuh', 'online:N1ilaKir3tgers']
TEST_USERNAMES_OFFLINE = ['offline:Lostya', 'offline:test1', 'offline:test2', 'offline:test3']
TEST_USERNAMES_INVALID = ['on:line:Lostya', ':', '', 'AAaa:aaAA', '::::::', 'badline:Lostya']

def check_for_backups(expected: bool, error_message: str):
    res = not expected
    for f in os.listdir(TEST_PATH):
        if re.search(REGEX_BACKUP, f):
            res = not res
            break
    assert res, error_message



class HighLevelTest(unittest.TestCase):
    def main(self, **opts):
        basic = dict(
            world=None,
            server_dir=pth.Path(TEST_PATH),
            backup=None,
            cleanup=False,
            oldname=None,
            newname=None,
            quiet=True
        )
        basic.update(opts)
        opt = SimpleNamespace(basic)
        return _main_process(opt)

    def test_backup_creation(self):
        # Lostya -> test1 w/ backup
        self.main(oldname=TEST_USERNAMES_UNSPECIF[0], newname=TEST_USERNAMES_UNSPECIF[1], backup=True, quiet=False)
        check_for_backups(True, 'No backups were created when they should have')

        # cleaning up the created backups
        self.main(cleanup=True)
        check_for_backups(False, 'Backups have not been cleaned')

        # test1 -> Lostya w/o backup
        self.main(oldname=TEST_USERNAMES_UNSPECIF[1], newname=TEST_USERNAMES_UNSPECIF[0], backup=False)
        check_for_backups(False, error_message='Backups were created when they shouldn\'t have')
        

    def test_verbose(self):
        self.main(oldname=TEST_USERNAMES_OFFLINE[0], newname=TEST_USERNAMES_UNSPECIF[1], backup=True)
        self.main(oldname=TEST_USERNAMES_UNSPECIF[1], newname=TEST_USERNAMES_UNSPECIF[0], backup=True)
        self.main(oldname=TEST_USERNAMES_UNSPECIF[0], newname=TEST_USERNAMES_OFFLINE[1], backup=True)
        self.main(oldname=TEST_USERNAMES_UNSPECIF[1], newname=TEST_USERNAMES_UNSPECIF[0], backup=True)
        self.main(oldname=TEST_USERNAMES_OFFLINE[0], newname=TEST_USERNAMES_OFFLINE[1], backup=True)
        self.main(oldname=TEST_USERNAMES_UNSPECIF[1], newname=TEST_USERNAMES_ONLINE[0], backup=True)
        self.main(oldname=TEST_USERNAMES_ONLINE[0], newname=TEST_USERNAMES_OFFLINE[1], backup=True)
        self.main(oldname=TEST_USERNAMES_UNSPECIF[1], newname=TEST_USERNAMES_ONLINE[0], backup=True)
        self.main(oldname=TEST_USERNAMES_ONLINE[0], newname=TEST_USERNAMES_OFFLINE[0], backup=True)
        self.main(oldname=TEST_USERNAMES_OFFLINE[0], newname=TEST_USERNAMES_OFFLINE[0], backup=True)

        check_for_backups(True, 'No backups were created when they should have')

        # cleaning up the created backups
        self.main(cleanup=True)
        check_for_backups(False, 'Backups have not been cleaned')

        with self.assertRaises(Exception):
            self.main(oldname=TEST_USERNAMES_INVALID[0], newname=TEST_USERNAMES_INVALID[1])

        with self.assertRaises(Exception):
            self.main(oldname=TEST_USERNAMES_ONLINE_NO[0], newname=TEST_USERNAMES_ONLINE_NO[1])



    def test_onilne_to_online(self):
        with self.assertRaises(Exception):
            self.main(oldname=TEST_USERNAMES_ONLINE[0], newname=TEST_USERNAMES_ONLINE[1])

    def test_no_newname(self):
        with self.assertRaises(Exception):
            self.main(oldname=TEST_USERNAMES_UNSPECIF[0], newname=None)
    
    def test_server_dir(self):
        with self.assertRaises(Exception):
            self.main(server_dir=TEST_WRONG_PATH)
        
    def test_string_args(self):
        ...



class CmdTest(unittest.TestCase):
    def cmd(self, args):
        proc = pth.Path(mcuuid.__file__)      # path to script

        args = [str(proc)] + list(args)
        res = sp.run(args, capture_output=True, text=True, check=True)

        return res
    
    def test_cmd_cleanup(self):
        args = '-C', '-s', TEST_PATH, TEST_USERNAMES_UNSPECIF[1], TEST_USERNAMES_UNSPECIF[0]

        with self.assertRaises(sp.CalledProcessError) as exc:
            self.cmd(args)

