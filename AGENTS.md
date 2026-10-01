# AGENTS.md

- Read `CONTRIBUTING.md` first.

## Commits and PRs

Keep each PR to a single commit, since PRs are squash-merged with "PR title + commit details".

Follow the rules below, derived from <https://cbea.ms/git-commit/> (read it for the background):

1. Separate the subject from the body with a blank line.
2. Limit the subject line to 80 characters.
3. Capitalize the subject line.
4. Do not end the subject line with a period.
5. Use the imperative mood in the subject line.
6. Wrap the body at 100 characters.
7. Use the body to explain what and why, not how.
   - State the scope so reviewers can judge what belongs.

Apply these project-specific rules over the ones above:

- Sign off with `git commit -s`.
- Add your standard `Co-Authored-By` trailer to the commit, after `Signed-off-by`.
- End the PR description with your standard attribution line instead.
- Keep only changes within the scope stated in the PR title and description.

If anything is unclear, check `git log` for examples and write the commit message in a similar style.
