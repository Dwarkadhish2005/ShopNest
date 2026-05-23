
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from src.config import MULTI_QUERY_VARIATIONS

logger = logging.getLogger(__name__)



_MULTI_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at generating alternative phrasings of customer support questions
for a ShopNest e-commerce platform.

Generate exactly {n} alternative versions of the given question.
Each version should:
- Capture the same intent but use different wording
- Use terminology a policy document or FAQ might use
- Be concise (under 20 words each)

Output ONLY the {n} variations, one per line. No numbering, no explanation, no blank lines."""),
    ("human", "Original question: {question}"),
])


class MultiQueryRetriever:

    def __init__(
        self,
        retriever,
        llm: BaseLanguageModel,
        n_variations: int = MULTI_QUERY_VARIATIONS,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self.n_variations = n_variations
        self._chain = _MULTI_QUERY_PROMPT | llm
        

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        variations = self._generate_variations(query)
        all_queries = [query] + variations

        logger.debug(
            f"[MultiQuery] Generated {len(variations)} variations for: '{query[:60]}'"
        )
        for i, v in enumerate(variations, 1):
            logger.debug(f"[MultiQuery]   Variation {i}: '{v}'")

        
        seen_content: set = set()
        all_docs: List[Document] = []

        for q in all_queries:
            try:
                docs = self._retriever.retrieve(q, k=k)
                for doc in docs:
                    content_key = doc.page_content[:200]
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        all_docs.append(doc)
            except Exception as e:
                logger.warning(f"[MultiQuery] Retrieval failed for variation '{q[:40]}': {e}")

        logger.debug(
            f"[MultiQuery] Unique docs after union: {len(all_docs)} "
            f"(from {len(all_queries)} queries)"
        )
        return all_docs

    def _generate_variations(self, query: str) -> List[str]:
        try:
            response = self._chain.invoke({
                "question": query,
                "n": self.n_variations,
            })
            raw = response.content.strip()
            variations = [line.strip() for line in raw.split("\n") if line.strip()]
            
            valid = [v for v in variations if 5 < len(v) < 200]
            return valid[:self.n_variations]
        except Exception as e:
            logger.warning(f"[MultiQuery] Variation generation failed: {e} — using single query")
            return []
