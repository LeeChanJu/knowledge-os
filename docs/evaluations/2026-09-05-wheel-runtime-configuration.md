# Wheel runtime configuration — 2026-09-05

## Observed gap

The local editable environment contained stale iCloud conflict files under `site-packages`, which
masked the source package. Recreating `.venv` as the README-prescribed non-editable install from
`uv.lock` restored stable imports. A separate clean-wheel test then found a real application
boundary gap: ontology, contracts, prompts, and the operations database already had
environment-configurable paths, but migrations were hard-coded to the process working directory in
the API, migration command, and Doctor.

## Minimal extension

`MIGRATIONS_PATH` now joins the existing runtime Settings contract. API startup, the migration CLI,
and Doctor all consume that one value. Relative paths retain repository-local behavior. Installed
wheels can instead receive absolute paths to the Git-controlled configuration and migration tree.
The files are deliberately not duplicated inside the wheel, avoiding two competing configuration
or migration sources of truth. No Source, Evidence, Knowledge, Governance, Retrieval, or Action
contract changed.

## Verification

- Ruff passed and all 50 unit tests passed.
- A wheel was built from the current source and installed with dependencies into a fresh temporary
  virtual environment.
- From `/tmp`, outside the repository, the installed package imported its API, configuration, and
  operational modules successfully.
- With absolute `OPS_DB_PATH`, `ONTOLOGY_PATH`, `CONTRACTS_PATH`, `PROMPTS_PATH`, and
  `MIGRATIONS_PATH`, the installed wheel generated OpenAPI and ran the live Doctor with all 35
  checks passing.
- The active `.venv` was recreated from the lockfile with `--no-editable`; Python imports the
  installed package and both the recovery and Doctor console scripts run without `PYTHONPATH`.

This proves relocatable execution when the deployment explicitly binds the wheel to one versioned
Git configuration tree. It does not turn the wheel into a self-contained configuration artifact,
which is intentional.
