import logging
import os
import click
import requests
from endpoint.readit.app.summarize_other import get_llm

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

# TODO: Introduce a centralized configuration module to manage repository and owner configurations dynamically in the future.
_OWNER = "parjong"
_REPO = "companion"
_VARIABLE_NAME = "READIT_SUMMARY_MODEL"


def validate_model(model_name: str) -> None:
    """Validates the model by performing a low-cost 2-token ping invocation."""
    logger.info("Validating model '%s' using 2-token ping...", model_name)
    llm = get_llm(model_name)
    llm.invoke("Hi", max_output_tokens=1)
    logger.info("Model validation succeeded.")


class UpdateGitHubVariable:
    """Updates the GITHUB Actions Repository Variable via GitHub Actions REST API."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def __call__(self, model_name: str) -> None:
        url = f"https://api.github.com/repos/{_OWNER}/{_REPO}/actions/variables/{_VARIABLE_NAME}"
        data = {
            "name": _VARIABLE_NAME,
            "value": model_name,
        }

        logger.info(
            "Dry-run mode inactive. Requesting GitHub API to update '%s' to '%s'...",
            _VARIABLE_NAME,
            model_name,
        )

        # GET request to check variable existence
        logger.info("Checking if variable '%s' exists via GET...", _VARIABLE_NAME)
        get_response = requests.get(url, headers=self.headers)

        # Early exit if the variable does not exist (404) or unexpected GET status codes
        if get_response.status_code == 404:
            raise click.ClickException(
                f"GitHub Repository Variable '{_VARIABLE_NAME}' does not exist. "
                "Please create it first in your repository settings or run the following GitHub CLI command:\n\n"
                f'  gh variable set {_VARIABLE_NAME} --body "{model_name}"'
            )
        if get_response.status_code != 200:
            logger.error(
                "GitHub Actions Variables API (Get) returned status code %d: %s",
                get_response.status_code,
                get_response.text,
            )
            get_response.raise_for_status()

        # Variable exists, execute PATCH update
        logger.info("Variable '%s' exists. Updating via PATCH...", _VARIABLE_NAME)
        response = requests.patch(url, headers=self.headers, json=data)

        if response.status_code != 204:
            logger.error(
                "GitHub Actions Variables API (Update) returned status code %d: %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        logger.info(
            "[+] Success: GitHub Variable '%s' has been successfully updated to '%s'.",
            _VARIABLE_NAME,
            model_name,
        )


@click.command()
@click.option(
    "--dry-run/--no-dry-run",
    default=not os.environ.get("CI"),
    help="Default is True unless CI environment variable is set.",
)
@click.argument("model_name", required=True)
def main(dry_run: bool, model_name: str) -> None:
    """Validates the model and updates GITHUB Repository Variable in a single atomic flow."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting model update process...")

    token = os.environ.get("OWNER_TOKEN")
    if not token:
        logger.error("Failed to update GitHub Actions Repository Variable.")
        raise click.ClickException("OWNER_TOKEN environment variable is missing.")

    validate_model(model_name)

    if dry_run:
        logger.info(
            "Dry-run mode active (CI variable not detected or forced). Skipping GitHub Variable update."
        )
        return

    update_github_variable = UpdateGitHubVariable(token)
    update_github_variable(model_name)


if __name__ == "__main__":
    main()
