import logging
import requests
from io import BytesIO
from PIL import Image
from StringIO import StringIO
from boto import s3
from boto.s3.key import Key


log = logging.getLogger(__name__)


class S3ImageResizerException(Exception):
    pass

class InvalidParameterException(S3ImageResizerException):
    pass

class CantFetchImageException(S3ImageResizerException):
    pass

class RTFMException(S3ImageResizerException):
    pass


class S3ImageResizer(object):

    def __init__(self, s3_conn):
        if not s3_conn or 'S3Connection' not in str(type(s3_conn)):
            raise InvalidParameterException("Expecting an instance of boto s3 connection")
        self.s3_conn = s3_conn
        self.image = None

    def fetch(self, url):
        """Fetch an image and keep it in memory"""
        assert url
        log.debug("Fetching image at url %s" % url)
        res = requests.get(url)
        if res.status_code != 200:
            raise CantFetchImageException("Failed to load image at url %s" % url)
        self.image = Image.open(StringIO(res.content))

    def resize(self, width=None, height=None):
        """Resize the in-memory image previously fetched, and
        return a clone of self holding the resized image"""
        if not width and not height:
            raise InvalidParameterException("One of width or height must be specified")
        if width and height:
            raise InvalidParameterException("Only one of width or height must be specified")
        if not self.image:
            raise RTFMException("No image loaded! You must call fetch() before resize()")

        # TODO: self.image = self.image.copy()
        raise Exception("Not implemented!")

    def store(self, in_bucket=None, key_name=None, metadata=None):
        """Store the loaded image into the given bucket with the given key name. Tag
        it with metadata if provided. Make the Image public and return its url"""
        if not in_bucket:
            raise InvalidParameterException("No in_bucket specified")
        if not key_name:
            raise InvalidParameterException("No key_name specified")
        if not self.image:
            raise RTFMException("No image loaded! You must call fetch() before store()")

        if metadata:
            assert type(metadata) is dict
        else:
            metadata = {}

        metadata['Content-Type'] = 'image/jpeg'

        # Export image to a string
        sio = StringIO()
        self.image.save(sio, 'JPEG')
        contents = sio.getvalue()
        sio.close()

        # Get the bucket
        bucket = self.s3_conn.get_bucket(in_bucket)

        # Create a key containing the image. Make it public
        k = Key(bucket)
        k.key = key_name
        k.set_contents_from_string(contents)
        k.set_remote_metadata(metadata, {}, True)
        k.set_acl('public-read')

        # Return the key's public url
        return k.generate_url(
            method='GET',
            expires_in=0,
            query_auth=False,
            force_http=False
        )
