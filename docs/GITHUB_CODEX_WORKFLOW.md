# Canonical GitHub → Codex Cloud → Databricks workflow

## Canonical repository connection (2026-10-25)

- Public repository: https://github.com/cevateness/winterops-databricks-lab.
- Local branch: `main`, tracking `origin/main` through the HTTPS remote `https://github.com/cevateness/winterops-databricks-lab.git`.
- This checkout uses Git Credential Manager for authentication. Commit identity is configured locally using the account's GitHub noreply address; no credentials are stored in project files.
- Local `pull.ff=only` prevents a pull from creating an unexpected merge when local and remote history diverge.
- The initial upload includes source code, documentation, synthetic data and the reported aggregate QA fixture. Raw operational data and local credential files remain excluded by `.gitignore`.

For another computer, clone the existing repository rather than creating a new GitHub repository or rerunning the initial publishing script:

```powershell
git clone https://github.com/cevateness/winterops-databricks-lab.git
cd winterops-databricks-lab
```

## Everyday sync

Start with a clean working tree, then download changes from GitHub:

```powershell
git status --short --branch
git pull --ff-only
```

After editing, run the relevant offline checks and review the files you intend to publish:

```powershell
python -m unittest discover -s tests -v
git diff
git status --short
# Replace these example paths with the files you actually changed.
git add README.md docs/GITHUB_CODEX_WORKFLOW.md
git diff --cached
git commit -m "Describe the change"
git push
```

Saving files does not automatically upload them: `commit` records a local version and `push` uploads those commits. `pull` downloads and integrates remote commits. Commit or stash unfinished changes before pulling. If a push is rejected because GitHub has newer commits, fetch and inspect the differences before integrating them; do not force push.

Check the [Actions page](https://github.com/cevateness/winterops-databricks-lab/actions) for offline CI results. No Databricks credentials are needed for that workflow.

## Codex Cloud connection

As of 2026-10-25, the user reports a published WinterOps environment but its selection from the extension remains unresolved. **Local development is the chosen path for now.** Cloud selection is not a prerequisite for tests, feature branches, or review PRs. Use the same repository task locally; see `ANALYTICS_SLICE.md` for the implemented analytics slice. Do not change or republish the user's Cloud environment as part of this work.

1. Open ChatGPT/Codex on web or desktop; start a new coding task and select **Work in → Cloud → Create environment**.
2. Connect GitHub if prompted and choose the **new** public WinterOps repository. Access to a GitHub repository in ChatGPT and permissions for Codex Cloud may require separate authorization or repository selection.
3. Let the environment inspect/install dependencies. Typical setup: `python -m pip install -e .`; then `python -m unittest discover -s tests -v`. No live Databricks credentials are needed for the first task.
4. Publish the configured environment. Copy/paste `docs/CODEX_CLOUD_TASK.md` into a new cloud coding task.
5. Review its diff and test report; open and merge a PR when satisfactory. Codex Cloud is a separate compute environment; it cannot automatically access the local Databricks workspace or credentials.

Official guidance: https://learn.chatgpt.com/docs/cloud and https://learn.chatgpt.com/docs/environments/cloud-environments

## ChatGPT Project relationship

- **GitHub** owns the current code, tests, documentation and issues/PRs.
- **Codex Cloud** edits the connected GitHub repo in an isolated environment.
- **This ChatGPT Project** stays our architecture discussion and learning notebook. The reference file uploaded to the ChatGPT Project is not automatically changed when GitHub's `PROJECT_REFERENCE.md` changes. Ask ChatGPT to review the current GitHub code and update this project's reference only when a relevant decision changes.
- **Databricks** stores operational data and hosts Spark/Delta computations. It is not the public code repository.

## Databricks automation (later, not a prerequisite)

- Authenticate locally using `databricks auth login --host <real-workspace-url> --profile winterops` with browser login, then use `scripts/test_databricks_connection.ps1 -Profile winterops -WorkspaceHost <real-workspace-url>` for read-only verification.
- **Do not upload** `.databrickscfg` or credentials to GitHub/Codex. Browser-based OAuth profiles on your Windows computer are **not** transferred into Codex Cloud.
- Do not set GitHub Actions jobs that mutate Databricks unless credentials, policy and target workspace have been explicitly reviewed. Free Edition has different limitations from a paid production workspace.
- Local scripts/CLI are fallback for Databricks execution if Codex Cloud cannot securely reach/authenticate the workspace. Code development, reviews and CI can continue cloud-only.
