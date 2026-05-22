# Releasing a new version

## One-time setup

```cmd
.venv\Scripts\activate
pip install hatch
```

Create a PyPI API token at [pypi.org](https://pypi.org) → Account Settings → API tokens,
scoped to the `cielab-gamut-tools` project.

Store it in `%USERPROFILE%\.pypirc` so `hatch publish` never prompts:

```ini
[distutils]
index-servers =
    pypi

[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE
```

## Release process

### 1. Bump the version

```cmd
hatch version patch    # 0.1.0 → 0.1.1
hatch version minor    # 0.1.0 → 0.2.0
hatch version major    # 0.1.0 → 1.0.0
```

This updates `src/cielab_gamut_tools/__init__.py` automatically — nothing else to edit.

### 2. Commit and tag

```cmd
git add src/cielab_gamut_tools/__init__.py
git commit -m "bump version to 0.1.1"
git tag v0.1.1
git push && git push --tags
```

### 3. Build the frontend

The wheel includes the compiled frontend from `src/cielab_gamut_tools/ui/dist/`.
Rebuild it before packaging so the release has the latest UI:

```cmd
cd src\cielab_gamut_tools\ui\frontend
npm run build
cd ..\..\..\..
```

(On WSL / Git Bash: `make ui` from the project root.)

### 4. Build and publish

```cmd
rmdir /s /q dist
hatch build
hatch publish
```

That's it. Verify the new version is live:

```cmd
pip index versions cielab-gamut-tools
```

---

## Dry run on TestPyPI

```cmd
hatch publish --repo test
pip install --index-url https://test.pypi.org/simple/ cielab-gamut-tools
```

You will need a separate account and token on [test.pypi.org](https://test.pypi.org).
