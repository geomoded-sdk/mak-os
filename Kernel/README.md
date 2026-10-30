# Kernel do Pineapple OS

> Leia este documento primeiro — ele explica **o que é o kernel**, **como o
> boot funciona** (com o PowerBook ID e o kernel panic) e **como compilar**.

## O que é este "kernel"?

O Pineapple OS usa uma arvore local do kernel **Linux 6.1**, compilada com uma
configuracao propria (`config-6.1-pineappleos`) e com codigo Pineapple integrado
em `Kernel/pineapple/`. A identidade
de plataforma é **Pineapple Kernel** — do mesmo jeito que o Android chama seu
kernel de "Android Kernel" mesmo sendo Linux por baixo.

Um detalhe importante, de forma honesta: **não é possível ter um kernel "não
Linux baseado em Linux"**. O kernel que roda no hardware É o Linux — o que dá
para fazer (e fazemos) é rebrandar, esconder a marca e adicionar comportamento
próprio (como o bloqueio por PowerBook ID). Um kernel verdadeiramente novo
(estilo XNU do macOS) seria um projeto de anos, fora do escopo de um repo.

## Arquivos

| Arquivo                    | Descrição                                            |
|----------------------------|------------------------------------------------------|
| `config-6.1-pineappleos`   | Configuração de referência do kernel (x86_64)        |
| `pineapple/`               | Código real integrado em `drivers/pineapple/`        |
| `pineapple/bsd/`           | Camada FreeBSD (sysctl estilo BSD, híbrido XNU)      |
| `pineapple/bootargs/`      | Boot-args no kernel (PowerBook ID + PNFS)            |
| `pineapple/hwcheck/`       | Allowlist de hardware por build (panic se fora)      |
| `pineapple/pnfs/`          | PNFS — filesystem de kernel (mount -t pnfs)          |
| `hwlist.txt`               | Hardware autorizado NESTA build (GPU, wifi, …)       |
| `vendor/linux-6.1.tar.xz`  | Fonte Linux 6.1 local, sem download no build        |
| `build/`                   | Diretório de build (gerado, fora do git)             |
| `../Scripts/build-kernel.sh` | Compila o kernel + módulos + initramfs             |

## Hardware por build (allowlist)

O build embute `Kernel/hwlist.txt` em **allowlist de hardware** (`allowed_hw.h`).
No boot, qualquer placa **display** (GPU) ou **rede** (wifi/ethernet) cujo
PCI `vendor:device` **não** esteja na lista causa **kernel panic** estilo
macOS. **Cada build aceita só o hardware escolhido na hora de compilar:**

```bash
# Antes de compilar, edite Kernel/hwlist.txt (use lspci -nn):
#   8086:9a49:03    Intel UHD (GPU)
#   8086:2723:02    Intel Wi-Fi AX200
./Scripts/build-kernel.sh
```

Lista vazia = sem restrição PCI (só o PowerBook ID vale).

## Identidade e "esconder a marca"

O build **modifica o fonte Linux** (`include/linux/uts.h` etc.): `uname -s`
retorna `Pineapple` e `/proc/version` começa com `Pineapple version …`.
O artefato do kernel **não se chama `vmlinuz`** — é **`pineapple.ekern`**
(o initramfs live é `pineapple.boot`).

| Onde                          | Como o Pineapple OS aparece                          |
|-------------------------------|------------------------------------------------------|
| `uname -s` / `uname -r`       | `Pineapple` / `6.1.0-pineappleos`                    |
| Artefato do kernel            | `/boot/pineapple.ekern-<release>` (nunca vmlinuz)    |
| `/etc/os-release`             | `NAME="Pineapple OS"` (`Installer/os-release`)       |
| Tela de boot (Plymouth/GRUB)  | fundo lavanda #262426 + abacaxi, sem "GNU/Linux"     |
| Logs do kernel                | ocultos (`quiet loglevel=0`), como no macOS          |

## Boot — fluxo completo

