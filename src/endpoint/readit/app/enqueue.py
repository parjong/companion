import functools
import logging
import os
import click
from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport
from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step
from endpoint.readit.steps.fetch import FetchStep
from endpoint.readit.steps.ensure import EnsureStep
from endpoint.readit.steps.ensure import AlreadyInQueueError
from endpoint.readit.app.send_to_personal import AlreadyInArchiveError
from endpoint.readit.steps.summarize import SummarizeStep
from endpoint.readit.steps.add_queue import AddQueueStep
from endpoint.readit.steps.send import SendStep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


class SaveStep(Step):
    """Pipeline step that saves the current blackboard to a file if a path is provided."""

    def __init__(self, path: str | None, step_name: str) -> None:
        self._path = path
        self._step_name = step_name

    def __call__(self, bb: Blackboard) -> Blackboard:
        if self._path:
            with open(self._path, "w", encoding="utf-8") as f:
                f.write(bb.model_dump_json(indent=2))
            logger.info(
                "Saved intermediate %s data to '%s'", self._step_name, self._path
            )
        return bb


def translate_domain_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AlreadyInQueueError as e:
            logger.info(
                "URL is already in the evaluation queue. Skipping remaining steps."
            )
            raise click.ClickException(str(e))
        except AlreadyInArchiveError as e:
            logger.info(
                "URL is already in the personal archive. Skipping remaining steps."
            )
            raise click.ClickException(str(e))

    return wrapper


@click.command()
@click.option(
    "--dry-run/--no-dry-run",
    default=not os.environ.get("CI"),
    help="Default is True unless CI environment variable is set.",
)
@click.option(
    "--fetch-path",
    type=click.Path(writable=True),
    help="Optional path to save intermediate blackboard after fetching.",
)
@click.option(
    "--summary-path",
    type=click.Path(writable=True),
    help="Optional path to save intermediate blackboard after summarizing.",
)
@click.argument("url")
@translate_domain_exceptions
def main(
    url: str, dry_run: bool, fetch_path: str | None, summary_path: str | None
) -> None:
    # Pre-flight environment variables check
    missing_vars = []
    for var in ["OWNER_TOKEN", "GITHUB_GRAPHQL_URL", "GEMINI_API_KEY"]:
        if not os.environ.get(var):
            missing_vars.append(var)
    if missing_vars:
        raise click.UsageError(
            f"Missing required environment variable(s): {', '.join(missing_vars)}. "
            "Please ensure they are defined in your environment."
        )

    # Initialize GQL Client
    github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]
    owner_token = os.environ["OWNER_TOKEN"]
    client = Client(
        transport=HTTPTransport(
            url=github_graphql_url,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    )

    bb = Blackboard(url=url)

    logger.info("Starting pipeline for URL: %s", url)

    # Execute flat pipeline
    bb = FetchStep()(bb)
    bb = SaveStep(fetch_path, "fetched")(bb)
    bb = EnsureStep(client)(bb)
    bb = SummarizeStep()(bb)
    bb = SaveStep(summary_path, "summarized")(bb)
    bb = AddQueueStep(client)(bb)
    bb = SendStep(dry_run=dry_run)(bb)

    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
