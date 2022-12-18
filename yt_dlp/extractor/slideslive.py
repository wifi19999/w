import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_qs,
    smuggle_url,
    traverse_obj,
    unified_timestamp,
    update_url_query,
    url_or_none,
    xpath_text,
)


class SlidesLiveIE(InfoExtractor):
    _VALID_URL = r'https?://slideslive\.com/(?:embed/(?:presentation/)?)?(?P<id>[0-9]+)'
    _TESTS = [{
        # service_name = yoda, only XML slides info
        'url': 'https://slideslive.com/38902413/gcc-ia16-backend',
        'info_dict': {
            'id': '38902413',
            'ext': 'mp4',
            'title': 'GCC IA16 backend',
            'timestamp': 1648189972,
            'upload_date': '20220325',
            'thumbnail': r're:^https?://.*\.jpg',
            'thumbnails': 'count:42',
            'chapters': 'count:41',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = yoda, /v7/ slides
        'url': 'https://slideslive.com/38935785',
        'info_dict': {
            'id': '38935785',
            'ext': 'mp4',
            'title': 'Offline Reinforcement Learning: From Algorithms to Practical Challenges',
            'upload_date': '20211115',
            'timestamp': 1636996003,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:640',
            'chapters': 'count:639',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = yoda, /v1/ slides
        'url': 'https://slideslive.com/38973182/how-should-a-machine-learning-researcher-think-about-ai-ethics',
        'info_dict': {
            'id': '38973182',
            'ext': 'mp4',
            'title': 'How Should a Machine Learning Researcher Think About AI Ethics?',
            'upload_date': '20220201',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1643728135,
            'thumbnails': 'count:3',
            'chapters': 'count:2',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = youtube, only XML slides info
        'url': 'https://slideslive.com/38897546/special-metaprednaska-petra-ludwiga-hodnoty-pro-lepsi-spolecnost',
        'md5': '8a79b5e3d700837f40bd2afca3c8fa01',
        'info_dict': {
            'id': 'jmg02wCJD5M',
            'display_id': '38897546',
            'ext': 'mp4',
            'title': 'SPECIÁL: Meta-přednáška Petra Ludwiga - Hodnoty pro lepší společnost',
            'description': 'Watch full version of this video at https://slideslive.com/38897546.',
            'channel_url': 'https://www.youtube.com/channel/UCZWdAkNYFncuX0khyvhqnxw',
            'channel': 'SlidesLive Videos - G1',
            'channel_id': 'UCZWdAkNYFncuX0khyvhqnxw',
            'uploader_id': 'UCZWdAkNYFncuX0khyvhqnxw',
            'uploader': 'SlidesLive Videos - G1',
            'uploader_url': 'http://www.youtube.com/channel/UCZWdAkNYFncuX0khyvhqnxw',
            'live_status': 'not_live',
            'upload_date': '20160710',
            'timestamp': 1618786715,
            'duration': 6827,
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'channel_follower_count': int,
            'age_limit': 0,
            'thumbnail': r're:^https?://.*\.(?:jpg|webp)',
            'thumbnails': 'count:169',
            'playable_in_embed': True,
            'availability': 'unlisted',
            'tags': [],
            'categories': ['People & Blogs'],
            'chapters': 'count:168',
        },
    }, {
        # embed-only presentation, only XML slides info
        'url': 'https://slideslive.com/embed/presentation/38925850',
        'info_dict': {
            'id': '38925850',
            'ext': 'mp4',
            'title': 'Towards a Deep Network Architecture for Structured Smoothness',
            'thumbnail': r're:^https?://.*\.jpg',
            'thumbnails': 'count:8',
            'timestamp': 1629671508,
            'upload_date': '20210822',
            'chapters': 'count:7',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # embed-only presentation, only JSON slides info, /v5/ slides (.png)
        'url': 'https://slideslive.com/38979920/',
        'info_dict': {
            'id': '38979920',
            'ext': 'mp4',
            'title': 'MoReL: Multi-omics Relational Learning',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:7',
            'timestamp': 1654714970,
            'upload_date': '20220608',
            'chapters': 'count:6',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # /v2/ slides (.jpg)
        'url': 'https://slideslive.com/38954074',
        'info_dict': {
            'id': '38954074',
            'ext': 'mp4',
            'title': 'Decentralized Attribution of Generative Models',
            'thumbnail': r're:^https?://.*\.jpg',
            'thumbnails': 'count:16',
            'timestamp': 1622806321,
            'upload_date': '20210604',
            'chapters': 'count:15',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # /v4/ slides (.png)
        'url': 'https://slideslive.com/38979570/',
        'info_dict': {
            'id': '38979570',
            'ext': 'mp4',
            'title': 'Efficient Active Search for Combinatorial Optimization Problems',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:9',
            'timestamp': 1654714896,
            'upload_date': '20220608',
            'chapters': 'count:8',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # /v10/ slides
        'url': 'https://slideslive.com/embed/presentation/38979880?embed_parent_url=https%3A%2F%2Fedit.videoken.com%2F',
        'info_dict': {
            'id': '38979880',
            'ext': 'mp4',
            'title': 'The Representation Power of Neural Networks',
            'timestamp': 1654714962,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:22',
            'upload_date': '20220608',
            'chapters': 'count:21',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # /v7/ slides, 2 non-image slides
        'url': 'https://slideslive.com/embed/presentation/38979682?embed_container_origin=https%3A%2F%2Fedit.videoken.com',
        'info_dict': {
            'id': '38979682',
            'ext': 'mp4',
            'title': 'LoRA: Low-Rank Adaptation of Large Language Models',
            'timestamp': 1654714920,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:30',
            'upload_date': '20220608',
            'chapters': 'count:31',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # /v6/ slides, 1 non-image slide, edit.videoken.com embed
        'url': 'https://slideslive.com/38979481/',
        'info_dict': {
            'id': '38979481',
            'ext': 'mp4',
            'title': 'How to Train Your MAML to Excel in Few-Shot Classification',
            'timestamp': 1654714877,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:43',
            'upload_date': '20220608',
            'chapters': 'count:43',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # service_name = yoda
        'url': 'https://slideslive.com/38903721/magic-a-scientific-resurrection-of-an-esoteric-legend',
        'only_matching': True,
    }, {
        # dead link, service_name = url
        'url': 'https://slideslive.com/38922070/learning-transferable-skills-1',
        'only_matching': True,
    }, {
        # dead link, service_name = vimeo
        'url': 'https://slideslive.com/38921896/retrospectives-a-venue-for-selfreflection-in-ml-research-3',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [{
        # only XML slides info
        'url': 'https://iclr.cc/virtual_2020/poster_Hklr204Fvr.html',
        'info_dict': {
            'id': '38925850',
            'ext': 'mp4',
            'title': 'Towards a Deep Network Architecture for Structured Smoothness',
            'thumbnail': r're:^https?://.*\.jpg',
            'thumbnails': 'count:8',
            'timestamp': 1629671508,
            'upload_date': '20210822',
            'chapters': 'count:7',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # Reference: https://slideslive.com/embed_presentation.js
        for embed_id in re.findall(r'(?s)new\s+SlidesLiveEmbed\s*\([^)]+\bpresentationId:\s*["\'](\d+)["\']', webpage):
            url_parsed = urllib.parse.urlparse(url)
            origin = f'{url_parsed.scheme}://{url_parsed.netloc}'
            yield update_url_query(
                f'https://slideslive.com/embed/presentation/{embed_id}', {
                    'embed_parent_url': url,
                    'embed_container_origin': origin,
                })

    def _download_embed_webpage_handle(self, video_id, headers):
        return self._download_webpage_handle(
            f'https://slideslive.com/embed/presentation/{video_id}', video_id,
            headers=headers, query=traverse_obj(headers, {
                'embed_parent_url': 'Referer',
                'embed_container_origin': 'Origin',
            }))

    def _get_slide_url_tmpl(self, slides_info_url):
        slides_version = int(self._search_regex(
            r'https?://slides\.slideslive\.com/\d+/v(\d+)/\w+\.(?:json|xml)',
            slides_info_url, 'slides version', default=0))
        if slides_version < 4:
            return 'https://cdn.slideslive.com/data/presentations/%s/slides/big/%s.jpg'
        else:
            return 'https://slides.slideslive.com/%s/slides/original/%s.png'

    def _extract_custom_m3u8_info(self, m3u8_data):
        m3u8_dict = {}

        lookup = {
            'PRESENTATION-TITLE': 'title',
            'PRESENTATION-UPDATED-AT': 'timestamp',
            'PRESENTATION-THUMBNAIL': 'thumbnail',
            'PLAYLIST-TYPE': 'playlist_type',
            'VOD-VIDEO-SERVICE-NAME': 'service_name',
            'VOD-VIDEO-ID': 'service_id',
            'VOD-VIDEO-SERVERS': 'video_servers',
            'VOD-SUBTITLES': 'subtitles',
            'VOD-SLIDES-JSON-URL': 'slides_json_url',
            'VOD-SLIDES-XML-URL': 'slides_xml_url',
        }

        for line in m3u8_data.splitlines():
            if not line.startswith('#EXT-SL-'):
                continue
            tag, _, value = line.partition(':')
            key = lookup.get(tag.lstrip('#EXT-SL-'))
            if not key:
                continue
            m3u8_dict[key] = value

        # Some values are stringified JSON arrays
        for key in ('video_servers', 'subtitles'):
            if key in m3u8_dict:
                m3u8_dict[key] = self._parse_json(m3u8_dict[key], None, fatal=False) or []

        return m3u8_dict

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, urlh = self._download_embed_webpage_handle(
            video_id, headers=traverse_obj(parse_qs(url), {
                'Referer': ('embed_parent_url', ...),
                'Origin': ('embed_container_origin', ...),
            }, get_all=False))
        redirect_url = urlh.geturl()
        if 'domain_not_allowed' in redirect_url:
            domain = traverse_obj(parse_qs(redirect_url), ('allowed_domains[]', ...), get_all=False)
            if not domain:
                raise ExtractorError(
                    'This is an embed-only presentation. Try passing --referer', expected=True)
            webpage, _ = self._download_embed_webpage_handle(video_id, headers={
                'Referer': f'https://{domain}/',
                'Origin': f'https://{domain}',
            })

        player_token = self._search_regex(r'data-player-token="([^"]+)"', webpage, 'player token')
        player_data = self._download_webpage(
            f'https://ben.slideslive.com/player/{video_id}', video_id,
            note='Downloading player info', query={'player_token': player_token})
        player_info = self._extract_custom_m3u8_info(player_data)

        service_name = player_info['service_name'].lower()
        assert service_name in ('url', 'yoda', 'vimeo', 'youtube')
        service_id = player_info['service_id']

        slides, slides_xml = None, None
        chapters, thumbnails = [], []
        if url_or_none(player_info.get('thumbnail')):
            thumbnails.append({'url': player_info['thumbnail']})

        if player_info.get('slides_json_url'):
            slides = traverse_obj(self._download_json(
                player_info['slides_json_url'], video_id, fatal=False,
                note='Downloading slides JSON', errnote=False), 'slides', expected_type=list)
        if slides:
            slide_url_template = self._get_slide_url_tmpl(player_info['slides_json_url'])
            for slide_id, slide in enumerate(slides, start=1):
                slide_path = traverse_obj(slide, ('image', 'name'))
                if slide_path:
                    thumbnails.append({
                        'id': f'{slide_id:03d}',
                        'url': slide_url_template % (video_id, slide_path),
                    })
                chapters.append({
                    'title': f'Slide {slide_id:03d}',
                    'start_time': int_or_none(slide.get('time'), scale=1000)
                })

        elif player_info.get('slides_xml_url'):
            slides_xml = self._download_xml(
                player_info['slides_xml_url'], video_id, fatal=False,
                note='Downloading slides XML', errnote='Failed to download slides info')
            slide_url_template = self._get_slide_url_tmpl(player_info['slides_xml_url'])
            for slide_id, slide in enumerate(slides_xml.findall('./slide') if slides_xml else [], start=1):
                slide_path = xpath_text(slide, './slideName', 'name')
                if slide_path:
                    thumbnails.append({
                        'id': f'{slide_id:03d}',
                        'url': slide_url_template % (video_id, slide_path),
                    })
                chapters.append({
                    'title': f'Slide {slide_id:03d}',
                    'start_time': int_or_none(xpath_text(slide, './timeSec', 'time')),
                })

        subtitles = {}
        for sub in traverse_obj(player_info, ('subtitles', ...), expected_type=dict):
            webvtt_url = url_or_none(sub.get('webvtt_url'))
            if not webvtt_url:
                continue
            subtitles.setdefault(sub.get('language') or 'en', []).append({
                'url': webvtt_url,
                'ext': 'vtt',
            })

        info = {
            'id': video_id,
            'title': player_info.get('title') or self._html_search_meta('title', webpage, default=''),
            'timestamp': unified_timestamp(player_info.get('timestamp')),
            'is_live': player_info.get('playlist_type') != 'vod',
            'thumbnails': thumbnails,
            'chapters': chapters,
            'subtitles': subtitles,
        }

        if service_name in ('url', 'yoda'):
            if service_name == 'url':
                info['url'] = service_id
            else:
                cdn_hostname = player_info['video_servers'][0]
                formats = []
                formats.extend(self._extract_m3u8_formats(
                    f'https://{cdn_hostname}/{service_id}/master.m3u8',
                    video_id, 'mp4', m3u8_id='hls', fatal=False, live=True))
                formats.extend(self._extract_mpd_formats(
                    f'https://{cdn_hostname}/{service_id}/master.mpd',
                    video_id, mpd_id='dash', fatal=False))
                info.update({
                    'formats': formats,
                })
        else:
            info.update({
                '_type': 'url_transparent',
                'url': service_id,
                'ie_key': service_name.capitalize(),
                'display_id': video_id,
            })
            if service_name == 'vimeo':
                info['url'] = smuggle_url(
                    f'https://player.vimeo.com/video/{service_id}',
                    {'http_headers': {'Referer': url}})

        return info
