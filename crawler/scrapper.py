from crawler.loaders import Tab


class Scrapper:
    """
    Scrapper download concrete channel with (or without video) from Youtube.

    loader : crawler.loaders.Loader
        This object must satisfy the interface `crawler.loaders.Loader`.
        Loader download and extract json with data from next pages:
            * featured
            * videos
            * channels
            * about
            * TODO: community
        If you want to add new pages, you should be add new constants int crawler.loaders.Tab
    """
    def __init__(self, loader, reloader, parsers=None, logger=None):

        self._parsers = parsers if parsers is not None else []
        self._reloader = reloader
        self._loader = loader

        self._logger = logger

        self._query_params = {
            Tab.HomePage: None,
            Tab.Videos: {'flow': 'grid', 'view': '0'},
            Tab.Channels: {'flow': 'grid', 'view': '56'},
            Tab.About: None,
        }

    def __reload_pages(self, p, next_page_token):
        count_pages = 1
        descr_slice = []
        while (p.max_page is None or count_pages < p.max_page) and next_page_token is not None:
            # TODO: добавить логгирование
            count_pages += 1
            data_config = self._reloader.load(next_page_token)
            descr, next_page_token = p.reload_parse(data_config)
            descr_slice += descr
        return descr_slice

    def parse(self, channel_id):
        # TODO: добавить логгирование
        descr = {}
        for p in self._parsers:
            player_config, data_config = self._loader.load(channel_id, p.tab, self._query_params[p.tab])
            descr, next_page_token = p.parse(player_config, data_config)
            descr[p.tab] = descr + self._reload_pages(p, next_page_token)
        return descr
