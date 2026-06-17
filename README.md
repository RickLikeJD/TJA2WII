# TJA2WII

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)

**Convert TJA chart files into fully compatible Taiko no Tatsujin Wii game assets.**

[English](#english) • [Português](#português)

</div>

---

# English

**TJA2WII** is a modding toolchain that automates the conversion of TJAs files into native binary formats for Taiko no Tatsujin Wii. It handles everything from chart data and audio processing to textures and metadata, outputting files ready to be injected directly into the game.

## Features

* **Interactive CLI:** No coding required. A user-friendly terminal menu guides you through the entire process.
* **Smart Parsing:** Automatically reads `.tja` files to extract titles, artists, BPM, and offsets.
* **Session Manager:** Automatically saves your progress. You can stop and resume your modding session at any time.
* **Full Asset Conversion:** Handles audio (WAV/IDSP/NUB), charts (fumen), textures, lyrics (LZ11), and metadata syncing.

## Compatibility

This tool has been explicitly built for and tested with:

* -[x] TnT Wii: Chogouka-Ban** (Taiko Wii 5)
* -[ ] TnT Wii: Keitebban** (Taiko Wii 4)
* -[ ] TnT Wii: Minna no Party Sandaime** (Taiko Wii 3)
* -[ ] TnT Wii: Do-Don to Nidaime!** (Taiko Wii 2)
* -[ ] Taiko no Tatsujin Wii** (Taiko Wii)
## Installation

### Prerequisites

* Python 3.8 or higher
* FFmpeg
* VGAudioCli

### Setup

1. Clone the repository:

```bash
git clone https://github.com/RickLikeJD/TJA2WII.git
cd TJA2Wii
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Download `ffmpeg.exe` and `VGAudioCli.exe` and place them inside:

```text
src/Audio/bin/
```

On first launch, the tool will ask for your Taiko songs directory and save it for future use.

## Usage

Run:

```bash
python main.py
```

Steps:

1. Select a `.tja` file using the arrow keys.
2. Configure song ID, genre, dancer, and lyrics.
3. Let the tool process the assets.
4. Continue adding songs until you're ready to compile the final game files.

Generated files:

* `tuning.bin`
* `musicinfo.bin`
* `fumensync.bin`


## Support & Donations

If TJA2WII helped you build your dream custom tracklist and saved you hours of manual hex editing, consider supporting the project.

* [Ko-fi](https://ko-fi.com/ricklikejd)
* Open an issue on GitHub for bug reports and feature requests

## Credits & License

* **Taiko no Tatsujin Wii** — Bandai Namco Entertainment
* **FFmpeg**
* **VGAudio** (Thealexbarney)
* **jaconv**
* **Pillow**
* **TJA2Fumen**

Released under the **MIT License**.

---

# Português

**TJA2WII** é um conjunto de ferramentas que automatiza a conversão de arquivos TJAs em formatos binários nativos do Taiko no Tatsujin para Wii. Ele gerencia desde charts e áudio até texturas e metadados, gerando arquivos prontos para serem injetados no jogo.

## Recursos

* **CLI Interativa:** Nenhum conhecimento de programação é necessário.
* **Leitura Inteligente:** Extrai automaticamente títulos, artistas, BPM e offsets dos arquivos `.tja`.
* **Gerenciador de Sessão:** Salva seu progresso automaticamente.
* **Conversão Completa:** Processa áudio (WAV/IDSP/NUB), charts (fumen), texturas, letras (LZ11) e sincronização de metadados.

## Compatibilidade

Compatível e testado com:

* -[x] TnT Wii: Chogouka-Ban** (Taiko Wii 5)
* -[ ] TnT Wii: Keitebban** (Taiko Wii 4)
* -[ ] TnT Wii: Minna no Party Sandaime** (Taiko Wii 3)
* -[ ] TnT Wii: Do-Don to Nidaime!** (Taiko Wii 2)
* -[ ] Taiko no Tatsujin Wii** (Taiko Wii)

## Instalação

### Pré-requisitos

* Python 3.8 ou superior
* FFmpeg
* VGAudioCli

### Configuração

1. Clone o repositório:

```bash
git clone https://github.com/RickLikeJD/TJA2WII.git
cd TJA2Wii
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Baixe `ffmpeg.exe` e `VGAudioCli.exe` e coloque-os em:

```text
src/Audio/bin/
```

Na primeira execução, o programa solicitará o diretório das músicas e salvará essa configuração para usos futuros.

## Como Usar

Execute:

```bash
python main.py
```

Passos:

1. Escolha um arquivo `.tja`.
2. Configure ID, gênero, dançarino e letras.
3. Aguarde o processamento.
4. Adicione quantas músicas desejar e gere os arquivos finais.

Arquivos gerados:

* `tuning.bin`
* `musicinfo.bin`
* `fumensync.bin`

## Suporte e Doações

Se o TJA2WII ajudou você a criar uma tracklist personalizada e economizou horas de edição hexadecimal manual, considere apoiar o projeto.

* [Ko-fi](https://ko-fi.com/ricklikejd)
* Abra uma issue no GitHub para relatar problemas ou sugerir melhorias

## Créditos e Licença

* **Taiko no Tatsujin Wii** — Bandai Namco Entertainment
* **FFmpeg**
* **VGAudio** (Thealexbarney)
* **jaconv**
* **Pillow**
* **TJA2Fumen**

Distribuído sob a **Licença MIT**.
