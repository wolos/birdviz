from typing import List, Dict, Any
import requests

class LocalAPI:
    def __init__(self, base: str):
        self.base = base.rstrip('/')

    def latest_distinct(self, limit: int) -> List[Dict[str, Any]]:
        url = f"{self.base}/api/latest_distinct"
        r = requests.get(url, params={"limit": limit}, timeout=6)
        r.raise_for_status()
        return r.json()