```
BIOS/UEFI
   │
   ▼
GRUB ──► menu "Pineapple OS" (fundo lavanda escuro + abacaxi)
   │        argumentos: quiet loglevel=0 splash
   │                     -pineapplepowerbookid=<ID>   ← OBRIGATÓRIO
   │                     -pineapplefs=<dev>           ← OBRIGATÓRIO (fora do live)
   ▼
Kernel + initramfs
   │
   ├─► init-bottom/pineapple-powerbook-check
   │        │
   │        ├─► valida o -pineapplepowerbookid=<ID> contra ids.txt
   │        │     ID ausente/errado ──► KERNEL PANIC (estilo macOS)
   │        │
   │        └─► valida o volume PNFS (fora do modo live)
   │              monta o dispositivo, confere .bfsprivate/volume.info
   │              sem PNFS válido ──► KERNEL PANIC (estilo macOS)
   │
   ▼
Plymouth ──► abacaxi sobre fundo #262426 + barra de progresso
   │
   ▼
systemd ──► pineappleos-session.target (compositor + shell + dock...)
```

## Argumentos de boot (estilo macOS)

| Argumento                    | Efeito                                       |
|------------------------------|----------------------------------------------|
| `quiet loglevel=0`           | esconde os logs do kernel (boot limpo)       |
| `splash`                     | mostra o Plymouth (abacaxi + barra)          |
| `-pineapplepowerbookid=<ID>` | ID do PowerBook (ver `ids.txt` na raiz)      |
| `-pineapplefs=<dev>`         | dispositivo do volume PNFS (ex.: `/dev/sdb2`) |

> O prefixo `-` é proposital: imita os boot args do macOS
> (`-v`, `-x`, `-s`...). O kernel Linux ignora argumentos desconhecidos como
> estes, mas o nosso verificador no initramfs os lê de `/proc/cmdline`.

## PowerBook ID + kernel panic

O Pineapple OS **não inicia** sem um PowerBook ID válido. O mecanismo:

1. `ids.txt` (raiz do repo) — lista de IDs válidos.
2. Hook de initramfs (`Installer/initramfs/hooks/`) embute a lista dentro do
   initramfs em `pineappleos-ids.txt`.
3. Verificador (`Installer/initramfs/scripts/init-bottom/`) roda no estágio
   `init-bottom` (com `/proc` montado, antes do chroot no disco):
   - lê `/proc/cmdline` e extrai `-pineapplepowerbookid=<ID>`;
   - valida o ID contra `pineappleos-ids.txt`;
   - **se ausente ou inválido** → imprime a mensagem de panic estilo macOS
     no console e força um kernel panic real via SysRq
     (`echo c > /proc/sysrq-trigger`), parando o boot.
4. Para que o SysRq funcione, o kernel é compilado com
   `CONFIG_MAGIC_SYSRQ=y`.

### Como definir o seu ID no GRUB (instalação)

```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=0 -pineapplepowerbookid=SEU_ID"

sudo update-grub
```

Para a ISO, use a variável de ambiente no build:

```bash
POWERBOOK_ID=SEU_ID ./Scripts/build-iso.sh
```

> Se você rodar sem o argumento, o kernel entra em panic e o sistema
> não inicia — exatamente o comportamento de bloqueio pedido.

## Volume PNFS obrigatório (fora do modo live)

Assim como o macOS exige um volume APFS, o Pineapple OS **não inicia** sem um
volume PNFS nativo válido (`volume.info` com `magic: PNFS`). O mesmo
verificador do initramfs:

1. Se houver `boot=live` na linha de boot, o PNFS é dispensado (demo/live).
2. Se houver `-pineapplefs=<dev>`, o dispositivo é montado (ro) e validado.
   `-pineapplefs=root` valida o próprio sistema raiz.
3. Sem o argumento, lê `/etc/fstab` do sistema raiz e valida os volumes
   montados em `/home` ou `/data`.
4. Nada encontrado/inválido → **kernel panic** estilo macOS.

O kernel tem o driver PNFS embutido, então o initramfs monta o volume nativo
sem depender de filesystem externo ou `modprobe`.

### Como criar o volume PNFS (instalação)

```bash
sudo ./Scripts/setup-pnfs.sh /dev/sdb2          # formata PNFS nativo em /data
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=0 -pineapplepowerbookid=SEU_ID -pineapplefs=/dev/sdb2"
sudo update-grub
```

## LPNU v2.0.0 (integrado OBRIGATORIAMENTE na compilação)

