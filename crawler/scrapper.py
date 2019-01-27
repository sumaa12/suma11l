from crawler import parsers
from crawler.loaders import Loader


class Scrapper:
    """
    Scrapper download concrete channel with (or without video) from Youtube.

    loader : crawler.loaders.Loader
        This object must satisfy the interface `crawler.loaders.Loader`.
        Loader download and extract json with data from next pages:
            * featured
            * videos
            * community
            * channels
            * about
        If you want to add new pages, you should be add new constants int crawler.loaders.Tab
    """
    def __init__(self, loader, parsers=None, logger=None, channel_descr_dumper=None, hard=True, channel_filter=None):
        self._hard = hard

        self._parsers = parsers if parsers is not None else []
        self._loader = loader
        self._channel_descr_dumper = channel_descr_dumper
        self._channel_filter = channel_filter

        self._logger = logger

    def _page_process(self, p, player_config, data_config):
        count_pages = 0
        channel_descr = []
        while True:
            count_pages += 1
            descr, next_page_token = p.parse(player_config, data_config)
            channel_descr.append(descr)
            if count_pages >= p.max_page_token or len(next_page_token) == 0:
                break
            player_config, data_config = self._loader.reload_page(next_page_token)
        return channel_descr

    def _dump(self, descr):
        with open(descr, 'w') as fd:
            self._channel_descr_dumper.dump(fd, descr)

    def parse(self, channel_id):
        channel_descr = {}
        for p in self._parsers:
            player_config, data_config = self._loader.load_page(channel_id, p.tab)
            channel_descr[p.tab] = self._page_process(p, player_config, data_config)

    def download(self, channel_id, descr_videos):
        # TODO: реализовать обкачку видео, инорфмацию по которым скачали
        # TODO: логгировать все статусы обкачки для того, чтобы можно было возобновить обкачку с прежнего места
        pass


channel_id = 'UCSoYSTOt1g_Vdo8xCJeQpHw'
l = Loader()
Scrapper(l, [
    parsers.HomePageParser(),
    parsers.VideosParser(),
    parsers.ChannelsParser(),
    parsers.AboutParser(),
]).parse(channel_id)