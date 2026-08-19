#!/usr/bin/env python3
"""Unified application detector and launcher for Pineapple OS."""
import argparse
import shutil
import stat
import subprocess
from pathlib import Path

MAGIC_MACHO = {
    b"\xfe\xed\xfa\xce": "macho32",
    b"\xce\xfa\xed\xfe": "macho32",
    b"\xfe\xed\xfa\xcf": "macho64",
    b"\xcf\xfa\xed\xfe": "macho64",
}


def detect(path):
    """Detect a format using file signatures, not only the filename."""
    path = Path(path)
    if path.suffix.lower() == ".appimage":
        return "appimage"
    if path.suffix.lower() in (".flatpak", ".flatpakref"):
        return "flatpak"
    try:
        with path.open("rb") as stream:
            header = stream.read(32)
    except OSError:
        return "unknown"
    if header.startswith(b"\x7fELF"):
        return "elf"
    if header.startswith(b"MZ"):
        return "pe"
    if header[:4] in MAGIC_MACHO:
        return "macho"
    return "unknown"


def runtime_available(kind):
    commands = {
        "elf": ("true",),
        "appimage": ("fuse-overlayfs", "fusermount", "fuse2fs"),
        "pe": ("wine",),
        "macho": ("darling",),
        "flatpak": ("flatpak",),
    }
    if kind in ("elf", "appimage"):
        return True
    return any(shutil.which(command) for command in commands.get(kind, ()))


def command_for(path, kind=None):
    path = str(Path(path).resolve())
    kind = kind or detect(path)
    if kind in ("elf", "appimage"):
        return [path]
    if kind == "pe":
        return ["wine", path]
    if kind == "macho":
        return ["darling", "exec", path]
    raise ValueError(f"unsupported application format: {kind}")


def desktop_entry(path, name=None, icon="application-x-executable"):
    path = Path(path).resolve()
    kind = detect(path)
    label = name or path.stem
    wrapper = Path(__file__).resolve()
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={label}",
        f"Exec={wrapper} launch {path}",
        f"Icon={icon}",
        "Terminal=false",
        f"X-Pineapple-Runtime={kind}",
        "Categories=Utility;",
        "",
    ])


def register(path, destination=None):
    path = Path(path).resolve()
    if detect(path) == "unknown":
        raise ValueError(f"cannot detect application format: {path}")
    destination = Path(destination or Path.home() / ".local/share/applications")
    destination.mkdir(parents=True, exist_ok=True)
    filename = "pineapple-" + "".join(c.lower() if c.isalnum() else "-" for c in path.stem) + ".desktop"
    target = destination / filename
    target.write_text(desktop_entry(path), encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    return target


def launch(path):
    kind = detect(path)
    if kind == "unknown":
        raise SystemExit(f"formato desconhecido: {path}")
    if not runtime_available(kind):
        raise SystemExit(f"runtime ausente para {kind}: instale a camada Pineapple correspondente")
    subprocess.run(command_for(path, kind), check=False)


def main():
    parser = argparse.ArgumentParser(prog="pineapple-app-wrapper")
    sub = parser.add_subparsers(dest="command", required=True)
    detect_parser = sub.add_parser("detect")
    detect_parser.add_argument("path")
    launch_parser = sub.add_parser("launch")
    launch_parser.add_argument("path")
    register_parser = sub.add_parser("register")
    register_parser.add_argument("path")
    register_parser.add_argument("--dir")
    args = parser.parse_args()
    if args.command == "detect":
        print(detect(args.path))
    elif args.command == "launch":
        launch(args.path)
    else:
        print(register(args.path, args.dir))


if __name__ == "__main__":
    main()
