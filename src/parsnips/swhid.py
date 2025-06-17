import hashlib


class Swhid:

    @staticmethod
    def compute_content_swhid(content_string):
        content_bytes = content_string.encode("utf-8")
        digest = hashlib.blake2s(content_bytes, digest_size=32).hexdigest()
        swhid = f"swh:1:cnt:{digest}"
        return swhid