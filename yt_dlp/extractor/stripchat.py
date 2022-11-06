from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    ExtractorError,
    lowercase_escape,
    traverse_obj,
)


class StripchatIE(InfoExtractor):
    _VALID_URL = r'https?://stripchat\.com/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://stripchat.com/feel_me',
        'info_dict': {
            'id': 'feel_me',
            'ext': 'mp4',
            'title': 're:^feel_me [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': str,
            'is_live': True,
            'age_limit': 18,
        },
        'skip': 'Room is offline',
    }, {
        'url': 'https://stripchat.com/Rakhijaan@xh',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers=self.geo_verification_headers())

        data = self._parse_json(
            self._search_regex(
                r'<script\b[^>]*>\s*window\.__PRELOADED_STATE__\s*=(?P<value>.*?)<\/script>',
                webpage, 'data', default='{}', group='value'),
            video_id, transform_source=lowercase_escape, fatal=False)
        if not data:
            raise ExtractorError('Unable to find configuration for stream.')

        if traverse_obj(data, ('viewCam', 'show'), expected_type=dict):
            raise ExtractorError('Model is in private show', expected=True)
        elif not traverse_obj(data, ('viewCam', 'model', 'isLive'), expected_type=bool):
            raise ExtractorError('Model is offline', expected=True)

        server = traverse_obj(data, ('viewCam', 'viewServers', 'flashphoner-hls'), expected_type=compat_str)
        host = traverse_obj(data, ('config', 'data', 'featuresV2', 'hlsFallback', 'fallbackDomains', 0), expected_type=compat_str)
        model_id = traverse_obj(data, ('viewCam', 'model', 'id'), expected_type=int)

        formats = self._extract_m3u8_formats(
            'https://b-%s.%s/hls/%d/%d.m3u8' % (server, host, model_id, model_id),
            video_id, ext='mp4', m3u8_id='hls', fatal=False, live=True)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'description': self._og_search_description(webpage),
            'is_live': True,
            'formats': formats,
            # Stripchat declares the RTA meta-tag, but in an non-standard format so _rta_search() can't be used
            'age_limit': 18,
        }
