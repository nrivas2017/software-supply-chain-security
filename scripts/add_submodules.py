from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOS_FILE = REPO_ROOT / "data" / "repos.json"


def _run_git_command(args: list[str], cwd: Path, error_msg: str) -> bool:
    try:
        result = subprocess.run(args, check=True, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        print("Error: 'git' command not found. Is Git installed and in your PATH?")
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or str(error)
        print(f"{error_msg}: {detail}")
        return False

    if result.stdout.strip():
        print(result.stdout.strip())
    return True


def _load_repositories(repos_file: Path) -> list[dict]:
    if not repos_file.exists():
        raise FileNotFoundError(f"Repositories file not found: {repos_file}")

    data = json.loads(repos_file.read_text(encoding="utf-8"))
    repositories = data.get("repositories", [])
    if not isinstance(repositories, list):
        raise ValueError("'repositories' must be a list in data/repos.json")

    return repositories


def _validate_repo_entry(repo: dict) -> tuple[str, Path, str | None]:
    url = repo.get("url")
    raw_path = repo.get("path")
    ref = repo.get("ref")

    if not url or not raw_path:
        raise ValueError(f"Invalid repository entry: {repo}")

    path = (REPO_ROOT / raw_path).resolve()
    repos_root = (REPO_ROOT / "data" / "repos").resolve()
    if repos_root not in path.parents and path != repos_root:
        raise ValueError(f"Repository path must stay under data/repos: {raw_path}")

    return url, path, ref


def sync_repositories(
    repos_file: Path = DEFAULT_REPOS_FILE,
    update: bool = True,
    dry_run: bool = False,
) -> int:
    repositories = _load_repositories(repos_file)
    if not repositories:
        print("No repositories configured.")
        return 0

    errors = 0
    for repo in repositories:
        try:
            url, path, ref = _validate_repo_entry(repo)
        except ValueError as error:
            print(error)
            errors += 1
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path_exists = path.exists()
        path_is_empty = path_exists and path.is_dir() and not any(path.iterdir())
        if not path_exists or path_is_empty:
            print(f"Cloning {url} into {path.relative_to(REPO_ROOT)}")
            if dry_run:
                continue
            if not _run_git_command(["git", "clone", url, str(path)], REPO_ROOT, f"Failed to clone {url}"):
                errors += 1
                continue
        elif not (path / ".git").exists():
            print(f"Skipping {path.relative_to(REPO_ROOT)}: directory exists but is not a Git repository.")
            errors += 1
            continue
        elif update:
            print(f"Updating {path.relative_to(REPO_ROOT)}")
            if dry_run:
                continue
            if not _run_git_command(["git", "fetch", "--all", "--prune"], path, f"Failed to fetch {path.name}"):
                errors += 1
                continue

        if ref:
            print(f"Checking out {ref} in {path.relative_to(REPO_ROOT)}")
            if dry_run:
                continue
            if not _run_git_command(["git", "checkout", ref], path, f"Failed to checkout {ref} in {path.name}"):
                errors += 1

    if errors:
        print(f"Repository sync finished with {errors} error(s).")
        return 1

    print("Repository sync complete.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clone or update example repositories declared in data/repos.json."
    )
    parser.add_argument(
        "--repos-file",
        type=Path,
        default=DEFAULT_REPOS_FILE,
        help="Path to the repositories configuration file.",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Do not fetch updates for repositories that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show clone/update actions without changing data/repos.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return sync_repositories(args.repos_file, update=not args.no_update, dry_run=args.dry_run)
    except Exception as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
