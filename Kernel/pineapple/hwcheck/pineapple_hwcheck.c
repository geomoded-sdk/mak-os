// SPDX-License-Identifier: GPL-2.0-only
/* Pineapple OS — hardware allowlist check (por build).
 *
 * A lista de hardware autorizado é embutida em tempo de compilação a partir
 * de Kernel/hwlist.txt (gerada por build-kernel.sh em allowed_hw.h).
 *
 * No boot, este módulo varre o barramento PCI: qualquer dispositivo cujo
 * vendor:device não esteja na allowlist desta build força KERNEL PANIC estilo
 * macOS — o sistema recusa iniciar em hardware não autorizado para aquela
 * build. A lista desta árvore foi gerada para o PC de desenvolvimento atual.
 *
 * A restrição vale SÓ para a build que embutiu a lista (cada build tem sua
 * allowlist própria).
 */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/panic.h>

/* Gerado no build a partir de Kernel/hwlist.txt — não versionar o .h gerado. */
#include "allowed_hw.h"

/* A ISO de produção usa o modo lock. O runner QEMU recebe observe no seu
 * grub.cfg temporário para testar o kernel e o initramfs sem fingir que o
 * hardware virtual pertence à máquina autorizada. */
static bool hwcheck_enforce = true;

static int __init pineapple_hwcheck_mode(char *value)
{
	if (value && (!strcmp(value, "observe") || !strcmp(value, "off")))
		hwcheck_enforce = false;
	return 0;
}
early_param("pineapple.hwcheck", pineapple_hwcheck_mode);

static const char *pci_class_name(unsigned int class)
{
	switch ((class >> 16) & 0xff) {
	case 0x02:
		return "rede";
	case 0x03:
		return "display";
	default:
		return "pci";
	}
}

/* Procura vendor:device (e opcionalmente classe) na allowlist. */
static bool hw_allowed(u16 vendor, u16 device, u8 class_code)
{
	unsigned int i;

	for (i = 0; i < pine_allowed_hw_count; i++) {
		const struct pine_allowed_hw *e = &pine_allowed_hw[i];

		if (e->vendor != vendor || e->device != device)
			continue;
		/* classe 0 na entrada = qualquer classe */
		if (e->class_code != 0 && e->class_code != class_code)
			continue;
		return true;
	}
	return false;
}

static int __init pineapple_hwcheck_init(void)
{
	struct pci_dev *pdev = NULL;
	u8 cls;

	if (!hwcheck_enforce) {
		pr_info("pineapple-hwcheck: modo observe (trava PCI suspensa para diagnóstico)\n");
		return 0;
	}

	/* Lista vazia = sem restrição de PCI (só PowerBook ID vale). */
	if (pine_allowed_hw_count == 0) {
		pr_info("pineapple-hwcheck: allowlist vazia — sem restrição PCI nesta build\n");
		return 0;
	}

	while ((pdev = pci_get_device(PCI_ANY_ID, PCI_ANY_ID, pdev)) != NULL) {
		cls = pdev->class >> 16;

		if (!hw_allowed(pdev->vendor, pdev->device, cls)) {
			panic("Pineapple OS: hardware não autorizado nesta build.\n\n"
			      "  Placa: %s %04x:%04x (classe %s)\n"
			      "  Esta build do OEM-X Kernel só aceita o hardware\n"
			      "  listado em hwlist.txt no momento da compilação.\n\n"
			      "  Você precisa reiniciar o computador.\n",
			      pci_name(pdev), pdev->vendor, pdev->device,
			      pci_class_name(cls));
		}
	}

	pr_info("pineapple-hwcheck: hardware PCI autorizado (%u entradas na allowlist)\n",
		pine_allowed_hw_count);
	return 0;
}

static void __exit pineapple_hwcheck_exit(void)
{
}

module_init(pineapple_hwcheck_init);
module_exit(pineapple_hwcheck_exit);

MODULE_DESCRIPTION("Pineapple OS hardware allowlist check (por build)");
MODULE_LICENSE("GPL");
