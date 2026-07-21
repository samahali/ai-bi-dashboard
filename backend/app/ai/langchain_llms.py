"""
LangChain LLM wrapper for IBM Granite (Watsonx).

There is no `langchain-ibm` package pinned in this project, so Watsonx is
exposed to LangChain via a thin custom `LLM` subclass around the
`ibm-watsonx-ai` SDK's synchronous `generate_text` call — the same call the
app already made directly before this module existed. Wrapping it as a
LangChain `LLM` is what lets `agent.py` build one real
`prompt | llm | StrOutputParser()` chain regardless of provider, instead of
branching on provider at the call site.
"""
from typing import Any, Optional

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM


class WatsonxGraniteLLM(LLM):
    """Minimal LangChain LLM adapter around an ibm-watsonx-ai Model instance."""

    model: Any  # ibm_watsonx_ai.foundation_models.Model — untyped to avoid a hard import here

    @property
    def _llm_type(self) -> str:
        return "watsonx-granite"

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        response = self.model.generate_text(prompt=prompt)
        return response if isinstance(response, str) else str(response)
