# Codex Recovery

A small local recovery CLI for files changed by coding agents or people.
Stash a copy before editing, move an item into a private recovery directory,
list entries, and restore without overwriting an existing destination.

Independent utility. Not affiliated with or endorsed by OpenAI. Adapted from
an original local helper; this portable first release deliberately contains no
Time Machine, APFS, snapshot, automatic cleanup, or backup administration.

## Requirements and installation

Python 3.10 or newer on macOS or Linux. Standard library only; no network access
or background process. macOS may require installing Python separately.

Download the `codex-recovery` and `SHA256SUMS` assets from the tagged GitHub
release. Verify the downloaded file before installing:

```sh
shasum -a 256 -c SHA256SUMS
mkdir -p "$HOME/.local/bin"
install -m 755 codex-recovery "$HOME/.local/bin/codex-recovery"
"$HOME/.local/bin/codex-recovery" --version
```

Add `$HOME/.local/bin` to your PATH if needed. Check for an existing command
first with `command -v codex-recovery`; preserve any existing installation
before replacing it. You can also run the downloaded script directly.

## Use

```sh
codex-recovery stash ./config.json
codex-recovery trash ./old-folder
codex-recovery list
codex-recovery restore ENTRY_ID
```

`stash` leaves the source in place. `trash` moves the source and therefore
requires that source and store be on the same filesystem. Both print an entry
ID. `list` prints one JSON object per line. Restore copies to the recorded
original path and retains its recovery entry. If that destination exists,
restore refuses; move it aside intentionally before retrying.

By default, entries live at `$HOME/.local/state/codex-recovery`. Override with
`CODEX_RECOVERY_STORE` or `--store /absolute/dedicated/directory` before the
subcommand. The store must be private (mode 700), owned by you, and have no
symlink directory components. Paths are recorded locally in metadata.

## Retention and limits

**Entries remain until you remove them yourself. There is no automatic
expiry, size pruning, cleanup command, or scheduled job.** Each input is
limited to 512 MiB logical size; sparse files count at their logical size.
Monitor disk space. After verifying a restore or an independent backup, you
may remove that specific entry directory manually. Do not delete the store
while another invocation is running. Uninstalling the executable keeps entries.

Final symlinks and links inside directories are preserved without following
their targets. Broad system/home roots, the store, its descendants and its
ancestors are refused. Changed symlink parents are refused on restore. Named
pipes, devices, sockets and other special files are unsupported. Commands use
an advisory lock to serialize cooperating invocations.

This is lightweight recovery, not a backup or security boundary against a
malicious process running as your user. Do not mutate sources, destination
directories, or store contents during an operation. Multi-item commands are
preflighted but are not one transaction: a later I/O failure can leave earlier
items archived. An interrupted operation can leave a `.pending-*` entry;
inspect its metadata and payload manually rather than deleting it. Restore
copy failure may leave an incomplete destination; the entry stays available.
Filesystem metadata preservation is best effort through Python's copy APIs;
resource forks, ACLs, hard-link relationships and all extended metadata are
not guaranteed. Test representative files and keep an independent backup.

## Uninstall

Remove only the executable you installed (`$HOME/.local/bin/codex-recovery`
in the example above). Keep your recovery store until you have reviewed and
recovered every needed entry. No service or startup item is installed.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests create isolated temporary homes and stores. They never access an
existing recovery store, snapshots, system Trash or user documents.

MIT licensed. Contributions should include isolated tests for filesystem
safety and describe platform-specific metadata limitations.
