# coding: utf-8
from __future__ import unicode_literals

import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    traverse_obj,
    unified_strdate,
)


class GronkhIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/(?:watch/)?stream/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://gronkh.tv/stream/536',
        'info_dict': {
            'id': '536',
            'ext': 'mp4',
            'title': 'GTV0536, 2021-10-01 - MARTHA IS DEAD  #FREiAB1830  !FF7 !horde !archiv',
            'view_count': 19491,
            'thumbnail': 'https://01.cdn.vod.farm/preview/6436746cce14e25f751260a692872b9b.jpg',
            'upload_date': '20211001'
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://gronkh.tv/watch/stream/546',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://api.gronkh.tv/v1/video/info?episode={id}', id)
        m3u8_url = self._download_json(f'https://api.gronkh.tv/v1/video/playlist?episode={id}', id)['playlist_url']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, id)
        if data_json.get('vtt_url'):
            subtitles.setdefault('en', []).append({
                'url': data_json['vtt_url'],
                'ext': 'vtt',
            })
        self._sort_formats(formats)
        return {
            'id': id,
            'title': data_json.get('title'),
            'view_count': data_json.get('views'),
            'thumbnail': data_json.get('preview_url'),
            'upload_date': unified_strdate(data_json.get('created_at')),
            'formats': formats,
            'subtitles': subtitles,
        }


class GronkhFeedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/?(feed/?)?$'
    IE_NAME = 'gronkh:feed'

    _TESTS = [{
        'url': 'https://gronkh.tv/feed',
        'info_dict': {
            '_type': 'playlist',
            'id': 'feed',
            'title': 'feed',
            'description': 'feed',
        },
        'playlist_count': 16,
    }, {
        'url': 'https://gronkh.tv',
        'info_dict': {
            '_type': 'playlist',
            'id': 'feed',
            'title': 'feed',
            'description': 'feed',
        },
        'playlist_count': 16,
    }]

    def _real_extract(self, url):
        recent_info = traverse_obj(self._download_json('https://api.gronkh.tv/v1/video/discovery/recent', 'recent'),
                                   'discovery', default=[])
        views_info = traverse_obj(self._download_json('https://api.gronkh.tv/v1/video/discovery/views', 'views'),
                                  'discovery', default=[])

        def entries():
            for item in recent_info + views_info:
                if item:
                    yield self.url_result(f'https://gronkh.tv/watch/stream/{item.get("episode")}', GronkhIE,
                                          item.get('title'))

        return self.playlist_result(entries(), 'feed', 'feed', 'feed')


class GronkhVodsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/vods/streams/?$'
    IE_NAME = 'gronkh:vods'

    _TESTS = [{
        'url': 'https://gronkh.tv/vods/streams',
        'info_dict': {
            '_type': 'playlist',
            'id': 'vods',
            'title': 'vods',
            'description': 'vods',
        },
        'playlist_mincount': 150,
    }]
    _PER_PAGE = 25

    def _fetch_page(self, page):
        items = traverse_obj(self._download_json(
            f'https://api.gronkh.tv/v1/search?offset={self._PER_PAGE * page}&first={self._PER_PAGE}', 'vods',
            note=f'Downloading stream video page {page + 1}'), ('results', 'videos'), default=[])
        for item in items:
            if item:
                yield self.url_result(f'https://gronkh.tv/watch/stream/{item.get("episode")}', GronkhIE,
                                      item.get('title'))
        page += 1

    def _real_extract(self, url):
        entries = OnDemandPagedList(functools.partial(self._fetch_page), self._PER_PAGE)
        return self.playlist_result(entries, 'vods', 'vods', 'vods')
