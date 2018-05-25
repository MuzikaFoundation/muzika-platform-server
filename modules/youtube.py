
import urllib.parse as urlparse


def parse_youtube_id(url):
    """
    Parsing youtube video id from youtube URL
    """
    parsed = urlparse.urlparse(url)

    netloc = parsed.netloc

    if netloc in ['www.youtube.com', 'youtube.com']:
        # parse v arguments in url
        try:
            video_id = urlparse.parse_qs(parsed.query)['v'][0]
        except KeyError:
            return None
    elif netloc == 'youtu.be':
        video_id = parsed.path[1:]
    else:
        return None

    video_id = video_id.strip()

    if video_id:
        return video_id
    else:
        return None

