# OEM-X vendored kernel sources

The OEM-X build is self-contained. The CI never downloads kernel source:

- `linux-6.1.tar.xz.part-*` is the official Linux source archive stored here;
- `freebsd-src/` contains selected FreeBSD source files used as BSD API and
  queue/sysctl references;
- `xnu/` contains selected XNU IPC/VM and BSD references.

The FreeBSD and XNU files are not linked directly into Linux. Their interfaces
and design are adapted in `Kernel/pineapple/compat/oemx_compat.c`, which is
compiled into the single OEM-X kernel. This keeps each upstream license and
copyright notice intact while avoiding incompatible kernel ABIs.

FreeBSD source: BSD-2-Clause. XNU source: Apple Public Source License 2.0.
Linux source and OEM-X kernel changes retain their respective GPL licensing.
