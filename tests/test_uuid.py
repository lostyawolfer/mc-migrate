from mcuuid import *
import unittest
# @unittest.expectedFailure


class UUIDTestCase(unittest.TestCase):
    def test_uuid(self):
        # test uuids calculated by https://minecraft.wiki/w/Calculators/Player_UUID
        # test uuid arrays calculated by https://www.soltoder.com/mc-uuid-converter/
        test_names = ['Lostya', 'Provektork', 'MrOmega', 'N1llKigg8rs']
        test_uuids = ['ddad5688-add5-392c-b451-d25dc7bbb442', 'e2f8fc82-cbde-3e6f-884d-701e67a6c154', '490cf33f-d86f-3b7a-945b-ff22982fc136', '22eac90e-e2bb-37ec-b753-080985c43293']
        test_lists = [[-575842680, -1378535124, -1269706147, -943999934], [-486998910, -874627473, -2008190946, 1738981716], [1225585471, -663798918, -1805910238, -1741700810], [585812238, -491046932, -1219295223, -2050739565]]

        for name, uuid, parts in zip(test_names, test_uuids, test_lists):
            uu = PlayerUUID(username=name, is_offline=True)
            assert uu.hyphenated() == uuid
            assert list(uu.intparts()) == list(parts)

if __name__ == '__main__':
    unittest.main()