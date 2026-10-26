import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "codex-recovery"


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.store = self.home / "recovery"
        self.env = {**os.environ, "HOME": str(self.home), "CODEX_RECOVERY_STORE": str(self.store)}

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, ok=True):
        result = subprocess.run([str(CLI), *map(str, args)], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result.stdout.strip()

    def file(self, name="sample.txt", text="original"):
        item = self.home / name
        item.write_text(text)
        return item

    def test_stash_restore_and_overwrite_refusal(self):
        item = self.file()
        entry = self.run_cli("stash", item)
        self.assertEqual(item.read_text(), "original")
        self.run_cli("restore", entry, ok=False)
        item.unlink()
        self.run_cli("restore", entry)
        self.assertEqual(item.read_text(), "original")
        self.assertTrue((self.store / "items" / entry / "payload").exists())

    def test_trash_roundtrip_directory_and_permissions(self):
        folder = self.home / "folder"
        folder.mkdir()
        (folder / "nested").write_text("content")
        (folder / "nested").chmod(0o640)
        entry = self.run_cli("trash", folder)
        self.assertFalse(folder.exists())
        self.run_cli("restore", entry)
        self.assertEqual((folder / "nested").read_text(), "content")
        self.assertEqual((folder / "nested").stat().st_mode & 0o777, 0o640)

    def test_broken_symlink_preserved(self):
        link = self.home / "link"
        link.symlink_to("does-not-exist")
        entry = self.run_cli("trash", link)
        self.run_cli("restore", entry)
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "does-not-exist")

    def test_directory_symlink_not_followed(self):
        target = self.file()
        folder = self.home / "folder"
        folder.mkdir()
        (folder / "external").symlink_to(target)
        entry = self.run_cli("stash", folder)
        self.assertTrue((self.store / "items" / entry / "payload/external").is_symlink())
        self.assertEqual(target.read_text(), "original")

    def test_protected_roots_store_and_ancestors_refused(self):
        for path in ("/", self.home, self.store, self.root):
            self.run_cli("trash", path, ok=False)
        alias = self.home / "alias"
        alias.symlink_to(self.home, target_is_directory=True)
        self.run_cli("trash", alias / "../home", ok=False)

    def test_restore_retargeted_parent_refused(self):
        folder = self.home / "original"
        folder.mkdir()
        item = folder / "item"
        item.write_text("data")
        entry = self.run_cli("trash", item)
        folder.rmdir()
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir()
        folder.symlink_to(elsewhere, target_is_directory=True)
        self.run_cli("restore", entry, ok=False)
        self.assertFalse((elsewhere / "item").exists())

    def test_tampered_metadata_and_id_refused(self):
        entry = self.run_cli("stash", self.file())
        metadata = self.store / "items" / entry / "metadata.json"
        record = json.loads(metadata.read_text())
        for destination in (str(self.home), "/", "relative", str(self.store / "unsafe")):
            record["original_path"] = destination
            metadata.write_text(json.dumps(record))
            self.run_cli("restore", entry, ok=False)
        self.run_cli("restore", "../outside", ok=False)

    def test_list_json_unicode_newlines(self):
        item = self.file("spaces ü\nname")
        entry = self.run_cli("stash", item)
        row = json.loads(self.run_cli("list"))
        self.assertEqual(row["id"], entry)
        self.assertEqual(row["original_path"], str(item))

    def test_symlinked_store_refused(self):
        actual = self.home / "actual"
        actual.mkdir()
        self.store.symlink_to(actual, target_is_directory=True)
        self.run_cli("stash", self.file(), ok=False)
        self.assertEqual(list(actual.iterdir()), [])

    def test_oversize_and_overlapping_inputs_refused(self):
        large = self.home / "sparse"
        with large.open("wb") as handle:
            handle.truncate(513 * 1024 * 1024)
        self.run_cli("trash", large, ok=False)
        self.assertTrue(large.exists())
        folder = self.home / "folder"
        folder.mkdir()
        child = folder / "child"
        child.write_text("data")
        self.run_cli("trash", folder, child, ok=False)
        self.assertTrue(child.exists())

    def test_special_file_refused(self):
        pipe = self.home / "pipe"
        os.mkfifo(pipe)
        self.run_cli("stash", pipe, ok=False)

    def test_entry_and_metadata_symlinks_refused(self):
        entry = self.run_cli("stash", self.file())
        metadata = self.store / "items" / entry / "metadata.json"
        metadata.unlink()
        metadata.symlink_to(self.file("other", "{}"))
        self.run_cli("restore", entry, ok=False)


if __name__ == "__main__":
    unittest.main()
