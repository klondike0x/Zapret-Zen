# GitHub Actions Workflow Consolidation Summary

## Changes Made (2026-06-24)

### 1. **Consolidated Workflow**
- **Merged** `build.yml` (PyInstaller-based) and `release.yml` (Nuitka-based) into a **single** `release.yml`
- **Kept** the Nuitka build process from the original `release.yml` as the primary build method
- **Archived** the old `build.yml` → renamed to `build.yml.obsolete`

### 2. **Fixed Critical Bugs**

#### Bug #1: `release_note.md` Ignored
**Problem:** The workflow was supposed to read `release_note.md` but it wasn't being used properly due to PowerShell multiline output issues with `$env:GITHUB_OUTPUT`.

**Solution:**
- Changed approach to write release notes to a temporary file `release_body.txt`
- Use `gh release create --notes-file release_body.txt` instead of trying to pass multiline content through environment variables
- Priority order now works correctly:
  1. `workflow_dispatch` input `body` (if provided)
  2. `release_note.md` file content (if exists and non-empty)
  3. Default fallback message: "Zapret-Zen {version} release."

#### Bug #2: Re-running Workflow Overwrites Release Title/Description
**Problem:** Re-running the workflow for an existing tag would overwrite the release title and description.

**Solution:**
- Added `Check if release exists` step using `gh release view <tag>`
- **New release path** (when tag doesn't exist):
  - Creates release with `gh release create`
  - Sets title, description from inputs or `release_note.md`
  - Uploads all assets
- **Existing release path** (when tag already exists):
  - **Skips** `gh release create` entirely
  - **Only** runs `gh release upload <tag> <files> --clobber`
  - Preserves original title and description
  - Replaces/updates only the binary assets

### 3. **Enhanced Triggers**
- **Push to tags** (`v*`): Automatically triggers on tag push
- **workflow_dispatch**: Manual trigger with inputs for tag, title, prerelease flag, and body

### 4. **Build Process (Unchanged)**
Kept the exact Nuitka-based build from the original `release.yml`:
- Windows x64 build on `windows-latest`
- Windows ARM64 build on `windows-11-arm`
- Version injection into `pyproject.toml`
- Universal installer creation
- Portable ZIP packages

### 5. **Key Improvements**
- Uses `gh` CLI (GitHub CLI) for better control and reliability
- Proper error handling with exit codes
- Clearer logging for debugging
- Idempotent: safe to re-run multiple times for the same tag
- Uses `fetch-depth: 0` for full git history access

## Files Modified
- ✅ `.github/workflows/release.yml` - **Rewritten** (consolidated workflow)
- 📦 `.github/workflows/build.yml.obsolete` - **Archived** (old PyInstaller workflow)
- ✨ `.github/workflows/ci.yml` - **Unchanged** (CI builds only)

## Testing Recommendations
1. Test with a new tag (e.g., `v2.3.0-test`):
   - Should create new release
   - Should read from `release_note.md` if no body provided
2. Re-run the same workflow for the same tag:
   - Should NOT change title/description
   - Should only update/replace the assets
3. Test `workflow_dispatch` with custom body input:
   - Should use the provided body instead of `release_note.md`

## Technical Details

### How `release_note.md` is Read
```powershell
# Read file with proper encoding
$content = Get-Content "release_note.md" -Raw -Encoding UTF8

# Write to temporary file (avoids multiline GITHUB_OUTPUT issues)
$content | Out-File -FilePath "release_body.txt" -Encoding UTF8 -NoNewline

# Use with gh CLI
gh release create $tag --notes-file release_body.txt
```

### How Idempotent Updates Work
```powershell
# Check if release exists
gh release view $tag 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
  # EXISTS: Only upload assets with --clobber
  gh release upload $tag $files --clobber
} else {
  # NEW: Create release with title, body, and assets
  gh release create $tag --title $name --notes-file body.txt $files
}
```

---
**Consolidation completed by:** AI DevOps Engineer  
**Date:** 2026-06-24
