"""
rag.py – Vertex AI Search retrieval for RAG.

Uses the Discovery Engine (Vertex AI Search) client library to perform
semantic search over the ingested knowledge base documents.
"""

import logging
from typing import Optional

log = logging.getLogger("cosmos.rag")


class VertexSearchRAG:
    """Thin async wrapper around the Vertex AI Search Discovery Engine."""

    def __init__(self, project_id: str, location: str, data_store_id: str,
                 serving_config: Optional[str] = None):
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id

        # Build serving config resource name
        if serving_config:
            self._serving_config = serving_config
        else:
            self._serving_config = (
                f"projects/{project_id}/locations/{location}"
                f"/collections/default_collection"
                f"/dataStores/{data_store_id}"
                f"/servingConfigs/default_serving_config"
            )

        self._client = None  # Lazy init

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import discoveryengine_v1 as discoveryengine
                self._client = discoveryengine.SearchServiceClient()
                log.info("Vertex AI Search client initialized")
            except ImportError:
                raise RuntimeError(
                    "google-cloud-discoveryengine not installed. "
                    "Run: pip install google-cloud-discoveryengine"
                )
        return self._client

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Perform a semantic search against the Vertex AI Search data store.
        Returns a list of dicts with 'content', 'title', 'source', 'score'.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_retrieve, query, top_k)

    def _sync_retrieve(self, query: str, top_k: int) -> list[dict]:
        from google.cloud import discoveryengine_v1 as discoveryengine

        client = self._get_client()

        request = discoveryengine.SearchRequest(
            serving_config=self._serving_config,
            query=query,
            page_size=top_k,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3,
                ),
                extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                    max_extractive_answer_count=3,
                    max_extractive_segment_count=3,
                ),
            ),
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO,
            ),
        )

        try:
            response = client.search(request)
            results = []
            for result in response.results:
                doc = result.document
                content_parts = []

                # Extract snippets
                if hasattr(result, "chunk") and result.chunk:
                    content_parts.append(result.chunk.content)

                # Extract from derived struct data
                struct = doc.derived_struct_data
                if struct:
                    # Extractive answers (higher quality)
                    answers = struct.get("extractive_answers", [])
                    for ans in answers:
                        if isinstance(ans, dict) and "content" in ans:
                            content_parts.append(ans["content"])

                    # Snippets fallback
                    snippets = struct.get("snippets", [])
                    for sn in snippets:
                        if isinstance(sn, dict) and "snippet" in sn:
                            content_parts.append(sn["snippet"])

                content = " ".join(content_parts).strip() or "(no content extracted)"

                title = ""
                link = ""
                if doc.struct_data:
                    title = doc.struct_data.get("title", "")
                    link = doc.struct_data.get("link", "")

                results.append({
                    "id": doc.id,
                    "title": title,
                    "source": link,
                    "content": content,
                    "relevance_score": result.model_scores.get("relevance_score", 0)
                    if hasattr(result, "model_scores") and result.model_scores else 0,
                })

            log.info(f"RAG retrieved {len(results)} results for: {query!r}")
            return results

        except Exception as exc:
            log.warning(f"Vertex AI Search error: {exc}")
            return []
