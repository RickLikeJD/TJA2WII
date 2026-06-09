import os
import json
from tkinter import Tk, filedialog

CONFIG_FILE = "src/Config/config.json"

def get_songs_folder():
    """Lê a pasta de músicas do config ou pede para o usuário selecionar."""

    # Garante que a pasta utils exista
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    # 1. Tenta ler o arquivo de configuração existente
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                pasta_salva = config.get("songs_folder")

                # Se a pasta existir no PC, retorna ela direto (modo silencioso)
                if pasta_salva and os.path.exists(pasta_salva):
                    return pasta_salva
        except json.JSONDecodeError:
            pass # Se o JSON corromper, ignora e pede a pasta de novo

    # 2. Se não achou o config ou a pasta é inválida, abre o Tkinter
    print("Songs folder not configured or invalid.")
    print("Please, select your songs directory on the popup window...")

    root = Tk()
    root.withdraw() # Esconde a janela principal do Tkinter
    root.attributes('-topmost', True) # Força a janela a abrir por cima do terminal

    folder_selected = filedialog.askdirectory(title="Select Taiko Songs Folder")
    root.destroy() # Fecha os processos do Tkinter

    # Se o usuário fechar a janela sem selecionar nada
    if not folder_selected:
        print("No folder selected. Exiting...")
        exit()

    # 3. Salva a nova pasta no _config.json para a próxima vez
    nova_config = {"songs_folder": folder_selected}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(nova_config, f, indent=4)

    print(f"✅ Folder saved to config: {folder_selected}\n")
    return folder_selected
