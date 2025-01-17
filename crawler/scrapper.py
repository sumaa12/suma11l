import logging

from crawler.loaders import Tab


class Scrapper:

    def __init__(self, loader, reloader, parsers=None):
        """
            Scrapper download concrete channel with (or without video) from Youtube.

            :param loader (object) : crawler.loaders.Loader
                This object must satisfy the interface `crawler.loaders.Loader`.
                Loader download and extract json with data from next pages:
                    * featured
                    * videos
                    * channels
                    * about
                    * TODO: community
                    * TODO: playlist (https://www.youtube.com/user/Sunfish737/playlists)
                If you want to add new pages, you should be add new constants int crawler.loaders.Tab
        """

        self.parsers = parsers if parsers is not None else []
        self.reloader = reloader
        self.loader = loader
        self.query_params = {
            Tab.HomePage: None,
            Tab.Videos: {'flow': 'grid', 'view': '0'},
            Tab.Channels: {'flow': 'grid', 'view': '56'},
            Tab.About: None,
        }

    def __reload_pages(self, p, next_page_token):
        descr_slice = []
        logging.info("reloading: %s" % p.tab.value)
        while not p.is_final_page() and next_page_token is not None:
            data_config = self.reloader.load(next_page_token)
            descr, next_page_token = p.parse(data_config, is_reload=True)
            descr_slice += descr
        logging.info("reloading was finished: %s" % p.tab.value)
        return descr_slice

    def parse(self, channel_id):
        descrs = {}
        for p in self.parsers:
            logging.info("loading: ******** %s ********" % p.tab.value)
            _, data_config = self.loader.load(channel_id, p.tab, self.query_params[p.tab])
            logging.info("loading was finished: %s" % p.tab.value)
            descr, next_page_token = p.parse(data_config, is_reload=False)
            descrs[p.tab] = descr + self.__reload_pages(p, next_page_token)
        return descrs
