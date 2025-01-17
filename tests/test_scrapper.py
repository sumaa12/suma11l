import logging
from collections import Counter

from crawler.scrapper import Scrapper
from tests import MockTab
from tests.utils import BaseTestClass, SubTest


class MockClientServer:
    def __init__(self, available_pages=None):
        self.available_pages = {} if available_pages is None else available_pages
        self.tabs = Counter()

    def is_cur_page_last(self, tab):
        if tab not in self.available_pages:
            raise Exception()
        if self.tabs[tab] + 1 >= self.available_pages[tab]:
            return True
        self.tabs[tab] += 1
        return False


class MockLoader:
    def __init__(self, client):
        self.client = client

    def load(self, channel_id, tab, query_params):
        token = None
        if not self.client.is_cur_page_last(tab):
            token = tab
        return {'Player': True}, {'Token': token}


class MockReloader:
    def __init__(self, client):
        self.client = client

    def load(self, next_page_token):
        token = None
        if not self.client.is_cur_page_last(next_page_token):
            token = next_page_token
        return {'Token': token}


class MockParser:
    def __init__(self, tab, max_pages):
        self.tab = tab
        self.max_page = max_pages
        self.__count_pages = 0

    def is_final_page(self):
        return not (self.max_page is None or self.__count_pages < self.max_page)

    def parse(self, data_config, is_reload=False):
        self.__count_pages += 1
        return [{'is_reload': is_reload, 'data_config': data_config}], data_config['Token']


class TestScrapper(BaseTestClass):
    """
    Token stores information about next page. We have loader and reloader
    which connect to server. Server has limited available pages. If server
    still has pages yet, then it return token else server return None.
    This token send to reloader and reloader return new page with token or
    not.
    """

    @staticmethod
    def __create_scrapper(available_pages, max_pages):
        client = MockClientServer(available_pages=available_pages)
        scrapper = Scrapper(
            loader=MockLoader(client),
            reloader=MockReloader(client),
            parsers=[MockParser(tab=tab, max_pages=max_pages[tab]) for tab in max_pages],
        )
        for k in max_pages:
            scrapper.query_params[k] = k
        return scrapper

    def setUp(self):
        logging.getLogger().setLevel(logging.CRITICAL)
        channel_id = "test_channel"

        self.tests = [
            # There are not parsers
            SubTest(
                name="Test 1",
                description="There aren't any parsers. Function does execute and return after that",
                configuration={'available_pages': [], 'max_pages': []},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={},
                    max_pages={},
                ),
                want={},
                exception=None,
            ),
            # One parsers
            SubTest(
                name="Test 2",
                description="One parser",
                configuration={'available_pages': [1], 'max_pages': [1]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 1},
                    max_pages={MockTab.TEST0: 1},
                ),
                want={
                    MockTab.TEST0: [{'is_reload': False, 'data_config': {'Token': None}}]
                },
                exception=None,
            ),
            SubTest(
                name="Test 3",
                description="One parser",
                configuration={'available_pages': [1], 'max_pages': [2]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 1},
                    max_pages={MockTab.TEST0: 2},
                ),
                want={
                    MockTab.TEST0: [{'is_reload': False, 'data_config': {'Token': None}}]
                },
                exception=None,
            ),
            SubTest(
                name="Test 4",
                description="One parser",
                configuration={'available_pages': [2], 'max_pages': [2]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 2},
                    max_pages={MockTab.TEST0: 2},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 5",
                description="One parser",
                configuration={'available_pages': [2], 'max_pages': [3]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 2},
                    max_pages={MockTab.TEST0: 3},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 6",
                description="One parser",
                configuration={'available_pages': [3], 'max_pages': [2]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 3},
                    max_pages={MockTab.TEST0: 2},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST0}},
                    ]
                },
                exception=None,
            ),
            # # Two parsers
            SubTest(
                name="Test 7",
                description="Two parser. The same configuration",
                configuration={'available_pages': [1, 1], 'max_pages': [1, 1]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 1, MockTab.TEST1: 1},
                    max_pages={MockTab.TEST0: 1, MockTab.TEST1: 1},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': None}},
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': None}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 8",
                description="Two parser. The same configuration",
                configuration={'available_pages': [1, 1], 'max_pages': [2, 2]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 1, MockTab.TEST1: 1},
                    max_pages={MockTab.TEST0: 2, MockTab.TEST1: 1},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': None}}
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': None}}
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 9",
                description="Two parser. The same configuration",
                configuration={'available_pages': [2, 2], 'max_pages': [2, 2]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 2, MockTab.TEST1: 2},
                    max_pages={MockTab.TEST0: 2, MockTab.TEST1: 2},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 10",
                description="Two parser. The same configuration",
                configuration={'available_pages': [2, 2], 'max_pages': [3, 3]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 2, MockTab.TEST1: 2},
                    max_pages={MockTab.TEST0: 3, MockTab.TEST1: 3},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 11",
                description="Two parser. The same configuration",
                configuration={'available_pages': [3, 3], 'max_pages': [2, 2]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 3, MockTab.TEST1: 3},
                    max_pages={MockTab.TEST0: 2, MockTab.TEST1: 2},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST0}},
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST1}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 12",
                description="Two parser. Different configuration",
                configuration={'available_pages': [3, 4], 'max_pages': [2, 4]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 3, MockTab.TEST1: 4},
                    max_pages={MockTab.TEST0: 2, MockTab.TEST1: 4},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST0}},
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ]
                },
                exception=None,
            ),
            SubTest(
                name="Test 13",
                description="Three parser",
                configuration={'available_pages': [3, 4, 1], 'max_pages': [2, 4, 1]},
                args={'channel_id': channel_id},
                object=self.__create_scrapper(
                    available_pages={MockTab.TEST0: 3, MockTab.TEST1: 4, MockTab.TEST2: 1},
                    max_pages={MockTab.TEST0: 2, MockTab.TEST1: 4, MockTab.TEST2: 1},
                ),
                want={
                    MockTab.TEST0: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST0}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST0}},
                    ],
                    MockTab.TEST1: [
                        {'is_reload': False, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': MockTab.TEST1}},
                        {'is_reload': True, 'data_config': {'Token': None}},
                    ],
                    MockTab.TEST2: [
                        {'is_reload': False, 'data_config': {'Token': None}},
                    ],
                },
                exception=None,
            ),
        ]

    def test_parse(self):
        for test in self.tests:
            self.apply_test(test, lambda obj, kwargs: obj.parse(**kwargs))
