# GitLab runner recovery report

Date: 2026-08-04

This runbook records only redacted operational facts. It must not contain SSH
passwords, GitLab runner authentication tokens, environment values, private
keys, database credentials, or JWT secrets.

## Repository finding

The deployment pipeline currently has no `tags:` declarations in
`.gitlab-ci.yml`. This does not match the expected runner architecture and can
leave tagged jobs pending when the only online runner is tagged
`rainbow-fashions-prod-runner`.

Required job routing after review and test:

| Workload | Runner tag | Executor | Protection |
| --- | --- | --- | --- |
| Tests, lint, typecheck, secret checks, Compose validation, image build | `rainbow-ci` | Docker | unprotected project runner; no untagged jobs |
| Release extraction, backup, deployment, migration, health checks | `rainbow-production` | Shell | protected project runner; no untagged jobs |

Do not assign both permanent tags to one runner. Keep the existing runner
registered until two replacement/reconfigured runners are visible as online and
have each run a safe test job.

## Current remote-access result

A non-interactive SSH check reached `178.238.237.182`, but no authorized key or
credential is available in this execution environment. Authentication therefore
failed without an interactive password prompt. No server commands were run and
no production business data was modified.

## Required server baseline

Run these commands from the recovered Contabo console or a verified admin SSH
session, redact token values before saving output, and attach the results to the
change record:

```bash
hostname; hostname -I; date -Is; uptime
cat /etc/os-release
systemctl status gitlab-runner docker nginx --no-pager || true
gitlab-runner list
gitlab-runner verify
sed -E 's/(token = ).*/\1"REDACTED"/' /etc/gitlab-runner/config.toml
install -d -m 700 /root/rainbow-runner-backup
cp /etc/gitlab-runner/config.toml /root/rainbow-runner-backup/config.toml.before-runner-repair
chmod 600 /root/rainbow-runner-backup/config.toml.before-runner-repair
```

Never print the unredacted runner configuration or unregister the existing
runner before the replacement/reconfiguration is verified.

## Safe runner repair sequence

1. Inspect the existing runner executor and tags. Reuse it as
   `rainbow-production` only if it is a valid shell executor with deployment
   permissions; otherwise reuse a safe Docker runner as `rainbow-ci`.
2. Register only the missing runner using project-runner authentication tokens
   entered directly on the server. Unset token variables immediately afterwards.
3. In GitLab, lock both runners to this project, disable untagged jobs, protect
   the production runner, and protect the `shop-inventory` branch. Do not weaken
   branch protection to make a job schedule.
4. Add `gitlab-runner` to the Docker group only after confirming it needs Docker
   builds. Verify with `sudo -u gitlab-runner docker version` and
   `sudo -u gitlab-runner docker compose version`.
5. Create the deployment directories with mode `0750` and ownership
   `gitlab-runner:gitlab-runner`; do not recursively change Docker-volume
   ownership.
6. Run a safe CI test job and a safe production-runner test job. Neither may
   access business data or deploy an application release.
7. Add the reviewed CI tags only after both runners are online. Deployment jobs
   must retain `resource_group: rainbow-fashions-production` and branch rules.
8. Retry pipeline `#206` once only after the runner tests pass. Record a safe
   error category and redacted final log lines if it fails.

## Remaining verification

- [ ] Existing runner executor and disposition verified
- [ ] CI Docker runner online with `rainbow-ci`
- [ ] Protected shell runner online with `rainbow-production`
- [ ] GitLab project/branch protection and untagged-job settings verified
- [ ] `/opt/rainbow-fashions/shared/backend.env` exists and is non-empty; its
      contents were not viewed
- [ ] Nginx, DNS, certificate, firewall, and local/public health checks pass
- [ ] Pipeline `#206` retried once and outcome recorded

Do not perform the SSH-hardening changes until a second key-authenticated admin
session is confirmed. Keep Contabo console recovery available throughout.
