/* OEM-X experimental UEFI loader.
 *
 * This is intentionally small: firmware loads this application, it prints a
 * diagnostic banner, loads the EFI-stub kernel from the ISO and transfers
 * control to it with an explicit, visible command line.  No GRUB code is
 * involved in the UEFI path.
 */
#include <efi.h>
#include <efilib.h>

static CHAR16 kernel_path[] = L"\\live\\oem-x.ekern";
static CHAR16 load_options[] =
    L"boot=live components console=ttyS0,115200 console=tty0 "
    L"loglevel=7 rd.debug initrd=\\live\\pineapple.boot";

static VOID print_line(CHAR16 *text)
{
    uefi_call_wrapper(ST->ConOut->OutputString, 2, ST->ConOut, text);
}

EFI_STATUS EFIAPI efi_main(EFI_HANDLE image, EFI_SYSTEM_TABLE *system_table)
{
    EFI_LOADED_IMAGE *self;
    EFI_DEVICE_PATH *path;
    EFI_HANDLE kernel = NULL;
    EFI_STATUS status;
    UINTN option_bytes = (StrLen(load_options) + 1) * sizeof(CHAR16);

    InitializeLib(image, system_table);
    print_line(L"OEM-X bootloader (experimental UEFI)\r\n");
    print_line(L"OEM-X: loading \\live\\oem-x.ekern\r\n");

    status = uefi_call_wrapper(BS->HandleProtocol, 3, image,
                               &LoadedImageProtocol, (VOID **)&self);
    if (EFI_ERROR(status)) {
        print_line(L"OEM-X: cannot get loader device\r\n");
        return status;
    }

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
