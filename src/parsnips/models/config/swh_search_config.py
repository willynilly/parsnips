from __future__ import annotations

import urllib.parse
from typing import ClassVar

import requests
from pydantic import Field

from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.swhid.swhid_context_qualifiers import SwhidContextQualifiers


class SwhSearchConfig(ParsnipsBaseModel):
    # Base URL for interacting with the Software Heritage API
    SWH_API_BASE_URL: ClassVar[str] = "https://archive.softwareheritage.org/api/1"

    # User-provided inputs used to identify a snapshot or object
    repo_url: str | None = None         # Required for any lookup (origin)
    commit: str | None = None           # Optional: commit hash (priority 1)
    release_name: str | None = None     # Optional: annotated tag name (priority 2)
    ref_name: str | None = None         # Optional: branch or lightweight tag (priority 3)
    visit: str | None = None            # Optional: snapshot visit ID to disambiguate visits

    # Internally resolved fields
    snapshot_id: str | None = Field(default=None, exclude=True)
    anchor_swhid: str | None = Field(default=None, exclude=True)

    # def lookup_snapshot(self) -> str:
    #     """
    #     Resolves the snapshot ID associated with the given origin.
    #     Returns the most recent visit unless a specific visit ID is provided.
    #     Raises if repo_url is not set, no visits exist, or snapshot cannot be determined.
    #     """
    #     if self.repo_url is None:
    #         raise ValueError("repo_url is required to lookup snapshot")

    #     origin_encoded = urllib.parse.quote(self.repo_url, safe='')
    #     url = f"{self.SWH_API_BASE_URL}/origin/{origin_encoded}/visits/"
    #     response = requests.get(url)
    #     response.raise_for_status()
    #     visits = response.json()['origin_visits']
    #     if not visits:
    #         raise ValueError("No visits found for origin in SWH.")

    #     if not self.visit:
    #         latest_visit = visits[-1]
    #     else:
    #         try:
    #             latest_visit = next(v for v in visits if v['visit'] == int(self.visit))
    #         except StopIteration:
    #             raise ValueError(f"Visit ID {self.visit} not found in origin visits.")

    #     self.snapshot_id = latest_visit['snapshot']
    #     if self.snapshot_id is None:
    #         raise ValueError("Failed to resolve snapshot_id from SWH API.")

    #     return self.snapshot_id

    def lookup_snapshot(self) -> str:
        """
        Resolves the snapshot ID associated with the given origin.
        Returns the most recent visit unless a specific visit ID is provided.
        Raises if repo_url is not set, no visits exist, or snapshot cannot be determined.
        """
        if self.repo_url is None:
            raise ValueError("repo_url is required to lookup snapshot")

        origin_encoded = urllib.parse.quote(self.repo_url, safe="")
        url = f"{self.SWH_API_BASE_URL}/origin/{origin_encoded}/visits/"
        response = requests.get(url)

        if response.status_code == 404:
            raise ValueError(
                f"Software Heritage has not archived the repository:\n  {self.repo_url}\n\n"
                "You can request ingestion at:\n"
                "   https://save.softwareheritage.org/\n\n"
                "Once the repo is ingested, re-run this command."
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(
                f"Failed to query SWH API for origin visits.\n"
                f"URL: {url}\n"
                f"HTTP Status: {response.status_code}\n"
                f"Response: {response.text}"
            ) from e

        data = response.json()
        visits = data.get("origin_visits")
        if not visits:
            raise ValueError(
                f"No visits found for origin in Software Heritage for:\n  {self.repo_url}"
            )

        if not self.visit:
            latest_visit = visits[-1]
        else:
            try:
                latest_visit = next(v for v in visits if v["visit"] == int(self.visit))
            except (StopIteration, ValueError):
                raise ValueError(
                    f"Visit ID {self.visit} not found in origin visits for:\n  {self.repo_url}"
                )

        self.snapshot_id = latest_visit.get("snapshot")
        if self.snapshot_id is None:
            raise ValueError(
                f"Snapshot ID could not be resolved for origin:\n  {self.repo_url}"
            )

        return self.snapshot_id


    def get_snapshot_object(self) -> dict:
        """
        Fetches the full snapshot metadata object.
        Will trigger snapshot lookup if not already done.
        """
        if self.repo_url is None:
            raise ValueError("repo_url is required")
        if not self.snapshot_id:
            self.lookup_snapshot()

        url = f"{self.SWH_API_BASE_URL}/snapshot/{self.snapshot_id}/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def lookup_revision_from_commit(self) -> str:
        """
        Resolves the revision SWHID for a given commit hash.
        Must have both repo_url and commit set.
        """
        if not self.repo_url or not self.commit:
            raise ValueError("Both repo_url and commit are required")

        origin_encoded = urllib.parse.quote(self.repo_url, safe='')
        url = f"{self.SWH_API_BASE_URL}/origin/{origin_encoded}/lookup/commit/{self.commit}/"
        response = requests.get(url)
        response.raise_for_status()
        rev_id = response.json()['id']
        self.anchor_swhid = rev_id
        return rev_id

    def lookup_release(self) -> str:
        """
        Resolves the SWHID of a release (annotated tag) by name.
        Raises if not found in the snapshot metadata.
        """
        snapshot = self.get_snapshot_object()
        releases = snapshot.get('releases', {})

        if self.release_name not in releases:
            raise ValueError(f"Release {self.release_name} not found in snapshot.")
        rel_id = releases[self.release_name]['target']['id']
        self.anchor_swhid = rel_id
        return rel_id

    def lookup_ref(self) -> str:
        """
        Resolves the SWHID of a revision pointed to by a ref (branch or lightweight tag).
        """
        snapshot = self.get_snapshot_object()
        branches = snapshot.get('branches', {})

        if self.ref_name not in branches:
            raise ValueError(f"Ref {self.ref_name} not found in snapshot.")
        rev_id = branches[self.ref_name]['target']['id']
        self.anchor_swhid = rev_id
        return rev_id

    def lookup_anchor(self) -> str:
        """
        Resolves the anchor SWHID using the following priority:
        1. commit → revision
        2. release_name → release
        3. ref_name → revision (from ref)
        """
        if not self.repo_url:
            raise ValueError("repo_url is required")

        if not self.snapshot_id:
            self.lookup_snapshot()

        if self.commit:
            return self.lookup_revision_from_commit()
        if self.release_name:
            return self.lookup_release()
        if self.ref_name:
            return self.lookup_ref()

        raise ValueError(
            "Unable to resolve anchor: provide one of commit, release_name, or ref_name."
        )

    def find_swhid_context_qualifiers(self) -> SwhidContextQualifiers:
        """
        Produces a structured object of SWHID context qualifiers
        including origin, visit (snapshot), and anchor (commit/tag).
        """
        
        if not self.repo_url:
            raise ValueError("repo_url is required")
        if not self.anchor_swhid:
            self.lookup_anchor()

        if self.anchor_swhid is None:
            raise ValueError("Failed to resolve anchor qualifier from SWH API.")

        return SwhidContextQualifiers(
            origin=self.repo_url,
            visit=f"swh:1:snp:{self.snapshot_id}",
            anchor=self.anchor_swhid
        )
