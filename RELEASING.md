# Releasing a new version

## Release process

### 1. Bump the version

```bash
hatch version patch    # 0.1.0 → 0.1.1
hatch version minor    # 0.1.0 → 0.2.0
hatch version major    # 0.1.0 → 1.0.0
```

Hatch prints the new version number to the terminal and updates
`src/cielab_gamut_tools/__init__.py`. Nothing else needs editing.

### 2. Commit and push

```bash
git add src/cielab_gamut_tools/__init__.py
git commit -m "bump version"
git push
```

That's it. The rest is automated:

- **auto-tag** workflow detects the version file change, reads the new version,
  and pushes a `vX.Y.Z` git tag.
- **release** workflow triggers on that tag, builds the frontend and wheel,
  and publishes to PyPI via OIDC (no token required locally).
- **Excavator** (in the `scoop-bucket` repo) runs daily and updates the Scoop
  manifest when it sees the new PyPI version.

Verify the release is live:

```bash
pip index versions cielab-gamut-tools
```

---

## One-time setup (PyPI Trusted Publisher)

This replaces the old `.pypirc` API token approach. Done once; never needs repeating.

### On PyPI

1. Go to [pypi.org](https://pypi.org) → your account → **Your projects** →
   `cielab-gamut-tools` → **Settings** → **Publishing**
2. Under **Add a new publisher**, choose **GitHub Actions** and fill in:
   - **Owner:** `CIELab-gamut-tools`
   - **Repository:** `cielab-gamut-tools-py`
   - **Workflow filename:** `release.yml`
   - **Environment name:** `release`
3. Save.

### On GitHub

1. Go to the repository → **Settings** → **Environments** → **New environment**
2. Name it `release` (must match the workflow exactly)
3. No additional protection rules are needed for a single-developer project,
   but you can add them if you want an extra confirmation step before publish.

---

## Dry run on TestPyPI

Set up a Trusted Publisher on [test.pypi.org](https://test.pypi.org) with the same
details, but use environment name `release-test` and a separate workflow file
(copy `release.yml`, change the environment name and add `--repository testpypi`
to the publish step).

Alternatively, build and publish manually for a one-off test:

```bash
hatch build
pip install hatch
hatch publish --repo test
```

You will need a separate API token on [test.pypi.org](https://test.pypi.org) for
the manual path.
