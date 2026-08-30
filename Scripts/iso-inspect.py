#!/usr/bin/env python3
# =============================================================================
#  iso-inspect.py — validador estrutural de ISO estilo "scanner do Rufus".
#
#  Reproduz os checks que o Rufus faz ao analisar uma ISO (ver "ISO analysis"
#  no log do Rufus) e verifica a estrutura de boot do Pineapple OS:
#    * El Torito: catálogo com entrada de boot BIOS (0x88) e entrada EFI (0xEF)
#      + validation entry com marcador 0xaa55;
#    * MBR híbrido: assinatura 0x55aa e partição protetora GPT (0xEE);
#    * Nenhum arquivo >= 4GiB (gatilho do aviso de cluster 64 KB do Rufus);
#    * Nenhum nome de arquivo não-ISO com mais de 64 caracteres (aviso do Rufus);
#    * Arquivos obrigatórios: /live/vmlinuz-*, /live/initrd.img-*, *.squashfs,
#      /boot/grub/grub.cfg (com busca por /live/vmlinuz + linux/initrd);
#    * Conteúdo EFI presente (BOOTX64.EFI dentro da imagem FAT embutida).
#
#  Saída resumida (estilo Rufus) e exit code:
#    0 = todas as verificações passaram; 1 = alguma falhou.
# =============================================================================

import struct
import sys
import mmap


def err(msg):
    print(f"  ERRO: {msg}")
    sys.exit(1)


def warn(msg):
    print(f"  aviso: {msg}")


def le32(b, off):
    return struct.unpack_from("<I", b, off)[0]


class SectorReader:
    def __init__(self, data):
        self.data = data
        self.sector_size = 2048
        self.title = ""

    def read(self, lba, size):
        off = lba * self.sector_size
        if off + size > len(self.data):
            raise IndexError(f"leitura fora da ISO em LBA {lba}")
        return self.data[off:off + size]

    def read_sector(self, lba):
        return self.read(lba, self.sector_size)


def parse_dir_record(dr):
    """Retorna dict basic de um directory record ISO9660."""
    if len(dr) < 33 or dr[0] == 0:
        return None
    rec_len = dr[0]
    if rec_len < 33 or rec_len > len(dr):
        return None
    ext_lba = le32(dr, 2)
    size = le32(dr, 10)
    flags = dr[25]
    name_len = dr[32]
    name = dr[33:33 + name_len]
    return {
        "len": rec_len,
        "lba": ext_lba,
        "size": size,
        "flags": flags,
        "name": name,
        "raw": dr[:rec_len],
    }


def rr_names(rec, reader):
    """Extrai o nome Rock Ridge (campos NM, com CONTINUE e CE)."""
    raw = rec["raw"]
    name_bytes = bytearray()
    # início da área de sistema: após nome (byte 33+name_len) + pad p/ par
    name_len = rec["name_len"] if "name_len" in rec else len(rec["name"])
    pos = 33 + name_len
    if pos % 2:
        pos += 1
    while pos + 4 <= len(raw):
        sig = raw[pos:pos + 2]
        ln = raw[pos + 2]
        ver = raw[pos + 3]
        if ln < 4 or sig == b"ST" or (sig[0] == 0 and sig[1] == 0):
            break
        body = raw[pos + 4:pos + ln]
        if sig == b"NM":
            flags = body[0]
            name_bytes += body[1:]
            if not (flags & 0x02):  # 0x02 = CONTINUE (nome continua)
                break
        elif sig == b"CE":
            # continuação em outro LBA (raro; genisoimage usa para NM longo)
            clba = le32(body, 0)
            csize = le32(body, 8)
            try:
                cont = reader.read(clba, csize)
                name_bytes += cont
            except IndexError:
                warn("CE de continuação fora da ISO; ignorando long name")
            break
        pos += ln
    if name_bytes:
        return name_bytes.decode("utf-8", "replace").rstrip("\x00")
    # fallback: nome ISO9660 (com ;1)
    n = rec["name"].decode("latin1", "replace").rstrip("\x00")
    return n


