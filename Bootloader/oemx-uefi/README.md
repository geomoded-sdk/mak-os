# OEM-X UEFI loader (experimental)

`BOOTX64.EFI` is the OEM-X UEFI entry point for experimental ISOs. Firmware
loads it directly from `EFI/BOOT`.  The El Torito FAT volume also carries
`OEMX/oem-x.ekern`, `OEMX/pineapple.boot` and `OEMX/bootargs.txt`; loading all
three from the same firmware-visible filesystem avoids the old, invalid
attempt to resolve `/live` inside ISO9660. This path is independent of GRUB.
BIOS boot remains a compatibility fallback until the OEM-X BIOS stage-2
loader is complete.
