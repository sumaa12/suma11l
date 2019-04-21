import sqlite3

from crawler import parsers, utils
from crawler.cache import DBSqlLiteCache
from crawler.loaders import Loader, Reloader, YoutubeDlLoader, Tab
from crawler.scrapper import Scrapper
from crawler.simple_logger import SimpleLogger

import json


class YoutubeCrawler:
    # TODO: указано скачать не все видео, а только часть, то при повторной загрузке, будет выбран другой набор видео
    # TODO: Скрапер обкачивает k видео, а Crawler m из них может отбраковать, после чего не скачает новые k - m видео

    def __init__(self, logger=None, cache=None, ydl_loader=None, scraper=None, max_attempts=5):
        # TODO: переписать на StateMachine
        self.__max_attempts = max_attempts

        self.logger = logger
        if self.logger is None:
            self.logger = SimpleLogger()

        self.__cache = cache
        if self.__cache is None:
            self.__cache = DBSqlLiteCache()


        # conn = sqlite3.connect(self.__cache.db_path)
        #
        # res = conn.execute("select * from channels WHERE channel_id = 'UCzAzPC4VWIMHqrnIM1iBPsQ'")
        # res = res.fetchall()
        #
        # res = conn.execute("select * from videos where video_id = '77zRrFOuW0k'")
        # res = res.fetchall()
        #
        # res = conn.execute("UPDATE channels SET downloaded = 0 WHERE channel_id = 'UCzAzPC4VWIMHqrnIM1iBPsQ'")
        # res = res.fetchall()
        #
        # res = conn.execute("delete from videos where video_id = '77zRrFOuW0k'")
        # res = res.fetchall()
        #
        # res = conn.execute("select * from channels where channel_id = 'UCzAzPC4VWIMHqrnIM1iBPsQ'")
        # res = res.fetchall()
        #
        # res = conn.execute("select * from videos where video_id = '77zRrFOuW0k'")
        # res = res.fetchall()
        #
        # conn.commit()
        #
        # res = conn.execute("select * from channels where channel_id = 'UCzAzPC4VWIMHqrnIM1iBPsQ'")
        # res = res.fetchall()
        #
        # res = conn.execute("select * from videos where video_id = '77zRrFOuW0k'")
        # res = res.fetchall()
        # conn.close()

        self.__video_downloader = ydl_loader
        if self.__video_downloader is None:
            self.__video_downloader = YoutubeDlLoader()

        self.__scraper = scraper
        if self.__scraper is None:
            self.__init_none_scraper()

        self.__crash_msg = "Channel from Cache isn't got. %s: [%s]. Crawler interrupts execute..."

    def __init_none_scraper(self):
        loader = Loader()
        reloader = Reloader()
        scrapper = Scrapper(
            loader=loader, reloader=reloader,
            parsers=[
                parsers.HomePageParser(),
                parsers.VideosParser(max_page=10),
                parsers.ChannelsParser(max_page=3),
                parsers.AboutParser(),
            ],
            logger=self.logger
        )
        self.__scraper = scrapper

    def scrappy_decorator(self, fn, *args, **kwargs):
        count = 0
        e = None
        while count < self.__max_attempts:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                self.logger.warn(utils.CrawlerError(e=e, msg="problem into scrapper. retry: %d" % count))
                count += 1
        raise e

    @staticmethod
    def __create_video(video_id, channel_id, full_descr, short_descr):
        # TODO: заменить на алгоритмы valid и priority
        valid = True
        priority = 0

        if 'subtitles' in full_descr:
            del full_descr['subtitles']
        return {
            'video_id': video_id,
            'channel_id': channel_id,
            'full_description': json.dumps(full_descr),
            'short_description': json.dumps(short_descr),
            'valid': valid,
            'priority': priority
        }

    @staticmethod
    def __create_cur_channel(channel_id, full_descr, short_descr):
        # TODO: заменить на алгоритмы valid и priority
        priority = 0

        new_full_descr = {}
        if full_descr is not None:
            for k in full_descr:
                new_full_descr[k.value] = full_descr[k]

        return [{
            'channel_id': channel_id,
            'priority': priority,
            'full_description': json.dumps(new_full_descr) if new_full_descr is not None else None,
            'short_description': json.dumps(short_descr) if short_descr is not None else None,
        }]

    def __get_neighb_channels(self, descr):
        channels = []
        for channel in descr[Tab.Channels]:
            channels += self.__create_cur_channel(channel['channel_id'], None, channel)
        return channels

    def __set_failed_channel(self, channel_id):
        try:
            self.__cache.update_failed_channel(channel_id)
        except Exception as e:
            self.logger.alert(e)

    def __download_videos(self, descrs):
        channel_id = descrs[Tab.HomePage][0]['owner_channel']['id']
        for descr in descrs[Tab.Videos]:
            video_id = descr['id']

            # Check in Cache video_id
            if self.__cache.check_exist_video(video_id):
                self.logger.info("Such video already exist. VideoId: %s" % video_id)
                continue

            # Download video
            try:
                full_video_descr = self.scrappy_decorator(self.__video_downloader.load, video_id)
            except Exception as e:
                self.__cache.update_failed_video(video_id)
                self.logger.warn(e)
                continue

            data = self.__create_video(video_id, channel_id, full_video_descr, descr)
            try:
                self.__cache.insert_video_descr(data)
            except Exception as e:
                self.logger.alert(e)

    def process(self, channel_ids=None):
        if channel_ids is None:
            channel_ids = []
        if type(channel_ids) is not list:
            raise utils.CrawlerError("channel_ids is not list")
        self.logger.info("Setting channel ids from arguments into Cache")

        msg = None
        channel_id = None
        try:
            ch_ids_str = ','.join(channel_ids)
            msg = "Set base channels was failed. ChannelIds: %s" % ch_ids_str
            self.__cache.set_base_channels(channel_ids)
            # Getting first channel from Cache
            msg = "Problem with extracting Base channel"
            channel_id = self.__cache.get_best_channel_id()
        except Exception as e:
            self.logger.alert(utils.CrawlerError(e=e, msg=msg))
            # raise exception

        while channel_id is not None:
            self.logger.info("Scrappy channelId: %s" % channel_id)
            try:
                full_descr = self.scrappy_decorator(self.__scraper.parse, channel_id)
                # Extract full_descr
                channel = self.__create_cur_channel(channel_id, full_descr, None)
                # Setting current channel into Cache. ChannelId
                self.__cache.set_channels(channel, scrapped=True, valid=True)
            except Exception as e:
                self.__set_failed_channel(channel_id)
                self.logger.error(e)
                channel_id = self.__cache.get_best_channel_id()
                continue

            neighb_channels = None
            try:
                # Setting neighbours channels into Cache. ChannelId
                neighb_channels = self.__get_neighb_channels(full_descr)
                self.__cache.set_channels(neighb_channels, scrapped=False, valid=True)
            except Exception as e:
                ch_ids_str = ','.join([ch['id'] for ch in neighb_channels])
                e = utils.CrawlerError(e=e, msg=self.__crash_msg % ("ChannelIds", ch_ids_str))
                self.logger.error(e)

            # Downloading youtube for ChannelId
            try:
                self.__download_videos(full_descr)
            except Exception as e:
                msg = "Problem with downloaded videos." + self.__crash_msg % ("ChannelId", channel_id)
                e = utils.CrawlerError(e=e, msg=msg)
                self.logger.error(e)
                channel_id = self.__cache.get_best_channel_id()
                continue

            # Channel was downloaded
            try:
                self.__cache.update_channel_downloaded(channel_id)
            except Exception as e:
                msg = "Problem with update channelId" + self.__crash_msg % ("ChannelId", channel_id)
                e = utils.CrawlerError(e=e, msg=msg)
                self.logger.error(e)
                channel_id = self.__cache.get_best_channel_id()
                continue

            # Getting next channel from Cache
            channel_id = self.__cache.get_best_channel_id()
