from copy import copy

from .common import InfoExtractor
from .extractors import BrightcoveNewIE
from ..utils import try_get


class ToggoIE(InfoExtractor):
    IE_NAME = 'toggo'
    _VALID_URL = r'https?://(?:www\.)?toggo\.de/[\w-]+/folge/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.toggo.de/weihnachtsmann--co-kg/folge/ein-geschenk-fuer-zwei',
        'md5': 'TODO',
        'info_dict': {
            'id': '6133142945001',
            'ext': 'mp4',
            'title': 'Ein Geschenk für zwei',
            'language': 'de',
            'thumbnail': r're:^http://.*\.jpg',
            'description': '',
            'release_timestamp': 'TODO',
        }
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)

        data = self._download_json(
            f'https://production-n.toggo.de/api/assetstore/vod/asset/{slug}', slug)['data']

        # print(json.dumps(data, indent=2))

        video_id = next(
            x['value'] for x in data['custom_fields'] if x['key'] == 'video-cloud-id')

        brightcove_ie = BrightcoveNewIE()
        downloader = copy(self._downloader)
        # This is needed to ignore the DRM error because we're going to replace the fragment base URL later on
        downloader.params = {'allow_unplayable_formats': True}
        brightcove_ie.set_downloader(downloader)

        info = brightcove_ie._real_extract(
            f'http://players.brightcove.net/6057955896001/default_default/index.html?videoId={video_id}')

        info.update({
            'id': data.get('id'),
            'title': data.get('title'),
            'language': data.get('language'),
            'thumbnail': try_get(data, lambda x: x['images']['Thumbnail']),  # TODO: Extract all thumbnails
            'description': data.get('description'),
            'release_timestamp': data.get('earliest_start_date'),
            'series': data.get('series_title'),
            'season': data.get('season_title'),
            'season_number': data.get('season_no'),
            'season_id': data.get('season_id'),
            'episode': data.get('title'),
            'episode_number': data.get('episode_no'),
            'episode_id': data.get('id'),
        })

        for f in info['formats']:
            if '/dash/live/cenc/' in f.get('fragment_base_url', ''):
                # Get hidden non-DRM format
                f['fragment_base_url'] = f['fragment_base_url'].replace('/cenc/', '/clear/')
                f['has_drm'] = False

        return info
