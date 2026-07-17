import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.ports import VulnerabilityExplainer

logger = get_logger(__name__)


class OpenAIVulnerabilityExplainer(VulnerabilityExplainer):
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

    async def explain_vulnerability(
        self,
        scanner: str,
        vulnerability_detail: dict[str, Any],
    ) -> dict[str, Any]:
        vuln_id = vulnerability_detail.get("vulnerability_id", "unknown")
        if self._is_mock:
            logger.info("openai_explainer_mock_mode", scanner=scanner, vulnerability_id=vuln_id)
            return {
                "explanation": (
                    f"Mock explanation for {vuln_id}: This represents a potential "
                    f"security issue detected by {scanner}."
                ),
                "recommendation": (
                    f"Mock recommendation: Ensure proper parameter validation, sanitization, "
                    f"and follow secure coding best practices for {vuln_id}."
                ),
                "code_fix": (
                    f"# Mock fix for {vuln_id}\n"
                    f"# TODO: Review and secure the implementation below\n"
                    f"pass"
                ),
            }

        logger.info("openai_explainer_calling", scanner=scanner, vulnerability_id=vuln_id)
        prompt = f"""
You are a Staff Security and AI Engineer.
Explain the following vulnerability found by the scanner '{scanner}':
{json.dumps(vulnerability_detail, indent=2)}

Provide your response in JSON format containing:
1. "explanation": A concise, clear explanation of what the vulnerability is and its impact.
2. "recommendation": Concrete recommendation steps to mitigate the issue.
3. "code_fix": A code snippet with the fix, or null if not applicable.
"""
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security engineer. Always output valid JSON.",
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
            logger.error("openai_explainer_failed", error=str(exc))
            return {
                "explanation": f"Failed to get explanation from LLM: {str(exc)}",
                "recommendation": "Review the scanner findings directly.",
                "code_fix": None,
            }
