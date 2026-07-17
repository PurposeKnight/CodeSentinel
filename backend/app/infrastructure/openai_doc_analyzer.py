import json
import os
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.ports import DocAnalyzer

logger = get_logger(__name__)


class OpenAIDocAnalyzer(DocAnalyzer):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        api_key = settings.openai_api_key.get_secret_value()
        self._is_mock = api_key == "mock-key"
        if not self._is_mock:
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.openai_api_base,
            )
        else:
            self._client = None

    async def analyze_documentation(self, target_dir: str) -> dict[str, Any]:
        all_files = []
        for root, _, files in os.walk(target_dir):
            if any(p in root for p in (".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache")):
                continue
            for file in files:
                if file.endswith((".py", ".md", ".json", ".yaml", ".yml")):
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    rel_path = rel_path.replace("\\", "/")
                    all_files.append(rel_path)

        if self._is_mock:
            logger.info("openai_doc_analyzer_mock_mode")
            return {
                "documentation_score": 95,
                "findings": [
                    {
                        "file": "README.md",
                        "explanation": "Mock doc assessment: The README is well structured but could include a developer guide.",
                        "recommendation": "Mock recommendation: Add a section on how to run tests locally.",
                    }
                ],
            }

        logger.info("openai_doc_analyzer_calling")
        prompt = f"""
You are a Technical Writer and Software Architect.
Analyze the files in the project to assess documentation, docstrings, and API documentation:
Files list: {json.dumps(all_files)}

Provide your response in JSON format containing:
1. "documentation_score": An integer from 0 to 100 representing documentation quality score.
2. "findings": A list of findings, where each finding is a JSON object with:
   - "file": The file path.
   - "explanation": Concise explanation of documentation gaps or docstring quality issues.
   - "recommendation": Concrete recommendation to improve docs.
"""
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a documentation quality analyzer. Always output valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI returned an empty response content.")
            return json.loads(content)
        except Exception as exc:
            logger.error("openai_doc_analyzer_failed", error=str(exc))
            return {
                "documentation_score": 100,
                "findings": [
                    {
                        "file": "unknown",
                        "explanation": f"Failed to get documentation review from LLM: {str(exc)}",
                        "recommendation": "Review docstrings and markdown files directly.",
                    }
                ],
            }
