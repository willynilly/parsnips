import urllib.parse

import requests


class SWHContext:
    BASE_URL = "https://archive.softwareheritage.org/api/1"

    def __init__(self, repo_url=None, commit=None, release_name=None, ref_name=None, visit=None):
        self.repo_url = repo_url
        self.commit = commit
        self.release_name = release_name
        self.ref_name = ref_name
        self.visit = visit  # optional snapshot ID
        self.snapshot_id = None
        self.anchor_swhid = None

    def lookup_snapshot(self) -> str | None:
        if self.repo_url is None:
            return None
        origin_encoded = urllib.parse.quote(self.repo_url, safe='')
        url = f"{self.BASE_URL}/origin/{origin_encoded}/visits/"
        response = requests.get(url)
        response.raise_for_status()
        visits = response.json()['origin_visits']
        if not visits:
            raise ValueError("No visits found for origin in SWH.")
        latest_visit = visits[-1] if not self.visit else next(
            v for v in visits if v['visit'] == int(self.visit))
        self.snapshot_id = latest_visit['snapshot']
        return self.snapshot_id

    def lookup_anchor(self) -> str | None:
        """
        Resolve the appropriate SWH anchor based on user-provided inputs.

        Priority order:
        1. --commit        → revision SWHID
        2. --release-name  → release SWHID
        3. --ref-name      → branch or lightweight tag → revision SWHID

        Returns:
            str: anchor SWHID (swh:1:rev:... or swh:1:rel:...)

        Raises:
            ValueError if none of the inputs are sufficient to resolve an anchor.
        """
        if self.repo_url is None:
            raise ValueError("Repository URL is required to resolve an anchor.")

        # Always ensure snapshot context is loaded before anchor resolution
        if not self.snapshot_id:
            self.lookup_snapshot()

        # 1. Priority: resolve revision via commit
        if self.commit:
            return self.lookup_revision_from_commit()

        # 2. Next: resolve release via release name (annotated tag)
        if self.release_name:
            return self.lookup_release()

        # 3. Last: resolve revision via ref (branch name or lightweight tag)
        if self.ref_name:
            return self.lookup_ref()

        # 4. Fail if no qualifying context is provided
        raise ValueError(
            "Unable to resolve anchor: provide at least one of --commit, --release-name, or --ref-name."
        )

    
    def lookup_revision_from_commit(self) -> str | None:
        if self.repo_url is None:
            return None
        
        origin_encoded = urllib.parse.quote(self.repo_url, safe='')
        url = f"{self.BASE_URL}/origin/{origin_encoded}/lookup/commit/{self.commit}/"
        response = requests.get(url)
        response.raise_for_status()
        revision_id = response.json()['id']
        self.anchor_swhid = revision_id
        return revision_id

    def lookup_release(self) -> str | None:
        if self.repo_url is None:
            return None
        
        snapshot: dict | None = self.get_snapshot_object()
        if snapshot is None:
            return None
        
        releases = snapshot.get('releases', {})
        if self.release_name not in releases:
            raise ValueError(f"Release {self.release_name} not found in snapshot.")
        rel_id = releases[self.release_name]['target']['id']
        self.anchor_swhid = rel_id
        return rel_id

    def lookup_ref(self) -> str | None:
        if self.repo_url is None:
            return None
        
        snapshot: dict | None = self.get_snapshot_object()
        if snapshot is None:
            return None
        
        branches = snapshot.get('branches', {})
        if self.ref_name not in branches:
            raise ValueError(f"Ref {self.ref_name} not found in snapshot.")
        rev_id = branches[self.ref_name]['target']['id']
        self.anchor_swhid = rev_id
        return rev_id

    def get_snapshot_object(self) -> dict | None:
        if self.repo_url is None:
            return None
        
        if not self.snapshot_id:
            self.lookup_snapshot()
        url = f"{self.BASE_URL}/snapshot/{self.snapshot_id}/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def get_context_qualifiers(self) -> dict | None:
        """Returns the context qualifiers as dict"""

        if self.repo_url is None:
            return None
        
        if not self.anchor_swhid:
            self.lookup_anchor()

        qualifiers = {
            "origin": self.repo_url,
            "visit": f"swh:1:snp:{self.snapshot_id}",
            "anchor": self.anchor_swhid
        }
        return qualifiers
