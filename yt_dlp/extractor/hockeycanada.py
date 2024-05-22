import base64
import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    mimetype2ext,
    traverse_obj,
)


class HockeyCanadaIE(InfoExtractor):
    _VALID_URL = r'https://video.hockeycanada.ca/(en(?:-\w+)?|fr)/c/.+\.(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://video.hockeycanada.ca/en/c/nwt-micd-up-with-jamie-lee-rattray.107486',
        'only_matching': True,
    }, {
        # m3u8 + https
        'url': 'https://video.hockeycanada.ca/en-us/c/nwt-micd-up-with-jamie-lee-rattray.107486',
        'info_dict': {
            'id': '107486',
            'title': 'NWT: Mic’d up with Jamie Lee Rattray',
            'ext': 'mp4',
            'duration': 115,
            'timestamp': 1634310409,
            'upload_date': '20211015',
            'tags': ['English', '2021', "National Women's Team"],
            'description': 'md5:efb1cf6165b48cc3f5555c4262dd5b23',
            'thumbnail': str,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://video.hockeycanada.ca/en/c/mwc-remembering-the-wild-ride-in-riga.112307',
        'info_dict': {
            'id': '112307',
            'title': 'MWC: Remembering the wild ride in Riga',
            'ext': 'mp4',
            'duration': 322,
            'timestamp': 1716235607,
            'upload_date': '20240520',
            'tags': ['English', '2024', "National Men's Team", 'IIHF World Championship', 'Fan'],
            'description': 'md5:fa853281d3e8e0b1463166dc49e975b7',
            'thumbnail': str,
        },
        'params': {'skip_download': True},
    }, {
        # the same video in French
        'url': 'https://video.hockeycanada.ca/fr/c/cmm-retour-sur-un-parcours-endiable-a-riga.112304',
        'info_dict': {
            'id': '112304',
            'title': 'CMM : Retour sur un parcours endiablé à Riga',
            'ext': 'mp4',
            'duration': 322,
            'timestamp': 1716235545,
            'upload_date': '20240520',
            'tags': ['French', '2024', "National Men's Team", 'IIHF World Championship', 'Fan'],
            'description': 'md5:cf825222882a3dab1cd62cffcf3b4d1f',
            'thumbnail': str,
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_url = self._html_search_regex(
            r'content_api:\s*(["\'])(?P<url>.+?)\1', webpage, 'content api url', group='url')

        return {
            'id': video_id,
            'formats': [*self._yield_formats(data_url, video_id)],
            **self._search_json_ld(
                webpage.replace('/*<![CDATA[*/', '').replace('/*]]>*/', ''), video_id),
        }

    def _yield_formats(self, data_url, video_id):
        media_config = traverse_obj(
            self._download_json(data_url, video_id),
            ('config', {lambda x: json.loads(base64.b64decode(x).decode())}))

        for media_source in traverse_obj(media_config, ('media', 'source', ..., {dict})):
            media_url = traverse_obj(media_source, 'src')
            media_type = mimetype2ext(traverse_obj(media_source, 'type'))
            if media_type == 'm3u8':
                yield from self._extract_m3u8_formats(media_url, video_id)
            elif media_type == 'mp4':
                fmt = {
                    'url': media_url,
                    'ext': media_type,
                    'vcodec': 'avc1',
                    'acodec': 'mp4a.40.2',
                }
                if bitrate := self._search_regex(r'_(\d+)k\.mp4', media_url, 'bitrate', default=None):
                    fmt.update({
                        'format_id': f'http-{bitrate}',
                        'tbr': int_or_none(bitrate),
                    })
                yield fmt
            else:
                yield {
                    'url': media_url,
                    'ext': media_type,
                }
