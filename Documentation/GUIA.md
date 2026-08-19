# Guia do Usuário — Pineapple OS

Bem-vindo ao **Pineapple OS**, um sistema operacional rápido, bonito e privado.
Este guia cobre o dia a dia: entrar, navegar, usar os apps, instalar programas
e aproveitar o assistente de IA.

---

## 1. Primeiros passos

### Entrar no sistema

1. Ligue o computador. O GRUB oferece **Pineapple OS** como primeira opção.
2. A tela de login (SDDM) mostra o relógio e o formulário:
   - digite o nome de **usuário** e a **senha**;
   - escolha a sessão (por padrão **Pineapple OS**);
   - pressione **Enter** ou clique em **Entrar**.
3. Para reiniciar ou desligar sem entrar, use os links **Reiniciar** e **Desligar**
   na parte de baixo da tela.

### O ambiente de trabalho

- **Barra superior**: relógio, status do sistema (rede, bateria, volume) e menu.
- **Dock**: na parte inferior, mostra seus aplicativos favoritos e os em execução.
  Passe o mouse para ver o efeito de aumento; clique para abrir. Janelas
  minimizadas aparecem no Dock após a divisória (com animação); clique na
  miniatura para restaurar.
- **Mission Control**: com **F3** ou **Ctrl+Seta acima** você vê todas as janelas
  e as áreas de trabalho; clique em um card para focar a janela, clique em uma
  área para trocar de área, e `Esc` fecha. No touchpad, deslize 3 dedos para
  cima para abrir.
- **Áreas de trabalho**: use **Super (Win) + 1..4** para alternar entre áreas.
- **Minimizar janelas**: use **Super + M** para minimizar a janela ativa; ela
  "colapsa" para o Dock e pode ser restaurada clicando na miniatura.
- **Atalhos úteis**:
  | Ação                | Atalho             |
  |---------------------|--------------------|
  | Abrir o Launcher    | `Super` ou `Alt+F1`|
  | Abrir o Terminal    | `Ctrl+Alt+T`       |
  | Abrir o Canopy      | `Super+F`          |
  | Mission Control     | `F3` ou `Ctrl+Up`  |
  | Minimizar janela    | `Super+M`          |
  | Mudar de área       | `Super+1..4`       |
  | Bloquear a tela     | `Super+L`          |

---

## 2. Aplicativos nativos

Todos os apps usam o visual e os ícones do Pineapple OS e abrem rapidamente.

| App             | Para que serve                              |
|-----------------|---------------------------------------------|
| **Pineapple Canopy**  | Navegar nos arquivos, copiar/colar, renomear e excluir. |
| **Pineapple Terminal**| Linha de comando, com abas (`Ctrl+Shift+T` nova, `Ctrl+Shift+W` fecha). |
| **Pineapple Calculator** | Cálculos simples e avançados.            |
| **Pineapple Notes**   | Notas rápidas, com busca, exportar/importar em Markdown. |
| **Pineapple Photos**  | Ver e organizar imagens.                     |
| **Pineapple Music**   | Tocar música local.                          |
| **Pineapple Browser** | Navegar na internet.                         |
| **Pineapple Monitor** | Ver uso de CPU, memória e lista de processos.|
| **Pineapple Settings**| Configurar o sistema.                        |
| **Pineapple Store**   | Instalar e gerenciar aplicativos.            |

### Pineapple Canopy — truques

- **Clique direito** em um arquivo/pasta para **copiar, colar, renomear,
  excluir (lixeira) ou criar nova pasta**.
- Clique duplo em uma pasta para entrar; em um arquivo, abre com o app padrão.
- Use a barra lateral (Início, Documentos, Downloads, Imagens) para ir direto.
- A lupa na barra filtra a pasta atual enquanto você digita.

### Pineapple Terminal — atalhos

| Atalho            | Ação                 |
|-------------------|----------------------|
| `Ctrl+Shift+T`    | Nova aba             |
| `Ctrl+Shift+W`    | Fechar aba           |
| `Ctrl+1..9`       | Ir para a aba N      |
| `Ctrl++` / `Ctrl+-` | Aumentar/diminuir fonte |

---

## 3. Instalar programas

### Pineapple Store (Flatpak)

1. Abra o **Pineapple Store**.
2. Escolha uma **categoria** na barra lateral (Gráficos, Escritório, Mídia…)
   ou pesquise pelo nome.
3. Clique em **Instalar** no cartão do app. A primeira instalação pode demorar
   um pouco (baixa o runtime do Flatpak).
4. Pronto — o app aparece no Launcher.

### Outros formatos

- **AppImage**: coloque o arquivo na pasta `~/Applications` e use o
  **Pineapple AppImage Manager**; ou dê permissão de execução e abra normalmente.
- **Programas Windows (.exe)**: com o **Wine** instalado, abra o `.exe` pelo
  Canopy (clique duplo) ou pelo menu de contexto.
- **Android**: se o **Waydroid** estiver configurado, apps Android rodam em
  janelas normais (veja `waydroid` na documentação de compatibilidade).
- **APT (Debian)**: terminal → `sudo apt install <pacote>`.

---

## 4. Assistente de IA (Pineapple AI)

O Pineapple OS inclui um assistente que roda **localmente** com o **Ollama**.

- **Pineapple Assistant** (gráfico): painel de conversa. Clique no ícone de voz para
  falar em vez de digitar (requer o pacote de voz).
- **Terminal**: `pineapple-ai "sua pergunta"` — responde direto no terminal.
- **O que ele faz**:
  - responde perguntas e explica conceitos;
  - abre aplicativos (`abra o terminal`);
  - procura arquivos (`procure por relatorio.pdf`);
  - resume documentos (texto/Markdown);
  - auxilia em programação.

> Privacidade: nada sai da sua máquina. O modelo roda localmente.
> Para configurar, veja `Scripts/setup-ollama.sh`.

---

## 5. Manutenção

| Comando                      | O que faz                          |
|------------------------------|------------------------------------|
| `pineapple-update`                 | Verifica e aplica atualizações OTA |
| `sudo apt update && upgrade` | Atualiza pacotes do sistema        |
| `flatpak update`             | Atualiza apps Flatpak              |
| `pineapple-ai`                     | Assistente no terminal             |

O **Pineapple Monitor** ajuda a entender o que está usando CPU/memória. Use o botão
**Terminar selecionado** apenas em processos que você reconhece.

---

## 6. Resolução de problemas

- **Não entro no Wayland/sessão**: verifique se o usuário está nos grupos
  `video`, `input` e `seat` (`sudo usermod -aG video,input,seat $USER`).
- **App não aparece no Launcher**: o cache é atualizado automaticamente; se
  não aparecer, reinicie a sessão (`pineapple-session`).
- **Sem som**: confira o volume na barra superior e o `wireplumber`.
- **Algo travou**: pressione `Super+L` para bloquear, ou reinicie com o menu
  da barra superior. O último recurso é `Ctrl+Alt+Supr` (reiniciar).

Para mais detalhes técnicos, veja `Documentation/` (arquitetura, roadmap e
guia de desenvolvimento).
