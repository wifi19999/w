from .common import InfoExtractor


class MatchTVIE(InfoExtractor):
    _VALID_URL = r'https?://matchtv\.ru/on-air'
    _TESTS = [{
        'url': 'http://matchtv.ru/on-air/',
        'info_dict': {
            'id': 'matchtv-live',
            'ext': 'mp4',
            'title': r're:^Матч ТВ - Прямой эфир \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = 'matchtv-live'
        webpage_url = 'https://video.matchtv.ru/iframe/channel/106'
        webpage = self._download_webpage(webpage_url, video_id)
        video_url = self._html_search_regex(
            r'data-config="config=([^?]*)?', webpage, 'video URL').replace('feed', 'media') + '.m3u8'
        formats = self._extract_m3u8_formats(video_url, video_id, 'mp4')
        return {
            'id': video_id,
            'title': 'Матч ТВ - Прямой эфир',
            'is_live': True,
            'formats': formats,
        }
