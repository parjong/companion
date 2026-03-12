---
description: Clean up local git branches that do not have a corresponding remote branch on origin
---

This workflow identifies and deletes local git branches that are either "gone" (tracking a deleted remote branch) or have no tracking branch at all.

### Steps

// turbo
1. Update remote tracking information:
   ```bash
   git fetch --prune
   ```

2. List branches that should be deleted for user review:
   ```bash
   git branch -vv | grep -E '\[origin/.*: gone\]|(?<!\* )[^ ]+ +[a-f0-9]+  '
   ```
   > [!NOTE]
   > The second part of the regex matches branches without an upstream (no brackets `[...]`).

3. Identify the specific branch names to delete (excluding the current branch).

4. Delete the identified branches:
   ```bash
   git branch -D <branch_names>
   ```

5. Verify the cleanup:
   ```bash
   git branch -vv
   ```
