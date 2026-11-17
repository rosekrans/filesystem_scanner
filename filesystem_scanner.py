#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable size."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    size = float(size_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:,.2f} {unit}"
        size /= 1024

    return f"{size_bytes:,} B"


def is_hidden(path: Path) -> bool:
    """Return True if the file or directory is hidden."""
    return path.name.startswith(".")


def scan_filesystem(root: Path):
    """
    Scan the filesystem recursively.

    Returns:
        files              List of file information
        directories        List of directory information
        hidden_files       List of hidden files
        hidden_directories List of hidden directories
        errors             List of paths that could not be accessed
    """

    files = []
    directories = []
    hidden_files = []
    hidden_directories = []
    errors = []

    # Track directory sizes separately so we can calculate
    # recursive directory usage.
    directory_sizes = {}

    try:
        root = root.resolve()
    except OSError as exc:
        print(f"ERROR: Cannot resolve path: {exc}", file=sys.stderr)
        sys.exit(1)

    if not root.exists():
        print(f"ERROR: Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if not root.is_dir():
        print(f"ERROR: Path is not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    # os.walk is used instead of Path.rglob so that we can
    # gracefully handle permission errors.
    for current_root, dirnames, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=lambda error: errors.append(str(error)),
    ):
        current_path = Path(current_root)

        # Remove symlinked directories from traversal.
        # This prevents accidentally walking outside the requested
        # filesystem or following recursive symlinks.
        real_dirs = []

        for dirname in dirnames:
            path = current_path / dirname

            try:
                if path.is_symlink():
                    continue
            except OSError:
                continue

            real_dirs.append(dirname)

        dirnames[:] = real_dirs

        # Register directories.
        for dirname in dirnames:
            directory = current_path / dirname

            try:
                stat = directory.stat()
            except OSError as exc:
                errors.append(f"{directory}: {exc}")
                continue

            directory_sizes[directory] = 0

            directory_info = {
                "path": directory,
                "name": dirname,
                "size": 0,
                "hidden": is_hidden(directory),
            }

            directories.append(directory_info)

            if directory_info["hidden"]:
                hidden_directories.append(directory_info)

        # Process files.
        for filename in filenames:
            file_path = current_path / filename

            try:
                if file_path.is_symlink():
                    continue

                stat = file_path.stat()
                size = stat.st_size

            except OSError as exc:
                errors.append(f"{file_path}: {exc}")
                continue

            file_info = {
                "path": file_path,
                "name": filename,
                "size": size,
                "hidden": is_hidden(file_path),
            }

            files.append(file_info)

            if file_info["hidden"]:
                hidden_files.append(file_info)

            # Add file size to every parent directory.
            parent = current_path

            while True:
                if parent in directory_sizes:
                    directory_sizes[parent] += size

                if parent == root:
                    break

                parent = parent.parent

    # The requested root directory needs to be included in the
    # directory results.
    root_size = sum(file["size"] for file in files)

    root_info = {
        "path": root,
        "name": root.name or str(root),
        "size": root_size,
        "hidden": is_hidden(root),
    }

    directories.append(root_info)

    # Update calculated recursive directory sizes.
    for directory_info in directories:
        directory = directory_info["path"]

        if directory == root:
            directory_info["size"] = root_size
        else:
            directory_info["size"] = directory_sizes.get(directory, 0)

    return (
        files,
        directories,
        hidden_files,
        hidden_directories,
        errors,
    )


def print_summary(
    root,
    files,
    directories,
    hidden_files,
    hidden_directories,
    errors,
):
    """Print the filesystem summary."""

    total_size = sum(file["size"] for file in files)

    print()
    print("Filesystem Scanner")
    print("==================")
    print()
    print(f"Path:                 {root}")
    print(f"Total size:           {format_size(total_size)}")
    print(f"Files:                {len(files):,}")
    print(f"Directories:          {len(directories):,}")
    print(f"Hidden files:         {len(hidden_files):,}")
    print(f"Hidden directories:   {len(hidden_directories):,}")
    print(f"Access errors:        {len(errors):,}")
    print()


def print_usage(directories, limit=25):
    """Print largest directories."""

    print("Largest Directories")
    print("===================")
    print()

    sorted_directories = sorted(
        directories,
        key=lambda item: item["size"],
        reverse=True,
    )

    for directory in sorted_directories[:limit]:
        print(
            f"{format_size(directory['size']):>12}  "
            f"{directory['path']}"
        )

    print()


def print_files(files, sort_by="size", limit=50):
    """Print files."""

    if sort_by == "name":
        sorted_files = sorted(
            files,
            key=lambda item: str(item["path"]).lower(),
        )
    else:
        sorted_files = sorted(
            files,
            key=lambda item: item["size"],
            reverse=True,
        )

    print("Files")
    print("=====")
    print()

    for file_info in sorted_files[:limit]:
        print(
            f"{format_size(file_info['size']):>12}  "
            f"{file_info['path']}"
        )

    if len(files) > limit:
        print()
        print(f"... showing top {limit} of {len(files):,} files")

    print()


def print_directories(directories, sort_by="size", limit=50):
    """Print directories."""

    if sort_by == "name":
        sorted_directories = sorted(
            directories,
            key=lambda item: str(item["path"]).lower(),
        )
    else:
        sorted_directories = sorted(
            directories,
            key=lambda item: item["size"],
            reverse=True,
        )

    print("Directories")
    print("===========")
    print()

    for directory in sorted_directories[:limit]:
        print(
            f"{format_size(directory['size']):>12}  "
            f"{directory['path']}"
        )

    if len(directories) > limit:
        print()
        print(
            f"... showing top {limit} "
            f"of {len(directories):,} directories"
        )

    print()


def print_hidden(hidden_files, hidden_directories):
    """Print hidden files and directories."""

    print("Hidden Directories")
    print("==================")
    print()

    if hidden_directories:
        for directory in sorted(
            hidden_directories,
            key=lambda item: item["size"],
            reverse=True,
        ):
            print(
                f"{format_size(directory['size']):>12}  "
                f"{directory['path']}"
            )
    else:
        print("None found.")

    print()
    print("Hidden Files")
    print("============")
    print()

    if hidden_files:
        for file_info in sorted(
            hidden_files,
            key=lambda item: item["size"],
            reverse=True,
        ):
            print(
                f"{format_size(file_info['size']):>12}  "
                f"{file_info['path']}"
            )
    else:
        print("None found.")

    print()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Read-only filesystem usage scanner."
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Filesystem path to scan.",
    )

    parser.add_argument(
        "--usage",
        action="store_true",
        help="Show largest directories.",
    )

    parser.add_argument(
        "--files",
        action="store_true",
        help="Show files.",
    )

    parser.add_argument(
        "--dirs",
        action="store_true",
        help="Show directories.",
    )

    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Show hidden files and directories.",
    )

    parser.add_argument(
        "--sort",
        choices=["size", "name"],
        default="size",
        help="Sort output by size or name. Default: size.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of items to display. Default: 50.",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.limit < 1:
        print("ERROR: --limit must be greater than zero.")
        sys.exit(1)

    (
        files,
        directories,
        hidden_files,
        hidden_directories,
        errors,
    ) = scan_filesystem(args.path)

    root = args.path.resolve()

    print_summary(
        root,
        files,
        directories,
        hidden_files,
        hidden_directories,
        errors,
    )

    # If no specific output flag was supplied, show the summary
    # and largest directories.
    if not any(
        [
            args.usage,
            args.files,
            args.dirs,
            args.hidden,
        ]
    ):
        print_usage(directories, args.limit)

    if args.usage:
        print_usage(directories, args.limit)

    if args.files:
        print_files(files, args.sort, args.limit)

    if args.dirs:
        print_directories(
            directories,
            args.sort,
            args.limit,
        )

    if args.hidden:
        print_hidden(
            hidden_files,
            hidden_directories,
        )

    if errors:
        print("Access Errors")
        print("=============")
        print()

        for error in errors:
            print(f"  {error}")

        print()


if __name__ == "__main__":
    main()
