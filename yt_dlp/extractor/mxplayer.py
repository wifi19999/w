from .common import InfoExtractor
from ..compat import compat_str
from ..utils import try_get


class MxplayerIE(InfoExtractor):
    #_VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?P<type>movie|show/[-\w]+/[-\w]+)/(?P<display_id>[-\w]+)-(?P<id>\w+)'
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?P<type>movie|show/[-\w]+/[-\w]+)/(?P<display_id>[-\w]+)-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/movie/watch-kitne-door-kitne-paas-movie-online-a9e9c76c566205955f70d8b2cb88a6a2',
        'info_dict': {
            'id': 'a9e9c76c566205955f70d8b2cb88a6a2',
            'display_id': 'watch-kitne-door-kitne-paas-movie-online',
            'title': 'Kitne Door Kitne Paas',
            'duration': 8458,
            'ext': 'mp4',
            'description': 'Jatin and Karishma, who meet each other on a plane to India, are set to marry the partners chosen by their respective parents. However, they find themselves attracted to each other.',
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/show/watch-ek-thi-begum-hindi/season-2/game-of-power-online-5e5305c28f1409847cdc4520b6ad77cf',
        'info_dict': {
            'id': '5e5305c28f1409847cdc4520b6ad77cf',
            'display_id': 'game-of-power-online',
            'title': 'Game Of Power',
            'duration': 1845,
            'ext': 'mp4',
            'description': 'Cops arrest Ashraf assuming a prostitute. But she gets away with her new identity, Leela Paswan. Maqsood dumps Nana Mhatre and appoints Shaqeel Ansari as a new Bombay chief. For society, he is a sophisticated businessman. The rift between the new chief minister, Yashwant Patil and Shaqeel Ansari begins with a failed business deal. Ashwin Surve, a daredevil young gangster challenges established gangs of Maqsood & Bhai Chavan. He wants to enter in the drug business. But the only supplier Nari Khan supplies stuff only to Maqsood gang and no one else. ACP Qureshi arrests Bhai Chavan and turns his focus on people close to Zaheer and Ashraf. Ashraf faces a narrow escape from Qureshi and decides to take up her new identity beyond just fake documents.',
            'series': 'Ek Thi Begum (Hindi)',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Episode 2',
            'episode_number': 2,
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    },]

    def _real_extract(self, url):
        video_type, display_id, video_id = self._match_valid_url(url).groups()
        if 'show' in video_type: video_type = 'episode'
        API_URL = f'https://api.mxplay.com/v1/web/detail/video?type={video_type}&id={video_id}'
        STREAM_URL = 'https://llvod.mxplay.com/{}'
        data_json = self._download_json(API_URL, display_id)
        print(API_URL)
        formats = []
        subtitles = {}

        from pprint import pprint

        description = data_json['description']
        series, season, season_number, episode_number = None, None, None, None

        if video_type == 'episode':
            series = data_json['container']['container']['title']
            season = data_json['container']['title']
            season_number = int(season.split()[1])
            episode_number = data_json['sequence']

        for key in 'dash', 'hls':
            playlist_url = STREAM_URL.format(data_json['stream'][key]['high'])
            print(playlist_url)
            if key == 'dash':
                frmt, subs = self._extract_mpd_formats_and_subtitles(playlist_url, display_id, fatal=False)
            else:
                frmt, subs = self._extract_m3u8_formats_and_subtitles(playlist_url, display_id, fatal=False)
            formats.extend(frmt)
            subtitles = self._merge_subtitles(subtitles, subs)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': data_json['title'],
            'duration': data_json['duration'],
            'description': description,
            'formats': formats,
            'subtitles': subtitles,
            'series': series,
            'season': season,
            'season_number': season_number,
            'episode_number': episode_number,
        }
        '''
        type, display_id, video_id = self._match_valid_url(url).groups()
        type = 'movie_film' if type == 'movie' else 'tvshow_episode'
        API_URL = 'https://androidapi.mxplay.com/v1/detail/'
        headers = {
            'X-Av-Code': '23',
            'X-Country': 'IN',
            'X-Platform': 'android',
            'X-App-Version': '1370001318',
            'X-Resolution': '3840x2160',
        }
        data_json = self._download_json(f'{API_URL}{type}/{video_id}', display_id, headers=headers)['profile']

        season, series = None, None
        for dct in data_json.get('levelInfos', []):
            if dct.get('type') == 'tvshow_season':
                season = dct.get('name')
            elif dct.get('type') == 'tvshow_show':
                series = dct.get('name')
        thumbnails = []
        for thumb in data_json.get('poster', []):
            thumbnails.append({
                'url': thumb.get('url'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
            })

        formats = []
        subtitles = {}
        for dct in data_json.get('playInfo', []):
            if dct.get('extension') == 'mpd':
                frmt, subs = self._extract_mpd_formats_and_subtitles(dct.get('playUrl'), display_id, fatal=False)
                formats.extend(frmt)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif dct.get('extension') == 'm3u8':
                frmt, subs = self._extract_m3u8_formats_and_subtitles(dct.get('playUrl'), display_id, fatal=False)
                formats.extend(frmt)
                subtitles = self._merge_subtitles(subtitles, subs)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': data_json.get('name') or display_id,
            'description': data_json.get('description'),
            'season_number': data_json.get('seasonNum'),
            'episode_number': data_json.get('episodeNum'),
            'duration': data_json.get('duration'),
            'season': season,
            'series': series,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }
    '''


class MxplayerShowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/show/(?P<display_id>[-\w]+)-(?P<id>\w+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-chakravartin-ashoka-samrat-series-online-a8f44e3cc0814b5601d17772cedf5417',
        'playlist_mincount': 440,
        'info_dict': {
            'id': 'a8f44e3cc0814b5601d17772cedf5417',
            'title': 'Watch Chakravartin Ashoka Samrat Series Online',
        }
    }]

    _API_SHOW_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowseasons?type=tv_show&id={}&device-density=2&platform=com.mxplay.desktop&content-languages=hi,en"
    _API_EPISODES_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowepisodes?type=season&id={}&device-density=1&platform=com.mxplay.desktop&content-languages=hi,en&{}"

    def _entries(self, show_id):
        show_json = self._download_json(
            self._API_SHOW_URL.format(show_id),
            video_id=show_id, headers={'Referer': 'https://mxplayer.in'})
        page_num = 0
        for season in show_json.get('items') or []:
            season_id = try_get(season, lambda x: x['id'], compat_str)
            next_url = ''
            while next_url is not None:
                page_num += 1
                season_json = self._download_json(
                    self._API_EPISODES_URL.format(season_id, next_url),
                    video_id=season_id,
                    headers={'Referer': 'https://mxplayer.in'},
                    note='Downloading JSON metadata page %d' % page_num)
                for episode in season_json.get('items') or []:
                    video_url = episode['webUrl']
                    yield self.url_result(
                        'https://mxplayer.in%s' % video_url,
                        ie=MxplayerIE.ie_key(), video_id=video_url.split('-')[-1])
                next_url = season_json.get('next')

    def _real_extract(self, url):
        display_id, show_id = self._match_valid_url(url).groups()
        return self.playlist_result(
            self._entries(show_id), playlist_id=show_id,
            playlist_title=display_id.replace('-', ' ').title())
