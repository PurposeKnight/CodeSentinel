import json
import os
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.ports import TestAnalyzer

logger = get_logger(__name__)


class OpenAITestAnalyzer(TestAnalyzer):
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

    async def analyze_tests(self, target_dir: str) -> dict[str, Any]:
        source_files = []
        test_files = []
        for root, _, files in os.walk(target_dir):
            if any(p in root for p in (".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache")):
                continue
            for file in files:
                if file.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    # Convert backslashes to forward slashes for cross-platform consistency
                    rel_path = rel_path.replace("\\", "/")
                    if file.startswith("test_") or "test" in rel_path.split("/"):
                        test_files.append(rel_path)
                    else:
                        source_files.append(rel_path)

        files_summary = {"source_files": source_files, "test_files": test_files}

        if self._is_mock:
            logger.info("openai_test_analyzer_mock_mode")
            return {
                "findings": [
                    {
                        "file": "app/main.py",
                        "test_status": "partial",
                        "recommendations": [
                            "Add unit tests for application lifecycle events",
                            "Verify exception handling on startup",
                        ],
                    }
                ],
            }

        logger.info("openai_test_analyzer_calling")
        prompt = f"""
You are a Principal QA Engineer.
Analyze the following project structure:
Source Files: {json.dumps(files_summary["source_files"])}
Test Files: {json.dumps(files_summary["test_files"])}

Identify missing test coverage, recommend additional test cases, and suggest how to improve unit/integration test coverage.
Provide your response in JSON format containing:
1. "findings": A list of findings, where each finding is a JSON object with:
   - "file": The source file with missing coverage.
   - "test_status": "none", "partial", or "adequate".
   - "recommendations": A list of test case recommendations or code snippets to add.
"""
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a test quality analyzer. Always output valid JSON.",
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
            logger.error("openai_test_analyzer_failed", error=str(exc))
            return {
                "findings": [
                    {
                        "file": "unknown",
                        "test_status": "none",
                        "recommendations": [f"Failed to get test analysis from LLM: {str(exc)}"],
                    }
                ],
            }
