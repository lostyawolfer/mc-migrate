from mc_migrate import *
from mc_migrate.mcmigrate import _parse_name
import unittest
# @unittest.expectedFailure


class UUIDTestCase(unittest.TestCase):
    def test_uuid_offline(self):
        # test uuids calculated by https://minecraft.wiki/w/Calculators/Player_UUID
        # test uuid arrays calculated by https://www.soltoder.com/mc-uuid-converter/
        test_names = ['Lostya', 'Provektork', 'MrOmega', 'N1llKigg8rs']
        test_uuids = ['ddad5688-add5-392c-b451-d25dc7bbb442', 'e2f8fc82-cbde-3e6f-884d-701e67a6c154', '490cf33f-d86f-3b7a-945b-ff22982fc136', '22eac90e-e2bb-37ec-b753-080985c43293']
        test_uuids_unhyphenated = ['ddad5688add5392cb451d25dc7bbb442', 'e2f8fc82cbde3e6f884d701e67a6c154', '490cf33fd86f3b7a945bff22982fc136', '22eac90ee2bb37ecb753080985c43293']
        test_lists = [[-575842680, -1378535124, -1269706147, -943999934], [-486998910, -874627473, -2008190946, 1738981716], [1225585471, -663798918, -1805910238, -1741700810], [585812238, -491046932, -1219295223, -2050739565]]

        for name, uuid, uuid_unhyphenated, parts in zip(test_names, test_uuids, test_uuids_unhyphenated, test_lists):
            uu = PlayerUUID(username=name, is_offline=True)
            assert uu.hyphenated() == uuid
            assert uu.hexdigest() == uuid_unhyphenated
            assert list(uu.intparts()) == list(parts)
    
    # @unittest.skip('reduce load on server')
    def test_uuid_online(self):
        names = {
            'Lostya': '6d88dcec-dd3a-475a-ba3b-544846a54cfa',
            'Provektork': '58d92483-a00b-40b2-bf18-dd3875d93410'
        }
        
        for name, exp_uuid in names.items():
            uu = PlayerUUID(username=name, is_offline=False)
            assert uu.hyphenated() == exp_uuid
        
        nonexistent = ['Lostya32843123123123', '=====']
        for name in nonexistent:
            with self.assertRaises(NotFoundError):
                uu = PlayerUUID(username=name, is_offline=False)


    def test_parse_username(self):
        opts = ['online:Lostya', 'offline:Provektork', 'Lostya']
        exps = [('Lostya', False), ('Provektork', True), ('Lostya', True)]

        for arg, exp in zip(opts, exps):
            res = _parse_name(arg)
            assert res == exp

        errs = [':Lostya', '', 'offline:']
        for err in errs:
            with self.assertRaises(Exception):
                res = _parse_name(err)

if __name__ == '__main__':
    unittest.main()