import os
import time


def atualizar_github():
    print("🚀 Iniciando atualização para o GitHub...")

    # 1. Adiciona todos os arquivos modificados
    print("1. Adicionando arquivos...")
    os.system("git add .")

    # 2. Pergunta o que você mudou (para o histórico)
    mensagem = input("📝 Digite uma mensagem sobre o que você mudou: ")
    if not mensagem:
        mensagem = "Atualizacao automatica via script"

    # 3. Salva a versão (Commit)
    print("2. Salvando versão local...")
    os.system(f'git commit -m "{mensagem}"')

    # 4. Envia para a nuvem (Push)
    print("3. Enviando para a nuvem...")
    resultado = os.system("git push -u origin main")

    # CORREÇÃO: A variável agora está escrita certa (resultado)
    if resultado == 0:
        print("\n✅ Sucesso! O sistema foi atualizado.")
        print("O Streamlit Cloud irá reiniciar automaticamente em instantes.")
    else:
        print("\n❌ Ocorreu um erro. Verifique se você tem internet ou permissão.")

    time.sleep(3)


if __name__ == "__main__":
    atualizar_github()