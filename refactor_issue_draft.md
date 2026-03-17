# Issue: Refactor GitHub GraphQL Logic in Existing Tools

## Description
Currently, `AddProjectV2DraftIssue`, `UpdateTextFieldValue`, and `ProjectItemID` have been extracted into a shared module `src/endpoint/readit/github.py`. This was done as part of the implementation of the evaluation queue registration CLI.

To maintain consistency and reduce code duplication, we should refactor other existing tools that use these same GraphQL mutations.

## Tasks
- Refactor `src/endpoint/readit/app/send_to_queue_v2.py` to use `AddProjectV2DraftIssue` and `UpdateTextFieldValue` from `endpoint.readit.github`.
- Identify and refactor any other tools using similar GitHub Project V2 mutations.
- Ensure all environment variable access is isolated within the `main` functions.
