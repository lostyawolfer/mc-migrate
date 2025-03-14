import unittest
import pathlib as pth
from types import SimpleNamespace
from mcuuid import _main_process
# from mcuuid import main as mcmain

import os
import re

REGEX_BACKUP = r".*\.bak$"
TEST_PATH = '/home/lostya/projects/test-mc-server'
TEST_WRONG_PATH = TEST_PATH + '/world'

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
        self.main(oldname='Lostya', newname='test1', backup=True, quiet=False)
        check_for_backups(True, 'No backups were created when they should have')

        # cleaning up the created backups
        self.main(cleanup=True)
        check_for_backups(False, 'Backups have not been cleaned')

        # test1 -> Lostya w/o backup
        self.main(oldname='test1', newname='Lostya', backup=False)
        check_for_backups(False, error_message='Backups were created when they shouldn\'t have')
    
    def test_backup_cleanup(self):
        self.main(cleanup=True, world_dir='world')
        self.main(cleanup=True, world_dir=None)

        with self.assertRaises(Exception):
            self.main(oldname='Lostya', newname='test1', cleanup=True)


    def test_verbose(self):
        self.main(oldname='offline:Lostya', newname='test1', backup=True)
        self.main(oldname='test1', newname='Lostya', backup=True)
        self.main(oldname='Lostya', newname='offline:test1', backup=True)
        self.main(oldname='test1', newname='Lostya', backup=True)
        self.main(oldname='offline:Lostya', newname='offline:test1', backup=True)
        self.main(oldname='test1', newname='online:Lostya', backup=True)
        self.main(oldname='online:Lostya', newname='offline:test1', backup=True)
        self.main(oldname='test1', newname='online:Lostya', backup=True)
        self.main(oldname='online:Lostya', newname='offline:Lostya', backup=True)
        self.main(oldname='offline:Lostya', newname='offline:Lostya', backup=True)

        check_for_backups(True, 'No backups were created when they should have')

        # cleaning up the created backups
        self.main(cleanup=True)
        check_for_backups(False, 'Backups have not been cleaned')

        with self.assertRaises(Exception):
            self.main(oldname='abcd:Lostya', newname='efg:test1')

        with self.assertRaises(Exception):
            self.main(oldname='online:test789342580y73', newname='offline:test2')



    def test_onilne_to_online(self):
        with self.assertRaises(Exception):
            self.main(oldname='online:Lostya', newname='online:test1')

    def test_no_newname(self):
        with self.assertRaises(Exception):
            self.main(oldname='Lostya', newname=None)
    
    def test_server_dir(self):
        with self.assertRaises(Exception):
            self.main(server_dir=TEST_WRONG_PATH)