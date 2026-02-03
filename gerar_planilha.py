import pandas as pd

# Definição das Abas e Colunas
estrutura = {
    "clientes": ["id", "nome", "telefone", "email", "data_nascimento", "anamnese", "created_at"],
    "procedimentos": ["id", "nome", "valor", "duracao_min", "categoria"],
    "agenda": ["id", "cliente_id", "cliente_nome", "procedimento_id", "procedimento_nome", "data_agendamento", "hora_agendamento", "status"],
    "despesas": ["id", "descricao", "valor", "data_despesa", "categoria", "created_at"]
}

# Cria o arquivo Excel
nome_arquivo = "banco_dados_estetica.xlsx"

with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
    for aba, colunas in estrutura.items():
        # Cria um DataFrame vazio apenas com os cabeçalhos
        df = pd.DataFrame(columns=colunas)
        df.to_excel(writer, sheet_name=aba, index=False)

print(f"✅ Arquivo '{nome_arquivo}' criado com sucesso! Agora suba ele para o Google Drive.")