O build do kernel compila, de forma **obrigatória**, a camada de compatibilidade
[LPNU v2.0.0](https://github.com/geomoded-sdk/lpnu/releases/tag/v2.0.0) **do
fonte contra o nosso kernel** — é o que permite rodar binários macOS no
Pineapple OS (os `.ko` pré-compilados do release são do `6.17.0-1011-azure` e
não carregariam num kernel custom por causa de vermagic/modversions):

| Componente | O que faz                                   | Onde é instalado                     |
|------------|---------------------------------------------|--------------------------------------|
| `lpnu.ko`  | kernel compatibility layer (binários macOS) | `/lib/modules/<ver>/extra/` + boot   |
| `apfs.ko`  | filesystem APFS (linux-apfs-rw v0.3.19)     | `/lib/modules/<ver>/extra/` + boot   |
| `ld-mac`   | Mach-O loader (binário do release, sha256)  | `/usr/local/bin/ld-mac`              |

O `Scripts/build-kernel.sh`:
1. baixa o **fonte** do LPNU v2.0.0 e do linux-apfs-rw v0.3.19 + o `ld-mac`;
2. verifica o **sha256** do `ld-mac` (falhou → aborta);
3. compila `lpnu.ko` e `apfs.ko` contra o nosso kernel (`make -C <kernel> M=...`);
4. confere o **vermagic** dos módulos — precisa ser exatamente
   `<release>-pineappleos`, senão o build é abortado;
5. instala em `/lib/modules/<release>/extra/`, roda `depmod` e ativa o
   carregamento automático via `/etc/modules-load.d/pineapple-lpnu.conf`;
6. instala `ld-mac` em `/usr/local/bin/`.

Na **ISO**, o mesmo fluxo roda dentro do live-build
(`Installer/live-build/hooks/pineapple-lpnu.hook.chroot`): o `build-iso.sh`
baixa as fontes no host e o hook compila contra os headers do kernel da ISO,
garantindo compatibilidade total.

## Otimizações incluídas no config

- `HZ_1000` + `PREEMPT` — latência mínima para UI fluida (desktop).
- `CONFIG_MAGIC_SYSRQ=y` — necessário para o kernel panic do PowerBook ID.
- `CONFIG_PINEAPPLE_PNFS=y` — PNFS nativo embutido no kernel.
- Suporte a GPUs AMD (amdgpu), NVIDIA (nouveau), Intel (i915).
- `FUSE_FS` — necessário para Flatpak e AppImage.
- `ANDROID_BINDER`/`OVERLAY_FS` — necessário para Waydroid.
- `APPARMOR` — segurança de pacotes e do Waydroid.

## Build

```bash
./Scripts/build-kernel.sh            # usa fonte local, integra e compila
make -C Kernel/build/linux-6.1 -j$(nproc) bzImage modules
```

O script nao baixa o Linux durante o build. Ele usa `Kernel/linux-6.1/` quando
essa arvore estiver extraida; caso contrario, extrai o arquivo local
`Kernel/vendor/linux-6.1.tar.xz` (ou as partes locais com sufixo
`.part-*`). Se nenhum dos dois existir, o build falha de forma explicita.

O componente `Kernel/pineapple/pineapple_core.c` e compilado dentro do kernel
e publica `/sys/kernel/pineapple/identity` e `/sys/kernel/pineapple/release`.
Isso e uma modificacao real do kernel, mantendo a ABI e a licenca GPL do Linux;
nao e apenas rebranding por configuracao.

Depois de instalar o kernel, **regere o initramfs** para embutir o
PowerBook ID check:

```bash
sudo /usr/share/initramfs-tools/hooks/  # já instalado por setup-boot-themes.sh
sudo update-initramfs -u
sudo update-grub
```

## Notas

- Para NVIDIA proprietária, desabilite `CONFIG_DRM_NOUVEAU` e instale o driver
  `nvidia-driver` + `nvidia-dkms`.
- Para reduzir RAM, desabilite módulos não utilizados (ex.:
  `CONFIG_DRM_AMDGPU` em máquinas Intel) e regenere o initramfs.
- O build do kernel é o único passo que exige uma máquina Linux (ou a CI);
  veja `.github/workflows/ci.yml` para o build da ISO x64.
