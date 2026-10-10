"""Delete uninstall artifacts only after their invoking Windows shell exits.

The worker runs on the base interpreter, outside the environment being removed.
An inherited process handle (not a PID polled later) prevents PID reuse races.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


# Kept self-contained: the installation containing this module may be removed.
_WORKER = r'''
import ctypes, json, os, pathlib, shutil, sys, time
from ctypes import wintypes
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
handle = int(sys.argv[1])
result = kernel.WaitForSingleObject(handle, 0xffffffff)
kernel.CloseHandle(handle)
if result != 0:
    raise OSError("cleanup could not wait for invoking process")
# An interactive shell may outlive a reinstall, or uninstall may have failed
# before deleting its marker. Never remove artifacts owned by that install.
if os.path.lexists(sys.argv[3]):
    print("Cleanup skipped: installation marker exists", flush=True)
    print("Cleanup finished", flush=True)
    sys.exit(0)
for raw in json.loads(sys.argv[2]):
    path = pathlib.Path(raw)
    for attempt in range(50):
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.exists():
                shutil.rmtree(path)
            break
        except OSError as exc:
            if attempt == 49:
                print(f"Retained: {path}: {exc}", flush=True)
            else:
                time.sleep(0.1)
print("Cleanup finished", flush=True)
'''


def _wait_handle():
    """Find cmd.exe past venv redirectors; otherwise wait for this Python."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class Entry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entries = {}
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            entries[entry.th32ProcessID] = (entry.th32ParentProcessID, entry.szExeFile.lower())
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    pid = os.getpid()
    target = pid
    # Only cross the one venv redirector, never a Python caller (e.g. pytest).
    parent = entries.get(pid, (0, ""))[0]
    if sys.prefix != sys.base_prefix and entries.get(parent, (0, ""))[1] in ("python.exe", "pythonw.exe"):
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        process = kernel.OpenProcess(0x1000, False, parent)
        if process:
            try:
                name = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(name))
                if (kernel.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(size))
                        and Path(name.value).resolve() == Path(sys.executable).resolve()):
                    target = parent
                    parent = entries.get(parent, (0, ""))[0]
            finally:
                kernel.CloseHandle(process)
    if entries.get(parent, (0, ""))[1] == "cmd.exe":
        target = parent
    handle = kernel.OpenProcess(0x00100000, True, target)  # SYNCHRONIZE, inheritable
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return kernel, handle


def defer_cleanup(paths: list[Path], marker: Path) -> None:
    """Schedule exact uninstall targets; report durable diagnostics to the user."""
    python = Path(sys._base_executable).resolve()
    targets = [path.absolute() for path in paths]
    if any(python == path.resolve() or path.resolve() in python.parents for path in targets):
        raise RuntimeError("cannot run Windows cleanup from an interpreter being removed")
    kernel, handle = _wait_handle()
    try:
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": [handle]}
        fd, log = tempfile.mkstemp(prefix="scripts-uninstall-", suffix=".log")
        with os.fdopen(fd, "wb") as output:
            subprocess.Popen(
                [str(python), "-I", "-c", _WORKER, str(handle),
                 json.dumps([str(path) for path in targets]), str(marker.absolute())],
                stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                startupinfo=startup, close_fds=True, cwd=tempfile.gettempdir(),
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
    finally:
        kernel.CloseHandle(handle)
    print("Cleanup scheduled after the invoking command shell exits (close it if interactive).")
    print(f"Cleanup log: {log}")
    for path in targets:
        quoted = str(path).replace("'", "''")
        print(f"  Pending: {path}")
        print(f"  If cleanup fails: Remove-Item -LiteralPath '{quoted}' -Recurse -Force")
