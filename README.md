# filesystem_scanner

A read-only Python script that scans a filesystem path and reports usage statistics.

It walks the directory tree, calculates recursive directory sizes, identifies hidden files and directories, and handles permission errors gracefully. No external dependencies are required—only the Python standard library.

## Features

- Total size, file count, directory count, and hidden item counts
- Largest directories by size
- Optional detailed lists of files, directories, or hidden items
- Sorting by size or name
- Configurable output limits
- Skips symlinks to avoid leaving the requested tree
- Collects and reports access errors without aborting the scan

## Requirements

- Python 3.6 or later

## Usage

```bash
python3 filesystem_scanner.py /path/to/scan
```

### Options

- `--usage` — Show the largest directories (shown by default if no other output flags are given)
- `--files` — List files
- `--dirs` — List directories
- `--hidden` — Show hidden files and directories
- `--sort {size,name}` — Sort order (default: size)
- `--limit N` — Maximum number of items to display (default: 50)

### Examples

```bash
# Summary + largest directories
python3 filesystem_scanner.py ~/Documents

# Show the 20 largest files
python3 filesystem_scanner.py /var/log --files --limit 20

# List all directories sorted by name
python3 filesystem_scanner.py . --dirs --sort name --limit 100

# Include hidden items
python3 filesystem_scanner.py ~ --hidden
```

## Notes

The tool is intentionally read-only. It never modifies the filesystem.

Directory sizes are calculated by summing the sizes of all regular files contained within them (recursively). Symlinked directories are not followed.

## License

MIT
