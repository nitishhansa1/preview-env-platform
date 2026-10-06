# Contributing to Preview Environment Platform

Thank you for your interest in contributing to **preview-env-platform**!

## Development & Contribution Workflow

We practice GitOps with dynamic, per-branch ephemeral preview environments:

1. **Branch**: Create a feature or fix branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(...)`: New features
   - `fix(...)`: Bug fixes
   - `docs(...)`: Documentation changes
   - `chore(...)`: Tooling, configuration, or dependencies
   - `ci(...)`: CI/CD workflows and automation
3. **Pull Request**: Open a PR targeting `main`.
4. **Preview**:
   - GitHub Actions automatically runs tests and builds container images tagged with your PR number.
   - Argo CD detects the PR and provisions an isolated preview environment in namespace `pr-<number>`.
   - The bot comments on your PR with the live URL (`http://pr-<number>.127.0.0.1.nip.io`).
5. **Merge**: Once reviews pass and CI checks succeed, merge to `main`. Argo CD automatically tears down the ephemeral preview environment and cleans up all associated resources.
