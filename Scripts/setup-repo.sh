#!/bin/bash
# =============================================================================
#  setup-repo.sh — cria repositório apt assinado do Mak OS a partir de dist/*.deb
#
#  Uso:
#    ./setup-repo.sh               # gera o repo em build/repo (local)
#    ./setup-repo.sh --install     # adiciona ao apt e instala os pacotes
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
REPO="$ROOT/build/repo"
CODENAME="${CODENAME:-makos}"

[ -n "$(ls -A "$DIST"/*.deb 2>/dev/null)" ] || {
  echo "nenhum .deb em dist/. Execute ./Scripts/build-debs.sh" >&2
  exit 1
}

echo "==> Preparando estrutura do repositório"
mkdir -p "$REPO/pool/main/m" "$REPO/dists/$CODENAME/main/binary-amd64"
cp "$DIST"/*.deb "$REPO/pool/main/m/"

echo "==> Gerando índices com apt-ftparchive"
cd "$REPO"
apt-ftparchive packages pool/ > "dists/$CODENAME/main/binary-amd64/Packages"
gzip -9fk "dists/$CODENAME/main/binary-amd64/Packages"

cat > apt.conf <<EOF
APT::FTPArchive::Release::Origin "Mak OS";
APT::FTPArchive::Release::Label "Mak OS Repository";
APT::FTPArchive::Release::Suite "stable";
APT::FTPArchive::Release::Codename "$CODENAME";
APT::FTPArchive::Release::Architectures "amd64";
APT::FTPArchive::Release::Components "main";
EOF

apt-ftparchive -c apt.conf release "dists/$CODENAME" > "dists/$CODENAME/Release"

# assinatura GPG (chave do projeto)
if [ ! -f "$ROOT/Installer/repo/makos-key.asc" ]; then
  mkdir -p "$ROOT/Installer/repo"
  gpg --batch --passphrase '' --quick-gen-key "Mak OS <dev@makos.example>" default default never
  gpg --export --armor "Mak OS <dev@makos.example>" > "$ROOT/Installer/repo/makos-key.asc"
fi
gpg --detach-sign --armor -o "dists/$CODENAME/Release.gpg" "dists/$CODENAME/Release"
gpg --clearsign -o "dists/$CODENAME/InRelease" "dists/$CODENAME/Release"

echo "==> Repositório em: $REPO"

if [ "${1:-}" = "--install" ]; then
  echo "==> Adicionando ao apt"
  echo "deb [signed-by=$ROOT/Installer/repo/makos-key.asc] file://$REPO $CODENAME main" \
    | sudo tee /etc/apt/sources.list.d/makos.list
  sudo cp "$ROOT/Installer/repo/makos-key.asc" /usr/share/keyrings/makos.asc
  sudo apt update
  echo "==> Instalando pacotes"
  sudo apt install -y mak-os-desktop mak-os-apps mak-os-themes mak-os-boot
fi

echo "==> Concluído."
