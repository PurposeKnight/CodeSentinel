import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


class GitService:
    async def clone_and_checkout_pr(
        self,
        repository: str,
        pr_number: int,
        target_dir: str,
    ) -> None:
        clone_url = f"https://github.com/{repository}.git"
        logger.info(
            "git_clone_starting",
            repository=repository,
            pr_number=pr_number,
            target_dir=target_dir,
        )

        # 1. Clone repository
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            clone_url,
            target_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore")
            logger.error("git_clone_failed", repository=repository, error=err_msg)
            raise RuntimeError(f"Git clone failed: {err_msg}")

        # 2. Fetch pull request branch
        logger.info("git_fetch_pr_starting", pr_number=pr_number)
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            target_dir,
            "fetch",
            "origin",
            f"pull/{pr_number}/head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore")
            logger.error("git_fetch_failed", pr_number=pr_number, error=err_msg)
            raise RuntimeError(f"Git fetch PR failed: {err_msg}")

        # 3. Checkout FETCH_HEAD (the PR branch head)
        logger.info("git_checkout_pr_starting")
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            target_dir,
            "checkout",
            "FETCH_HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore")
            logger.error("git_checkout_failed", error=err_msg)
            raise RuntimeError(f"Git checkout PR failed: {err_msg}")

        logger.info("git_checkout_pr_completed", repository=repository, pr_number=pr_number)
