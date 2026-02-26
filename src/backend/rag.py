"""
rag.py – Vertex AI Search retrieval for RAG.
Uses v1beta REST API with correct global location and response parsing.
"""

import logging
import asyncio
import json
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

log = logging.getLogger("cosmos.rag")


class VertexSearchRAG:
    def __init__(self, project_id: str, location: str, data_store_id: str,
                 serving_config: Optional[str] = None):
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id

        # Always use global for Vertex AI Search
        self._search_url = (
            f"https://discoveryengine.googleapis.com/v1beta"
            f"/projects/{project_id}/locations/global"
            f"/collections/default_collection"
            f"/dataStores/{data_store_id}"
            f"/servingConfigs/default_search:search"
        )
        log.info(f"Vertex AI Search URL: {self._search_url}")

    def _get_access_token(self) -> str:
        """Get access token using google-auth."""
        try:
            import google.auth
            import google.auth.transport.requests
            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(google.auth.transport.requests.Request())
            return credentials.token
        except Exception as e:
            log.error(f"Failed to get access token: {e}")
            raise

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_retrieve, query, top_k)

    def _sync_retrieve(self, query: str, top_k: int) -> list[dict]:
        try:
            token = self._get_access_token()

            payload = json.dumps({
                "query": query,
                "pageSize": top_k,
                "contentSearchSpec": {
                    "extractiveContentSpec": {
                        "maxExtractiveAnswerCount": 3,
                        "maxExtractiveSegmentCount": 3
                    },
                    "snippetSpec": {
                        "returnSnippet": True,
                        "maxSnippetCount": 3
                    }
                },
                "queryExpansionSpec": {"condition": "AUTO"},
                "spellCorrectionSpec": {"mode": "AUTO"}
            }).encode("utf-8")

            req = Request(
                self._search_url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Goog-User-Project": self.project_id,
                }
            )

            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            results = []
            for item in data.get("results", []):
                doc = item.get("document", {})
                derived = doc.get("derivedStructData", {})

                # Extract content from extractive answers
                content_parts = []
                for ans in derived.get("extractive_answers", []):
                    if isinstance(ans, dict) and "content" in ans:
                        content = ans["content"]
                        content = content.replace("<b>", "").replace("</b>", "")
                        content = content.replace("&#39;", "'").replace("&amp;", "&")
                        content_parts.append(content)

                # Fallback to snippets
                for sn in derived.get("snippets", []):
                    if isinstance(sn, dict) and "snippet" in sn:
                        content_parts.append(sn["snippet"])

                content = " ".join(content_parts).strip() or "(no content)"
                link = derived.get("link", "")
                title = derived.get("title", link.split("/")[-1] if link else "Knowledge Base")

                results.append({
                    "id": doc.get("id", ""),
                    "title": title,
                    "source": link,
                    "content": content,
                    "relevance_score": item.get("rankSignals", {}).get("semanticSimilarityScore", 0)
                })

            log.info(f"RAG retrieved {len(results)} results for: {query!r}")
            return results

        except Exception as exc:
            log.warning(f"Vertex AI Search error: {exc}")
            return []
