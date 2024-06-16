import base64
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import js_to_json


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtp\.pt/play/p(?P<program_id>[0-9]+)/(?P<id>[^/?#]+)/?'
    _TESTS = [{
        'url': 'http://www.rtp.pt/play/p405/e174042/paixoes-cruzadas',
        'md5': 'e736ce0c665e459ddb818546220b4ef8',
        'info_dict': {
            'id': 'e174042',
            'ext': 'mp3',
            'title': 'Paixões Cruzadas',
            'description': 'As paixões musicais de António Cartaxo e António Macedo',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'http://www.rtp.pt/play/p831/a-quimica-das-coisas',
        'only_matching': True,
    }]

    _RX_OBFUSCATION = re.compile(r'''(?xs)
        atob\s*\(\s*decodeURIComponent\s*\(\s*
            (\[[0-9A-Za-z%,'"]*\])
        \s*\.\s*join\(\s*(?:""|'')\s*\)\s*\)\s*\)
    ''')

    __HEADERS = {
        'Referer': 'https://www.rtp.pt/',
        'Origin': 'https://www.rtp.pt',
        'Accept': '*/*',
        'Accept-Language': 'pt,en-US;q=0.7,en;q=0.3',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-GPC': '1',
    }

    def __unobfuscate(self, data, *, video_id):
        if data.startswith('{'):
            data = self._RX_OBFUSCATION.sub(
                lambda m: json.dumps(
                    base64.b64decode(urllib.parse.unquote(
                        ''.join(self._parse_json(m.group(1), video_id)),
                    )).decode('iso-8859-1')),
                data)
        return js_to_json(data)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta(
            'twitter:title', webpage, display_name='title', fatal=True)

        f, config = self._search_regex(
            r'''(?sx)
                var\s+f\s*=\s*(?P<f>".*?"|{[^;]+?});\s*
                var\s+player1\s+=\s+new\s+RTPPlayer\s*\((?P<config>{(?:(?!\*/).)+?})\);(?!\s*\*/)
            ''', webpage,
            'player config', group=('f', 'config'))

        f = self._parse_json(
            f, video_id,
            lambda data: self.__unobfuscate(data, video_id=video_id))
        config = self._parse_json(
            config, video_id,
            lambda data: self.__unobfuscate(data, video_id=video_id))

        formats = []
        if isinstance(f, dict):
            f_hls = f.get('hls')
            if f_hls is not None:
                formats.extend(self._extract_m3u8_formats(
                    f_hls, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', headers=self.__HEADERS))

            f_dash = f.get('dash')
            if f_dash is not None:
                formats.extend(self._extract_mpd_formats(
                    f_dash, video_id, mpd_id='dash', headers=self.__HEADERS))
        else:
            formats.append({
                'format_id': 'f',
                'url': f,
                'vcodec': 'none' if config.get('mediaType') == 'audio' else None,
            })

        subtitles = {}

        vtt = config.get('vtt')
        if vtt is not None:
            for lcode, lname, url in vtt:
                subtitles.setdefault(lcode, []).append({
                    'name': lname,
                    'url': url,
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': self._html_search_meta(['description', 'twitter:description'], webpage),
            'thumbnail': config.get('poster') or self._og_search_thumbnail(webpage),
            'subtitles': subtitles,
            'http_headers': self.__HEADERS,
        }
