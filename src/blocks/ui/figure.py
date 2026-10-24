import base64

from ._kit import block


def figure(image, caption=None):
    """SVG text, or PNG bytes (e.g. matplotlib's savefig into a BytesIO)."""
    if isinstance(image, (bytes, bytearray)):
        return block("figure", media="image/png", data=base64.b64encode(bytes(image)).decode(), caption=caption)
    return block("figure", media="image/svg+xml", data=str(image), caption=caption)
