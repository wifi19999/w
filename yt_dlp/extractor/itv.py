# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from .brightcove import BrightcoveNewIE
from ..utils import (
    clean_html,
    determine_ext,
    extract_attributes,
    ExtractorError,
    get_element_by_class,
    JSON_LD_RE,
    merge_dicts,
    parse_duration,
    smuggle_url,
    try_get,
    url_or_none,
)


class ITVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?itv\.com/hub/[^/]+/(?P<id>[0-9a-zA-Z]+)'
    _GEO_COUNTRIES = ['GB']
    _TESTS = [{
        'url': 'https://www.itv.com/hub/plebs/2a1873a0002',
        'info_dict': {
            'id': '2a1873a0002',
            'ext': 'mp4',
            'title': 'Plebs - The Orgy',
            'description': 'md5:4d7159af53ebd5b36e8b3ec82a41fdb4',
            'series': 'Plebs',
            'season_number': 1,
            'episode_number': 1
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # unavailable via data-playlist-url
        'url': 'https://www.itv.com/hub/through-the-keyhole/2a2271a0033',
        'only_matching': True,
    }, {
        # InvalidVodcrid
        'url': 'https://www.itv.com/hub/james-martins-saturday-morning/2a5159a0034',
        'only_matching': True,
    }, {
        # ContentUnavailable
        'url': 'https://www.itv.com/hub/whos-doing-the-dishes/2a2898a0024',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        params = extract_attributes(self._search_regex(
            r'(?s)(<[^>]+id="video"[^>]*>)', webpage, 'params'))
        variants = self._parse_json(
            try_get(params, lambda x: x['data-video-variants'], str) or '{}',
            video_id, fatal=False)
        platform_tag_video = None
        featureset_video = None
        for platform_tag, featuresets in variants.items():
            for featureset in featuresets:
                if (isinstance(featureset, list) and len(featureset) >= 2
                        and featureset[0] == 'hls' and featureset[1] == 'aes'):
                    platform_tag_video = platform_tag
                    featureset_video = featureset
                    break
        if not platform_tag_video or not featureset_video:
            raise ExtractorError('No downloads available', expected=True, video_id=video_id)

        ios_playlist_url = params.get('data-video-playlist') or params['data-video-id']
        hmac = params['data-video-hmac']
        headers = self.geo_verification_headers()
        headers.update({
            'Accept': 'application/vnd.itv.vod.playlist.v2+json',
            'Content-Type': 'application/json',
            'hmac': hmac.upper(),
        })
        ios_playlist = self._download_json(
            ios_playlist_url, video_id, data=json.dumps({
                'user': {
                    'itvUserId': '',
                    'entitlements': [],
                    'token': ''
                },
                'device': {
                    'manufacturer': 'Safari',
                    'model': '5',
                    'os': {
                        'name': 'Windows NT',
                        'version': '6.1',
                        'type': 'desktop'
                    }
                },
                'client': {
                    'version': '4.1',
                    'id': 'browser'
                },
                'variantAvailability': {
                    'featureset': {
                        'min': featureset_video,
                        'max': featureset_video
                    },
                    'platformTag': platform_tag_video
                }
            }).encode(), headers=headers)
        video_data = try_get(ios_playlist, lambda x: x['Playlist']['Video'], dict) or {}
        ios_base_url = video_data.get('Base')
        hls_subs = {}
        formats = []
        for media_file in (video_data.get('MediaFiles') or []):
            href = media_file.get('Href')
            if not href:
                continue
            if ios_base_url:
                href = ios_base_url + href
            ext = determine_ext(href)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    href, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': href,
                })
        self._sort_formats(formats)

        subtitles = {}
        platform_tag_subs = None
        featureset_subs = None
        for platform_tag, featuresets in variants.items():
            for featureset in featuresets:
                if (isinstance(featureset, list) and len(featureset) >= 3
                        and featureset[2] == 'outband-webvtt'):
                    platform_tag_subs = platform_tag
                    featureset_subs = featureset
                    break
        if not platform_tag_subs or not featureset_subs:
            self.report_warning('No subtitles available', video_id)
        else:
            subs_playlist = self._download_json(
                ios_playlist_url, video_id, data=json.dumps({
                    'user': {
                        'itvUserId': '',
                        'entitlements': [],
                        'token': ''
                    },
                    'device': {
                        'manufacturer': 'Safari',
                        'model': '5',
                        'os': {
                            'name': 'Windows NT',
                            'version': '6.1',
                            'type': 'desktop'
                        }
                    },
                    'client': {
                        'version': '4.1',
                        'id': 'browser'
                    },
                    'variantAvailability': {
                        'featureset': {
                            'min': featureset_subs,
                            'max': featureset_subs
                        },
                        'platformTag': platform_tag_subs
                    }
                }).encode(), headers=headers)
            subs = try_get(subs_playlist, lambda x: x['Playlist']['Video']['Subtitles'], list) or []
            for sub in subs:
                if not isinstance(sub, dict):
                    continue
                href = url_or_none(sub.get('Href'))
                if not href:
                    continue
                subtitles.setdefault('en', []).append({'url': href})
        subtitles = self._merge_subtitles(subtitles, hls_subs)
        info = self._search_json_ld(webpage, video_id, default={})
        if not info:
            json_ld = self._parse_json(self._search_regex(
                JSON_LD_RE, webpage, 'JSON-LD', '{}',
                group='json_ld'), video_id, fatal=False)
            if json_ld and json_ld.get('@type') == 'BreadcrumbList':
                for ile in (json_ld.get('itemListElement:') or []):
                    item = ile.get('item:') or {}
                    if item.get('@type') == 'TVEpisode':
                        item['@context'] = 'http://schema.org'
                        info = self._json_ld(item, video_id, fatal=False) or {}
                        break

        return merge_dicts({
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'formats': formats,
            'subtitles': subtitles,
            'duration': parse_duration(video_data.get('Duration')),
            'description': clean_html(get_element_by_class('episode-info__synopsis', webpage)),
        }, info)


class ITVBTCCIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?itv\.com/btcc/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.itv.com/btcc/articles/btcc-2019-brands-hatch-gp-race-action',
        'info_dict': {
            'id': 'btcc-2019-brands-hatch-gp-race-action',
            'title': 'BTCC 2019: Brands Hatch GP race action',
        },
        'playlist_count': 12,
    }
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1582188683001/HkiHLnNRx_default/index.html?videoId=%s'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        json_map = try_get(self._parse_json(self._html_search_regex(
            '(?s)<script[^>]+id=[\'"]__NEXT_DATA__[^>]*>([^<]+)</script>', webpage, 'json_map'), playlist_id),
            lambda x: x['props']['pageProps']['article']['body']['content']) or []

        # Discard empty objects
        video_ids = []
        for video in json_map:
            if video['data'].get('id'):
                video_ids.append(video['data']['id'])

        entries = [
            self.url_result(
                smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % video_id, {
                    # ITV does not like some GB IP ranges, so here are some
                    # IP blocks it accepts
                    'geo_ip_blocks': [
                        '193.113.0.0/16', '54.36.162.0/23', '159.65.16.0/21'
                    ],
                    'referrer': url,
                }),
                ie=BrightcoveNewIE.ie_key(), video_id=video_id)
            for video_id in video_ids]

        title = self._og_search_title(webpage, fatal=False)

        return self.playlist_result(entries, playlist_id, title)
