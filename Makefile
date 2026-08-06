# =============================================================================
#  Mak OS — Makefile de conveniência
# =============================================================================

PREFIX ?= /usr/local

.PHONY: all help build python icons rust test install uninstall iso kernel \
        session clean fmt check

help:
	@echo "Alvos disponíveis:"
	@echo "  build    compila componentes Rust + copia apps Python"
	@echo "  icons    gera os ícones SVG"
	@echo "  test     roda a suíte de testes (Python)"
	@echo "  install  instala no sistema (sudo)"
	@echo "  iso      gera a ISO live (live-build)"
	@echo "  kernel   compila o kernel otimizado"
	@echo "  session  inicia a sessão de desenvolvimento"
	@echo "  clean    remove artefatos de build"

all: build

build: icons
	./Scripts/build.sh

python:
	python3 -m py_compile Apps/*/*.py AI/*.py
	@echo "apps Python OK"

rust:
	cargo build --release --manifest-path Desktop/Cargo.toml
	cargo build --release --manifest-path Dock/Cargo.toml
	cargo build --release --manifest-path Launcher/Cargo.toml
	cargo build --release --manifest-path Launchpad/Cargo.toml
	cargo build --release --manifest-path Finder/Cargo.toml
	cargo build --release --manifest-path Gestures/Cargo.toml

icons:
	python3 Scripts/gen-icons.py

test:
	python3 -m unittest discover -s tests -v

install:
	sudo ./Scripts/install.sh
	./Scripts/setup-systemd.sh

iso:
	./Scripts/build-iso.sh

kernel:
	./Scripts/build-kernel.sh

session:
	./Scripts/start-session.sh

fmt:
	-cargo fmt --manifest-path Desktop/Cargo.toml
	-cargo fmt --manifest-path Dock/Cargo.toml
	-cargo fmt --manifest-path Launcher/Cargo.toml
	-cargo fmt --manifest-path Launchpad/Cargo.toml
	-cargo fmt --manifest-path Finder/Cargo.toml
	-cargo fmt --manifest-path Gestures/Cargo.toml
	@echo "formatação aplicada"

check: test
	-cargo clippy --manifest-path Desktop/Cargo.toml -- -D warnings
	-cargo clippy --manifest-path Dock/Cargo.toml -- -D warnings
	-cargo clippy --manifest-path Launcher/Cargo.toml -- -D warnings
	-cargo clippy --manifest-path Launchpad/Cargo.toml -- -D warnings
	-cargo clippy --manifest-path Finder/Cargo.toml -- -D warnings
	-cargo clippy --manifest-path Gestures/Cargo.toml -- -D warnings

clean:
	rm -rf build/ Kernel/build
	cargo clean --manifest-path Desktop/Cargo.toml 2>/dev/null || true
	cargo clean --manifest-path Dock/Cargo.toml 2>/dev/null || true
	cargo clean --manifest-path Launcher/Cargo.toml 2>/dev/null || true
	cargo clean --manifest-path Launchpad/Cargo.toml 2>/dev/null || true
	cargo clean --manifest-path Finder/Cargo.toml 2>/dev/null || true
	cargo clean --manifest-path Gestures/Cargo.toml 2>/dev/null || true
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "limpo"
