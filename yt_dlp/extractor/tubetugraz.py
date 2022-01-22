# coding: utf-8
from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata, try_get, traverse_obj
from collections import defaultdict
import re


class TubeTuGrazIE(InfoExtractor):
    IE_DESC = 'tube.tugraz.at'
    IE_NAME = 'TubeTuGraz'

    _VALID_URL = r'''(?x)
        https?://tube\.tugraz\.at/paella/ui/(?:
            (?P<series>browse\.html\?series=)|
            (?P<episode>watch.html\?id=)
        )(?P<id>[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})
    '''
    _TESTS = [{
        'url': 'https://tube.tugraz.at/paella/ui/watch.html?id=f2634392-e40e-4ac7-9ddc-47764aa23d40',
        'md5': 'a23a3d5c9aaca2b84932fdba66e17145',
        'info_dict': {
            'id': 'f2634392-e40e-4ac7-9ddc-47764aa23d40',
            'ext': 'mp4',
            'title': '#6 (23.11.2017)',
            'episode': '#6 (23.11.2017)',
            'series': '[INB03001UF] Einführung in die strukturierte Programmierung',
            'creator': 'Safran C',
            'duration': 3295818,
        }
    }]

    _NETRC_MACHINE = "tubetugraz"

    _API_EPISODE = 'https://tube.tugraz.at/search/episode.json'

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        result = self._download_webpage_handle(
            'https://tube.tugraz.at/Shibboleth.sso/Login?target=/paella/ui/index.html',
            None,
            note='downloading login page',
            errnote='unable to fetch login page',
            fatal=False)
        if result is False:
            return
        else:
            _, login_page_handle = result

        result = self._download_webpage_handle(
            login_page_handle.url, None,
            note='logging in',
            errnote='unable to log in',
            fatal=False,
            data=urlencode_postdata({
                b'lang': 'de',
                b'_eventId_proceed': '',
                b'j_username': username,
                b'j_password': password
            }),
            headers={
                'referer': login_page_handle.url
            })
        if result is False:
            return
        else:
            _, result_page_handle = result

        if result_page_handle.url != 'https://tube.tugraz.at/paella/ui/index.html':
            self.report_warning('unable to login: incorrect password')
            return

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        match = re.match(self._VALID_URL, url)

        id = match.group('id')
        if match.group('series') is not None:
            return self._extract_series(id)
        elif match.group('episode') is not None:
            return self._extract_episode(id)
        else:
            raise ExtractorError('no video found on page')

    def _extract_series(self, id):
        series_data = self._download_json(
            'https://tube.tugraz.at/series/series.json',
            None,
            note='downloading series metadata',
            errnote='failed to download series metadata',
            fatal=False,
            query={
                'seriesId': id,
                'count': 1,
                'sort': 'TITLE'
            })
        series_info = traverse_obj(series_data,
            ('catalogs', 0, 'http://purl.org/dc/terms/')) or {}

        if len(series_info) == 0:
            self.report_warning(
                'failed to download series metadata: '
                + 'authentication required or series does not exist', id)

        title = traverse_obj(series_info, ('title', 0, 'value'))

        episodes_data = self._download_json(
            self._API_EPISODE, None,
            note='downloading episode list',
            errnote='failed to download episode list',
            fatal=False,
            query={
                'sid': id
            })
        episodes_info = traverse_obj(episodes_data,
            ('search-results', 'result')) or []

        return {
            '_type': 'playlist',
            'id': id,
            'title': title,
            'entries': [self._extract_episode_from_info(episode_info)
                        for episode_info in episodes_info]
        }

    def _extract_episode(self, id):
        episode_data = self._download_json(
            self._API_EPISODE, None,
            note='downloading episode metadata',
            errnote='failed to download episode metadata',
            fatal=False,
            query={
                'id': id,
                'limit': 1
            })
        episode_info = traverse_obj(episode_data,
            ('search-results', 'result')) or {}

        if len(episode_info) == 0:
            self.report_warning(
                'failed to download series metadata: '
                + 'authentication required or video does not exist', id)

        return self._extract_episode_inner(id, episode_info)

    def _extract_episode_from_info(self, episode_info):
        id = try_get(episode_info, 'id')
        return self._extract_episode_inner(id, episode_info)

    def _extract_episode_inner(self, id, episode_info):
        title = traverse_obj(episode_info,
            ('mediapackage', 'title'), 'dcTitle') or id

        creator = traverse_obj(episode_info,
            ('mediapackage', 'creators', 'creator'), 'dcCreator')
        if isinstance(creator, list):
            creator = ', '.join(creator)

        duration = traverse_obj(episode_info,
            ('mediapackage', 'duration'), 'dcExtent')

        series_id = traverse_obj(episode_info,
            ('mediapackage', 'series'), 'dcIsPartOf')

        series_title = traverse_obj(episode_info,
            ('mediapackage', 'seriestitle')) or series_id

        episode_title = title if series_title is not None else None

        format_infos = traverse_obj(episode_info,
            ('mediapackage', 'media', 'track')) or []

        formats = []
        format_types = defaultdict(lambda: defaultdict(int))
        for format_info in format_infos:
            formats.extend(self._extract_formats(format_info, format_types))

        self._guess_formats(formats, format_types, id)
        self._sort_formats(formats)

        return {
            '_type': 'video',
            'id': id,
            'title': title,
            'creator': creator,
            'duration': duration,
            'series': series_title,
            'episode': episode_title,
            'formats': formats
        }

    def _extract_formats(self, format_info, format_types):
        PREFERRED_TYPE = 'presentation'

        url = traverse_obj(format_info, ('tags', 'url'), 'url')
        type = try_get(format_info, 'type') or 'unknown'
        transport = try_get(format_info, 'transport') or 'https'
        audio_bitrate = traverse_obj(format_info, ('audio', 'bitrate'))
        video_bitrate = traverse_obj(format_info, ('video', 'bitrate'))
        framerate = traverse_obj(format_info, ('video', 'framerate'))
        resolution = traverse_obj(format_info, ('video', 'resolution'))

        type = type.replace('/delivery', '')
        transport = transport.lower()

        if isinstance(audio_bitrate, int):
            audio_bitrate = audio_bitrate / 1000
        if isinstance(video_bitrate, int):
            video_bitrate = video_bitrate / 1000
        if isinstance(audio_bitrate, int) and isinstance(video_bitrate, int):
            bitrate = audio_bitrate + video_bitrate
        else:
            bitrate = None

        if type == PREFERRED_TYPE:
            preference = -1
        else:
            preference = -2

        if url is None:
            formats = []
        elif transport == 'https':
            formats = [{
                'url': url,
                'tbr': bitrate,
                'abr': audio_bitrate,
                'vbr': video_bitrate,
                'framerate': framerate,
                'resolution': resolution,
            }]
        elif transport == 'hls':
            formats = self._extract_m3u8_formats(
                url, None,
                note='downloading %s HLS manifest' % type,
                fatal=False,
                ext='mp4')
        elif transport == 'dash':
            formats = self._extract_mpd_formats(
                url, None,
                note='downloading %s DASH manifest' % type,
                fatal=False)
        else:
            # RTMP, HDS, SMOOTH, and unknown formats
            # - RTMP url fails on every tested entry until now
            # - HDS url 404's on every tested entry until now
            # - SMOOTH url 404's on every tested entry until now
            formats = []

        for format in formats:
            format['preference'] = preference
            self._gen_format_id(format, type, transport, format_types)

        return formats

    def _guess_formats(self, formats, format_types, id):
        PREFERRED_TYPE = 'presentation'

        for type in ('presentation', 'presenter'):
            m3u8_url = 'https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_%s_%s.smil/playlist.m3u8' % (id, type)
            mpd_url = 'https://wowza.tugraz.at/matterhorn_engage/smil:engage-player_%s_%s.smil/manifest_mpm4sav_mvlist.mpd' % (id, type)

            if type == PREFERRED_TYPE:
                preference = -1
            else:
                preference = -2

            if 'hls' not in format_types[type]:
                # guessing location of HLS manifest
                hls_formats = self._extract_m3u8_formats(
                    m3u8_url, None,
                    note='downloading %s HLS manifest' % type,
                    fatal=False,
                    errnote=False,
                    ext='mp4')

                for format in hls_formats:
                    format['preference'] = preference
                    self._gen_format_id(format, type, 'hls', format_types)

                formats.extend(hls_formats)
            if 'dash' not in format_types[type]:
                # guessing location of DASH manifest
                dash_formats = self._extract_mpd_formats(
                    mpd_url, None,
                    note='downloading %s DASH manifest' % type,
                    fatal=False,
                    errnote=False)

                for format in dash_formats:
                    format['preference'] = preference
                    self._gen_format_id(format, type, 'dash', format_types)

                formats.extend(dash_formats)

    def _gen_format_id(self, format, type, transport, format_types):
        format_types[type][transport] += 1
        index = format_types[type][transport]

        vbr = format.get('vbr')
        abr = format.get('abr')
        tbr = format.get('tbr') or ((vbr or 0) + (abr or 0))
        vcodec = format.get('vcodec')
        acodec = format.get('acodec')
        if acodec == 'none' or (vbr and not abr):
            pre_index = 'vbr'
            index = int(tbr)
        elif vcodec == 'none' or (abr and not vbr):
            pre_index = 'abr'
            index = int(tbr)
        elif tbr:
            pre_index = 'br'
            index = int(tbr)
        else:
            pre_index = ''

        format_id = '%s-%s-%s%d' % (type, transport, pre_index, index)
        format['format_id'] = format_id
