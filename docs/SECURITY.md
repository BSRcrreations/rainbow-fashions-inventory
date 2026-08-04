# Secret and environment-file handling

Real environment files belong outside version control. Create them from one of
the reviewed examples, keep them in the ignored local path, and set permissions
to owner-read/write only (`chmod 600`). Production environment files belong in
the protected host-level shared configuration location, not in a release or Git
worktree.

The five tracked examples contain only `CHANGE_ME` placeholders for credentials,
JWT material, connection values, and service URLs. Do not replace placeholders
with reusable values in a commit, issue, log, or screenshot.

Run the tracked-secret check before committing:

```bash
bash scripts/security/check_tracked_secrets.sh
```

The check reports violating file paths only. It rejects real or oddly named
environment files, whitespace/control-character filenames, private keys,
database dumps, and likely hard-coded credential assignments.
