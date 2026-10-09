"""Network-enabled generated repository tool acceptance for the 3-OS CI job."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from scriptkit.contracts import ToolSpec, resource_text
from scriptkit.generator import apply, preview
from scriptkit.generator.scaffolds import tool

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="scripts-generated-") as temporary:
        root = Path(temporary).resolve()
        source = root / "tool café"
        source.mkdir()
        value = json.loads(resource_text("ToolSpec.example.json"))
        value.update(name="disposable-tool", entrypoint="disposable.cli:main")
        spec = ToolSpec.from_dict(value)
        apply(source, preview(source, tool(spec, "repository")))
        install = root / "install café"
        install.mkdir()
        shutil.copytree(ROOT / "requirements", install / "requirements")
        shutil.copy(ROOT / "scripts", install / "scripts")
        shutil.copytree(ROOT / "pokanop_manager", install / "pokanop_manager")
        bin_dir = root / "bin café"
        bin_dir.mkdir()
        unrelated = bin_dir / ("netsy.cmd" if os.name == "nt" else "netsy")
        unrelated.write_bytes(b"preserve unrelated wrapper")
        (install / ".scripts-install.json").write_text(json.dumps({"version": 1, "tools": ["netsy"]}))
        def cli(*args):
            subprocess.run([sys.executable, "-X", "utf8", str(install / "scripts"), *args,
                            "--dir", str(install), "--bin-dir", str(bin_dir)], cwd=root, check=True)
        cli("register", str(source))
        cli("install", "disposable-tool", "--no-pull", "--no-path")
        wrapper = bin_dir / ("disposable-tool.cmd" if os.name == "nt" else "disposable-tool")
        subprocess.run([str(wrapper), "--help"], cwd=root, check=True)
        subprocess.run([str(wrapper), "doctor"], cwd=root, check=True)
        host_wrapper = bin_dir / ("scripts.cmd" if os.name == "nt" else "scripts")
        subprocess.run([str(host_wrapper), "list"], cwd=root, check=True)
        cli("uninstall", "disposable-tool", "--keep-path")
        cli("unregister", "disposable-tool")
        assert not wrapper.exists()
        assert unrelated.read_bytes() == b"preserve unrelated wrapper"
        marker = json.loads((install / ".scripts-install.json").read_text())
        assert marker["tools"] == ["netsy"]
        assert (source / "tool.json").exists()
        assert not json.loads((install / ".scripts-catalog.json").read_text())
        print("Generated repository registration/install/doctor/removal passed; unrelated state retained")


if __name__ == "__main__":
    main()
