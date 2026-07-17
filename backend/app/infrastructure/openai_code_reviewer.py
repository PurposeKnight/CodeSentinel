import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.ports import CodeReviewer

logger = get_logger(__name__)


class OpenAICodeReviewer(CodeReviewer):
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

    async def review_code(self, diff: str) -> dict[str, Any]:
        if self._is_mock:
            logger.info("openai_code_reviewer_mock_mode")
            return {
                "architecture_score": 90,
                "performance_score": 85,
                "findings": [
                    {
                        "file": "main.py",
                        "line": 10,
                        "explanation": "Mock explanation: This is a placeholder finding for architecture/performance.",
                        "recommendation": "Mock recommendation: Refactor complex code blocks and optimize imports.",
                    }
                ],
            }

        logger.info("openai_code_reviewer_calling")
        prompt = f"""
You are a Staff Software Engineer.
Review the following pull request code diff and provide a detailed analysis:
{diff}

Provide your response in JSON format containing:
1. "architecture_score": An integer from 0 to 100 representing architectural clean code score.
2. "performance_score": An integer from 0 to 100 representing performance/complexity score.
3. "findings": A list of findings, where each finding is a JSON object with:
   - "file": The file path.
   - "line": The line number (as an integer), or null if not specific.
   - "explanation": Concise explanation of the code quality or design issue.
   - "recommendation": Concrete recommendation to improve the code.
"""
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code reviewer. Always output valid JSON.",
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
            logger.error("openai_code_reviewer_failed", error=str(exc))
            return {
                "architecture_score": 100,
                "performance_score": 100,
                "findings": [
                    {
                        "file": "unknown",
                        "line": None,
                        "explanation": f"Failed to get code review from LLM: {str(exc)}",
                        "recommendation": "Review the code changes directly.",
                    }
                ],
            }
