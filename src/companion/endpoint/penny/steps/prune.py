import os
from dataclasses import dataclass
from dataclasses import field
from logging import getLogger
from gql import Client

from companion.connectors.github import DeleteProjectV2Item
from companion.connectors.github import ListProjectV2Items
from companion.connectors.github import ProjectItem

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

# Project filter that lists closed issues and pull requests. Draft issues have no state,
# so they are never listed.
_QUERY = "is:closed"


@dataclass(frozen=True)
class PruneResult:
    deleted: list[ProjectItem] = field(default_factory=list)
    failed: list[ProjectItem] = field(default_factory=list)
    # Items that a dry run would have deleted.
    skipped: list[ProjectItem] = field(default_factory=list)


class PruneClosedStep:
    """Deletes the project items whose linked Issue or PullRequest is closed."""

    # This Project ID can be verified by running the following GitHub CLI command:
    # gh api graphql -f query='
    #   query { node(id: "PVT_kwHOAOPA3c4BKzL3") { ... on ProjectV2 { number title } } }
    # '
    PROJECT_ID = "PVT_kwHOAOPA3c4BKzL3"

    def __init__(self, client: Client, *, limit: int | None, dry_run: bool):
        self._client = client
        self._limit = limit
        self._dry_run = dry_run

    def __call__(self) -> PruneResult:
        """Delete the closed items of the project.

        If 'limit' is set, only the first 'limit' closed items are deleted.
        """
        candidates = ListProjectV2Items(
            projectId=self.PROJECT_ID, query=_QUERY
        ).execute(self._client)
        logger.info("Found %d closed item(s)", len(candidates))

        # Deletion cannot be undone, so record every candidate before deleting any of
        # them. This log is what lets us re-add an item if it turns out to be wrong.
        for item in candidates:
            logger.info(
                "  Candidate %s %s %s '%s' %s",
                item.id,
                item.kind,
                item.state,
                item.title,
                item.url,
            )

        targets = candidates[: self._limit]
        if len(targets) < len(candidates):
            logger.info("Limited to the first %d item(s)", len(targets))

        deleted = []
        failed = []
        skipped = []
        for item in targets:
            if self._dry_run:
                logger.info("  [Dry Run] Would delete %s", item.id)
                skipped.append(item)
                continue

            try:
                DeleteProjectV2Item(projectId=self.PROJECT_ID, itemId=item.id).execute(
                    self._client
                )
            except Exception:
                logger.exception("  Failed to delete %s", item.id)
                failed.append(item)
                continue

            logger.info("  Deleted %s", item.id)
            deleted.append(item)

        return PruneResult(deleted=deleted, failed=failed, skipped=skipped)
