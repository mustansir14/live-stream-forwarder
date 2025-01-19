class BaseStreamSourceException(Exception):
    """Base exception for stream sources"""


class StreamNotFound(BaseStreamSourceException):
    """Stream not found exception"""
