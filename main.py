import logging

from internal import arguments
from internal import compose

# TODO: Внутри crawler сделать нормальные декораторы
# TODO: из первого канала скачалось только 50 видео. А где остальные? Скорее всего они не скачались, т.к. у них нет субтитров


def main():
    args = arguments.parse()
    crawler = compose.build_crawler(**args)
    logging.basicConfig(
        format='%(asctime)-15s %(levelname)s [%(name)s]: %(message)s',
        filename=args['logging_filename']
    )

    with open(args['base_channels']) as fd:
        channel_ids = list(filter(lambda x: len(x) > 0, map(compose.sep_url, fd.readlines())))

    crawler.process(channel_ids)


if __name__ == '__main__':
    main()
