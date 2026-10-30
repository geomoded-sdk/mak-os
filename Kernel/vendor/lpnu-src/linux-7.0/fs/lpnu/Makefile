obj-m = lpnu.o
lpnu-objs = lpnu_main.o lpnu_mach_o.o lpnu_vfs_compat.o lpnu_kext.o

ccflags-y += -I$(src)

KBUILD_EXTMOD = $(src)
KERNELRELEASE ?= $(shell uname -r)
KERNEL_DIR ?= /lib/modules/$(KERNAME-RELEASE)/build
PWD := $(shell pwd)

default:
	make -C $(KERNEL_DIR) M=$(PWD) modules

modules:
	make -C $(KERNEL_DIR) M=$(PWD) modules

clean:
	make -C $(KERNEL_DIR) M=$(PWD) clean