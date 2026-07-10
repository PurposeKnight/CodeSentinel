from typing import Any, Protocol


class Scanner(Protocol):
    async def scan(self, target_dir: str) -> list[dict[str, Any]]:
        """Run static analysis tool on the target directory.

        Returns a list of standardized vulnerability dictionaries.
        """
