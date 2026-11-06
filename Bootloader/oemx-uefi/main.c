/* OEM-X experimental UEFI loader.
 *
 * This is intentionally small: firmware loads this application, it prints a
 * diagnostic banner, loads the EFI-stub kernel from the ISO and transfers
 * control to it with an explicit, visible command line.  No GRUB code is
 * involved in the UEFI path.
 */
#include <efi.h>
#include <efilib.h>

/* The UEFI El Torito image is a separate FAT filesystem.  Keep the kernel,
 * initramfs and arguments in that filesystem: a firmware-loaded app cannot
 * resolve /live from the ISO9660 filesystem through its DeviceHandle. */
static CHAR16 kernel_path[] = L"\\OEMX\\oem-x.ekern";
static CHAR16 args_path[] = L"\\OEMX\\bootargs.txt";
static CHAR16 load_options[2048];
static CHAR16 fallback_options[] =
    L"boot=live components console=ttyS0,115200 console=tty0 "
    L"loglevel=7 rd.debug initrd=\\OEMX\\pineapple.boot";

static VOID print_line(CHAR16 *text)
{
    uefi_call_wrapper(ST->ConOut->OutputString, 2, ST->ConOut, text);
}

/* bootargs.txt is deliberately ASCII.  It is produced alongside the FAT
 * image, keeping per-build PowerBook policy out of the loader binary. */
static VOID load_boot_options(EFI_HANDLE device)
{
    EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *fs = NULL;
    EFI_FILE_HANDLE root = NULL, file = NULL;
    CHAR8 raw[sizeof(load_options) / sizeof(CHAR16)];
    UINTN size = sizeof(raw) - 1;
    UINTN i, out = 0;
    EFI_STATUS status;

    status = uefi_call_wrapper(BS->HandleProtocol, 3, device,
                               &FileSystemProtocol, (VOID **)&fs);
    if (!EFI_ERROR(status))
        status = uefi_call_wrapper(fs->OpenVolume, 2, fs, &root);
    if (!EFI_ERROR(status))
        status = uefi_call_wrapper(root->Open, 5, root, &file, args_path,
                                   EFI_FILE_MODE_READ, 0);
    if (!EFI_ERROR(status))
        status = uefi_call_wrapper(file->Read, 3, file, &size, raw);

    if (!EFI_ERROR(status) && size) {
        for (i = 0; i < size && out + 1 < sizeof(load_options) / sizeof(CHAR16); i++) {
            CHAR8 c = raw[i];
            if (c == '\r' || c == '\n' || c == '\t')
                c = ' ';
            if (c >= 0x20 && c <= 0x7e)
                load_options[out++] = (CHAR16)c;
        }
        while (out && load_options[out - 1] == L' ')
            out--;
        load_options[out] = L'\0';
    }
    if (!out)
        StrCpy(load_options, fallback_options);

    if (file)
        uefi_call_wrapper(file->Close, 1, file);
    if (root)
        uefi_call_wrapper(root->Close, 1, root);
}

EFI_STATUS EFIAPI efi_main(EFI_HANDLE image, EFI_SYSTEM_TABLE *system_table)
{
    EFI_LOADED_IMAGE *self;
    EFI_DEVICE_PATH *path;
    EFI_HANDLE kernel = NULL;
    EFI_STATUS status;
    UINTN option_bytes;

    InitializeLib(image, system_table);
    print_line(L"OEM-X bootloader (experimental UEFI)\r\n");
    print_line(L"OEM-X: loading \\OEMX\\oem-x.ekern\r\n");

    status = uefi_call_wrapper(BS->HandleProtocol, 3, image,
                               &LoadedImageProtocol, (VOID **)&self);
    if (EFI_ERROR(status)) {
        print_line(L"OEM-X: cannot get loader device\r\n");
        return status;
    }

    load_boot_options(self->DeviceHandle);
    option_bytes = (StrLen(load_options) + 1) * sizeof(CHAR16);

    path = FileDevicePath(self->DeviceHandle, kernel_path);
    if (!path) {
        print_line(L"OEM-X: cannot create kernel path\r\n");
        return EFI_OUT_OF_RESOURCES;
    }

    status = uefi_call_wrapper(BS->LoadImage, 6, FALSE, image, path,
                               NULL, 0, &kernel);
    FreePool(path);
    if (EFI_ERROR(status)) {
        print_line(L"OEM-X: kernel not found or not an EFI image\r\n");
        return status;
    }

    status = uefi_call_wrapper(BS->HandleProtocol, 3, kernel,
                               &LoadedImageProtocol, (VOID **)&self);
    if (EFI_ERROR(status)) {
        print_line(L"OEM-X: cannot configure kernel image\r\n");
        return status;
    }
    self->LoadOptions = load_options;
    self->LoadOptionsSize = option_bytes;

    print_line(L"OEM-X: starting kernel (serial + console diagnostics enabled)\r\n");
    status = uefi_call_wrapper(BS->StartImage, 3, kernel, NULL, NULL);
    if (EFI_ERROR(status))
        print_line(L"OEM-X: kernel returned an error\r\n");
    return status;
}
