import hashlib
import io
import tempfile
import tarfile
import unittest
import zipfile
from pathlib import Path
from jroc_samsung.core import sha256_file, inspect_firmware, collect_diagnostics


class CoreTests(unittest.TestCase):
    def test_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "x.bin"
            path.write_bytes(b"test-data")
            self.assertEqual(sha256_file(path), hashlib.sha256(b"test-data").hexdigest())

    def test_zip_components(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "firmware.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("BL_MODEL.tar.md5", b"x")
                z.writestr("AP_MODEL.tar.md5", b"y")
                z.writestr("HOME_CSC_OXM.tar.md5", b"z")
            result = inspect_firmware(path)
            self.assertEqual(result["archive_type"], "zip")
            self.assertTrue(result["components"]["BL"])
            self.assertTrue(result["components"]["AP"])
            self.assertTrue(result["components"]["HOME_CSC"])
            self.assertFalse(result["authenticity_verified"])

    def test_tar_components(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "AP_MODEL.tar"
            data = b"firmware"
            info = tarfile.TarInfo("AP_MODEL.bin")
            info.size = len(data)
            with tarfile.open(path, "w") as archive:
                archive.addfile(info, io.BytesIO(data))
            self.assertTrue(inspect_firmware(path)["components"]["AP"])

    def test_diagnostics_are_read_only(self):
        result = collect_diagnostics()
        self.assertFalse(result["flash_write_supported"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
