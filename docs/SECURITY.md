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
environment files, whitespace/control-character filenames, private-key
containers, database files and dumps, release archives, runtime uploads, and
invoice test fixtures. Keep document fixtures generated during tests rather
than committing real-world files.

CI also runs the fixed-password-hash check. Any credential material needed for
tests must be generated at runtime and kept in test-only source.
