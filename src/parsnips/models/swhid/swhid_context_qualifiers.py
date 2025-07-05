import urllib.parse

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class SwhidContextQualifiers(ParsnipsBaseModel):
    """
    Represents contextual metadata used to fully qualify a SWHID.
    These qualifiers help trace the origin and snapshot of a specific object.
    """
    origin: str   # The original repo URL (origin)
    visit: str    # The snapshot SWHID, e.g., swh:1:snp:...
    anchor: str   # The specific commit, release, or ref SWHID

    def qualify(self, base_swhid: str) -> str:
        """
        Attaches the contextual qualifiers to a base SWHID.

        Args:
            base_swhid (str): A base SWHID such as a content or revision ID.

        Returns:
            str: A qualified SWHID string like:
                 swh:1:rev:abcd1234;origin=https%3A...;visit=swh%3A1%3Asnp%3A...;anchor=swh%3A1%3Arev%3A...
        """
        suffix = ";".join(
            f"{k}={urllib.parse.quote(v, safe='')}"
            for k, v in self.model_dump(mode="json")
        )
        return f"{base_swhid};{suffix}"
