# OEM-X UEFI loader (experimental)

`BOOTX64.EFI` is the OEM-X UEFI entry point for experimental ISOs. Firmware
loads it directly from `EFI/BOOT`; it loads the EFI-stub OEM-X kernel from
`/live/oem-x.ekern` and passes a visible serial/console command line. This
path is deliberately independent of GRUB. BIOS boot remains a compatibility
fallback until the OEM-X BIOS stage-2 loader is complete.