def main():
    if len(sys.argv) != 2:
        sys.exit("uso: iso-inspect.py <imagem.iso>")
    path = sys.argv[1]

    with open(path, "rb") as f:
        data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    print(f"==> Validação estrutural (estilo Rufus): {path}")
    print(f"    tamanho: {len(data)} bytes ({len(data)/1024**3:.2f} GiB)")

    total_sectors = len(data) // 2048
    reader = SectorReader(data)

    # ------------------------------------------------------------ PVD + label
    pvd = reader.read_sector(16)
    if pvd[0] != 1:
        err("PVD (volume descriptor 1) não encontrado no LBA 16")
    label = pvd[40:72].decode("utf-8", "replace").rstrip("\x20").rstrip("\x00")
    print(f"    label: '{label}'")
    root_rec = parse_dir_record(pvd[156:156 + 34])
    if root_rec is None:
        err("directório raiz inválido no PVD")

    # ------------------------------------------------------------ El Torito
    eltorito = None
    for lba in range(16, 48):
        vd = reader.read_sector(lba)
        st = vd[7:39].rstrip(b" \x00")
        if vd[0] == 0 and st == b"EL TORITO SPECIFICATION":
            eltorito = le32(vd, 71)
            break
        if vd[0] == 255:
            break
    if eltorito is None:
        err("El Torito: boot record ausente (ISO não bootável via BIOS)")
    cat = reader.read(eltorito, 512)
    if cat[0] != 0x01 or struct.unpack("<H", cat[30:32])[0] != 0xAA55:
        err("El Torito: validation entry inválida (marcador != aa55)")
    bios_ok = False
    efi_ok = False
    efi_rba = 0
    off = 32
    for _ in range(8):
        ind = cat[off]
        typ = cat[off + 1]
        nsec = struct.unpack("<H", cat[off + 6:off + 8])[0]
        img_lba = le32(cat, off + 8)
        if ind == 0x88:
            bios_ok = True
            print(f"    El Torito BIOS: entry 0x88 img_lba={img_lba} sectors={nsec}")
        elif ind == 0x91 and (typ == 0xEF or img_lba or nsec):
            efi_ok = True
            efi_rba = img_lba
            print(f"    El Torito EFI : entry 0x91/0xEF img_lba={img_lba} sectors={nsec}")
        elif ind == 0x00:
            break
        off += 32
    if not bios_ok:
        err("El Torito: entrada de boot BIOS (0x88) ausente")
    if not efi_ok:
        warn("El Torito: sem entry de marcador EFI (0x91/0xEF) no catálogo")
    elif efi_rba == 0:
        warn("El Torito: entry EFI sem RBA no catálogo (OVMF resolve via árvore do ISO)")

    # ------------------------------------------------------------ MBR híbrido
    mbr = reader.read(0, 512)
    hybrid = mbr[510] == 0x55 and mbr[511] == 0xAA
    protective = False
    for i in range(4):
        if mbr[446 + i * 16 + 4] == 0xEE:
            protective = True
    if not hybrid:
        err("MBR: sem assinatura 0x55aa (não é ISO híbrida)")
    if not protective:
        warn("MBR híbrido sem partição protetora GPT (0xEE)")
    print(f"    MBR híbrido: {'OK (0x55aa)' if hybrid else 'FALHOU'} "
          f"{'com partição protetora GPT' if protective else ''}")

    # ------------------------------------------------------------ árvore
    required = {
        "live_vmlinuz": None,
        "live_initrd": None,
        "live_squashfs": None,
        "grub_cfg": None,
    }
    files = []
    max_size = 0
    max_name = 0
    max_name_path = ""
    dirs_scan = [(root_rec, "/")]
    visited_dirs = {(root_rec["lba"], root_rec["size"])}

    def walk(rec, prefix):
        nonlocal max_size, max_name, max_name_path
        is_dir = bool(rec["flags"] & 0x02)
        base_name = rr_names(rec, reader).rstrip(";1").rstrip("\x00")
        if not base_name or base_name in (".", ".."):
            return
        path = prefix + base_name
        if is_dir:
            if (rec["lba"], rec["size"]) not in visited_dirs:
                visited_dirs.add((rec["lba"], rec["size"]))
                dirs_scan.append((rec, path + "/"))
            return
        files.append((path, rec["size"]))
        if rec["size"] > max_size:
            max_size = rec["size"]
        if len(path) > max_name:
            max_name = len(path)
            max_name_path = path
        # confere requisitos
        if path.startswith("/live/"):
            if "vmlinuz" in base_name and required["live_vmlinuz"] is None:
                required["live_vmlinuz"] = path
            if "initrd" in base_name and required["live_initrd"] is None:
                required["live_initrd"] = path
            if base_name.endswith(".squashfs") and \
                    required["live_squashfs"] is None:
                required["live_squashfs"] = path
        if path == "/boot/grub/grub.cfg":
            required["grub_cfg"] = path

    while dirs_scan:
        rec, prefix = dirs_scan.pop()
        try:
            dirdata = reader.read(rec["lba"], rec["size"])
        except IndexError:
            err(f"directório {prefix} fora da ISO")
        pos = 0
        while pos < len(dirdata):
            dr = parse_dir_record(dirdata[pos:pos + 300])
            if dr is None:
                pos += 1
                continue
            dr["name_len"] = len(dr["name"])
            walk(dr, prefix)
            pos += dr["len"]

    missing = [k for k, v in required.items() if v is None]
    if missing:
        err(f"arquivos obrigatórios ausentes: {missing}")

    print(f"    arquivos: {len(files)} | maior arquivo: {max_size} bytes")
    p4gb = 4 * 1024 * 1024 * 1024
    if max_size >= p4gb:
        err(f"arquivo >= 4GiB encontrado ({max_size} bytes) — o Rufus exigirá "
            "FAT32 de cluster 64 KB em modo ISO")
    print("    >4GB file: No")
    if max_name > 64:
        warn(f"nome com {max_name} caracteres: {max_name_path} (Rufus avisa)")
    print(f"    vmlinuz : {required['live_vmlinuz']}")
    print(f"    initrd  : {required['live_initrd']}")
    print(f"    squashfs: {required['live_squashfs']}")
    print(f"    grub.cfg: {required['grub_cfg']}")

    # ------------------------------------------------------------ grub.cfg
    # localiza o grub.cfg nos arquivos/modes e lê seu conteúdo
    g = required["grub_cfg"]
    # re-achata para obter lba/size do grub.cfg (caminho /boot/grub/grub.cfg)
    # walk direto: percorrer novamente seria caro; usar cache de arquivos
    # (desnecessário: faremos segunda varredura barata? não — reutilizamos files
    # mas sem lba; então varremos o directório /boot/grub de novo, garantindo
    # tamanho pequeno). Para simplicidade: aceitamos a presença e validamos o
    # conteúdo via varredura direta do caminho boot/grub.
    grub_cfg_content = None
    scan = [(root_rec, "")]
    scan_vis = {(root_rec["lba"], root_rec["size"])}
    while scan:
        rec, prefix = scan.pop()
        if not (rec["flags"] & 0x02):
            continue
        dirdata = reader.read(rec["lba"], rec["size"])
        pos = 0
        while pos < len(dirdata):
            dr = parse_dir_record(dirdata[pos:pos + 300])
            if dr is None:
                pos += 1
                continue
            nm = rr_names(dr, reader).rstrip(";1").rstrip("\x00")
            if not nm or nm in (".", "..", "\x00", "\x01"):
                pos += dr["len"]
                continue
            sub = prefix + "/" + nm
            if dr["flags"] & 0x02:
                if (dr["lba"], dr["size"]) not in scan_vis:
                    scan_vis.add((dr["lba"], dr["size"]))
                    scan.append((dr, sub))
            elif sub == "/boot/grub/grub.cfg":
                grub_cfg_content = reader.read(dr["lba"], dr["size"])
            pos += dr["len"]
    if grub_cfg_content:
        text = grub_cfg_content.decode("utf-8", "replace")
        ok_s = "search" in text and "--set=root" in text
        ok_l = "linux /live/" in text
        ok_i = "initrd /live/" in text
        ok_m = "menuentry" in text
        if not (ok_s and ok_l and ok_i and ok_m):
            err("grub.cfg sem busca/menuentry/linux/initrd esperados (ver /boot/grub/grub.cfg)")
        print("    grub.cfg: OK (search + menuentry + linux/initrd /live/*)")
    else:
        err("grub.cfg presente mas não lido")

    # ------------------------------------------------------------ EFI content
    efi_in_tree = [p for p, _ in files if p.lower().startswith("/efi/")]
    if efi_in_tree:
        print("    EFI files visíveis na árvore do ISO: "
              f"{' '.join(efi_in_tree[:3])}{' ...' if len(efi_in_tree) > 3 else ''}")
    else:
        print("    EFI files visíveis na árvore: nenhum (apenas na imagem FAT embutida)")
    has_efi = data.find(b"BOOTX64.EFI") != -1
    if not has_efi:
        err("conteúdo EFI (BOOTX64.EFI na imagem FAT embutida) não encontrado")
    print("    EFI bootloader (BOOTX64.EFI): presente")

    # ------------------------------------------------------------ MBR híbrido (Rufus)
    # Rufus em modo ISO grava o MBR híbrido: assinatura 0x55AA + partição 1
    # ATIVA (0x80) apontando para o próprio ISO. Sem isso o Rufus/Nero/pendrive
    # não enxerga a mídia como bootável.
    # crush: a checagem do MBR acima (linha ~179) já garante híbrido; aqui só
    # REPORTAMOS a partição ativa do ponto de vista do Rufus (reusa reader, não
    # o mmap, para manter estado consistente).
    mbr = reader.read(0, 512)
    boot_ind = mbr[446]
    part_type = mbr[450]
    if boot_ind != 0x80:
        warn("partição 1 do MBR híbrido sem flag ATIVA (0x80) — Rufus pode ignorá-la")
    ok_types = {0x00, 0x17, 0xEF, 0xEE, 0x0B, 0x0C, 0x83}
    if part_type not in ok_types:
        warn(f"tipo inesperado da partição 1 do MBR híbrido: 0x{part_type:02X}")
    print(f"    MBR híbrido: partição1 tipo 0x{part_type:02X}, boot flag 0x{boot_ind:02X}")

    print("\n==> VALIDAÇÃO OK: a ISO é híbrida (BIOS+UEFI), sem arquivos >= 4GiB,")
    print("    com grub.cfg resolvido por busca — apta para Rufus em modo ISO.")
    sys.exit(0)


if __name__ == "__main__":
    main()