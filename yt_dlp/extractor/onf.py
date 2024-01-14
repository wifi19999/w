from .common import InfoExtractor
from ..utils import int_or_none


class ONFIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?onf\.ca/film/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.onf.ca/film/mal-du-siecle/',
        'info_dict': {
            'id': 'mal-du-siecle',
            'ext': 'mp4',
            'title': 'Le mal du siècle',
            'description': 'md5:1abf774d77569ebe603419f2d344102b',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Catherine Lepage',
            'release_year': 2019
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage('https://www.onf.ca/film/%s/' % video_id, video_id)

        iframe = self._html_search_regex(
            r'<[^>]+\bid=["\']player-iframe["\'][^>]*src=["\']([^"\']+)',
            webpage, 'iframe', default=None, fatal=True)
        if iframe.startswith('/'):
            iframe = f'https://www.onf.ca{iframe}'

        player = self._download_webpage(iframe, video_id)

        source = self._html_search_regex(
            r'source:\s*\'([^\']+)',
            player, 'source', default=None, fatal=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(source, video_id, ext='mp4')

        return {
            'id': video_id,
            'title': self._html_search_regex(
                r'<[^>]+\bid=["\']titleHeader["\'][^>]*>\s*<h1[^>]*>\s*([^<]+?)\s*</h1>',
                webpage, 'title', default=None),
            'description': self._html_search_regex(
                r'<[^>]+\bid=["\']tabSynopsis["\'][^>]*>\s*<p[^>]*>\s*([^<]+)',
                webpage, 'description', default=None),
            'thumbnail': self._html_search_regex(
                r'poster:\s*\'([^\']+)',
                player, 'thumbnail', default=None),
            'uploader': self._html_search_regex(
                r'<[^>]+\bitemprop=["\']name["\'][^>]*>([^<]+)',
                webpage, 'uploader', default=None),
            'release_year': int_or_none(self._html_search_regex(
                r'<[^>]+\bitemprop=["\']datePublished["\'][^>]*>([^<]+)',
                webpage, 'release_year', default=None)),
            'formats': formats,
            'subtitles': subtitles,
        }