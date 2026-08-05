# Kernel Mak OS

## Visão geral

O Mak OS usa o kernel Linux principal (upstream) com uma configuração otimizada
para desktop: baixa latência, preempção, e suporte amplo a GPUs para aceleração
da interface.

## Arquivos

| Arquivo                 | Descrição                                   |
|-------------------------|---------------------------------------------|
| `config-6.1-makos`      | Configuração de referência (x86_64)         |
| `build/`                | Diretório de build (gerado, fora do git)    |

## Build

```bash
./Scripts/build-kernel.sh
```

## Otimizações incluídas

- `HZ_1000` + `PREEMPT` — latência mínima para UI fluida.
- Suporte a GPUs AMD (amdgpu), NVIDIA (nouveau), Intel (i915).
- `FUSE_FS` — necessário para Flatpak e AppImage.
- `ANDROID_BINDER`/`OVERLAY_FS` — necessário para Waydroid.
- `APPARMOR` — segurança dos pacotes e do Waydroid.

## Notas

- Para NVIDIA proprietária, desabilite `CONFIG_DRM_NOUVEAU` e instale o driver
  `nvidia-driver` + `nvidia-dkms` no instalador.
- Para reduzir ainda mais o uso de RAM, desabilite módulos não utilizados
  (ex.: `CONFIG_DRM_AMDGPU` em máquinas Intel) e regenere o initramfs.
