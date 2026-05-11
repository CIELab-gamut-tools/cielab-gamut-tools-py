# Releasing a new version

## One-time setup

```cmd
.venv\Scripts\activate
pip install hatch
```

Create a PyPI API token at [pypi.org](https://pypi.org) → Account Settings → API tokens,
scoped to the `cielab-gamut-tools` project. `hatch publish` will prompt for it on first
use and cache it.

## Release process

### 1. Bump the version

```cmd
hatch version patch    # 0.1.0 → 0.1.1
hatch version minor    # 0.1.0 → 0.2.0
hatch version major    # 0.1.0 → 1.0.0
```

This updates `pyproject.toml` automatically — nothing else to edit.

### 2. Commit and tag

```cmd
git add pyproject.toml
git commit -m "bump version to 0.1.1"
git tag v0.1.1
git push && git push --tags
```

### 3. Build and publish

```cmd
hatch build
hatch publish
```

That's it. Verify the new version is live:

```cmd
pip index versions cielab-gamut-tools
```

### Clean up between releases

```cmd
rmdir /s /q dist
```

---

## Dry run on TestPyPI

```cmd
hatch publish --repo test
pip install --index-url https://test.pypi.org/simple/ cielab-gamut-tools
```

You will need a separate account and token on [test.pypi.org](https://test.pypi.org).
