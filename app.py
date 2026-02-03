import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema Estética", layout="wide", page_icon="✨")
ARQUIVO_DB = "banco_dados_estetica.xlsx"

# --- CONFIGURAÇÃO DE E-MAIL (Preencha aqui ou use Secrets) ---
EMAIL_REMETENTE = "luizmarcelomanacas@gmail.com"
EMAIL_SENHA = "njyt nrvd vtro jgwi"  # Senha de App do Google
EMAIL_DESTINATARIO = "luizmarcelomanacas@gmail.com"


# --- FUNÇÕES DE BANCO DE DADOS (EXCEL LOCAL) ---
def load_data():
    if not os.path.exists(ARQUIVO_DB):
        # Se não existe, cria as abas vazias
        with pd.ExcelWriter(ARQUIVO_DB, engine='openpyxl') as writer:
            pd.DataFrame(
                columns=['id', 'nome', 'telefone', 'email', 'data_nascimento', 'anamnese', 'created_at']).to_excel(
                writer, sheet_name='clientes', index=False)
            pd.DataFrame(
                columns=['id', 'cliente_id', 'cliente_nome', 'procedimento_id', 'procedimento_nome', 'data_agendamento',
                         'hora_agendamento', 'status']).to_excel(writer, sheet_name='agenda', index=False)
            pd.DataFrame(columns=['id', 'nome', 'valor', 'duracao_min', 'categoria']).to_excel(writer,
                                                                                               sheet_name='procedimentos',
                                                                                               index=False)
            pd.DataFrame(columns=['id', 'descricao', 'valor', 'data_despesa', 'categoria', 'created_at']).to_excel(
                writer, sheet_name='despesas', index=False)

    try:
        # Lê todas as abas
        xls = pd.read_excel(ARQUIVO_DB, sheet_name=None)
        return xls
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return {}


def save_data(dfs_dict):
    try:
        with pd.ExcelWriter(ARQUIVO_DB, engine='openpyxl') as writer:
            for sheet_name, df in dfs_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


# --- FUNÇÃO DE ENVIO DE E-MAIL (ROBÔ) ---
def enviar_agenda_email():
    try:
        dfs = load_data()
        df_ag = dfs.get('agenda', pd.DataFrame())

        hoje = str(date.today())
        df_hoje = pd.DataFrame()

        if not df_ag.empty and 'data_agendamento' in df_ag.columns:
            # Converte para string para garantir a comparação
            df_ag['data_agendamento'] = df_ag['data_agendamento'].astype(str)
            df_hoje = df_ag[df_ag['data_agendamento'] == hoje].sort_values('hora_agendamento')

        # Monta o E-mail
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda do Dia - {datetime.now().strftime('%d/%m/%Y')}"

        if df_hoje.empty:
            html = f"<h3>Bom dia! ☀️</h3><p>Agenda livre hoje ({datetime.now().strftime('%d/%m')}).</p>"
        else:
            tabela = """<table style='width:100%; border-collapse: collapse; font-family: Arial;'>
            <tr style='background-color: #d4af37; color: white;'><th style='padding:8px;'>Hora</th><th style='padding:8px;'>Cliente</th><th style='padding:8px;'>Procedimento</th></tr>"""

            for _, row in df_hoje.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela += f"<tr style='border-bottom:1px solid #ddd;'><td style='padding:8px;'><b>{hora}</b></td><td style='padding:8px;'>{row['cliente_nome']}</td><td style='padding:8px;'>{row['procedimento_nome']}</td></tr>"
            tabela += "</table>"
            html = f"<h3>Agenda de Hoje:</h3>{tabela}"

        msg.attach(MIMEText(html, 'html'))

        # Envia
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(EMAIL_REMETENTE, EMAIL_SENHA)
        s.send_message(msg)
        s.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro no envio: {e}"


# --- GATILHO DO GITHUB (ROBÔ) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# --- INTERFACE ---
with st.sidebar:
    st.title("✨ Menu")
    menu = st.radio("Ir para",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "Insights 🎂"])
    st.markdown("---")
    if st.button("Recarregar Dados"): st.rerun()

dfs = load_data()

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("Visão Geral")
    df_ag = dfs.get('agenda', pd.DataFrame())
    hoje = str(date.today())
    qtd = 0
    if not df_ag.empty and 'data_agendamento' in df_ag.columns:
        qtd = len(df_ag[df_ag['data_agendamento'].astype(str) == hoje])
    st.metric("Agendamentos Hoje", qtd)
    st.success("Sistema rodando em modo Local (Excel).")

# 2. CLIENTES
elif menu == "Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Novo", "Lista"])
    with t1:
        with st.form("cli_form"):
            nome = st.text_input("Nome")
            tel = st.text_input("Telefone")
            email = st.text_input("Email")
            nasc = st.date_input("Nascimento", min_value=date(1920, 1, 1))
            obs = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                df = dfs.get('clientes', pd.DataFrame())
                novo_id = 1 if df.empty else df['id'].max() + 1
                novo = pd.DataFrame([{
                    "id": novo_id, "nome": nome, "telefone": tel, "email": email,
                    "data_nascimento": str(nasc), "anamnese": obs, "created_at": str(datetime.now())
                }])
                dfs['clientes'] = pd.concat([df, novo], ignore_index=True)
                save_data(dfs)
                st.success("Cliente salvo!")
                time.sleep(1);
                st.rerun()
    with t2:
        st.dataframe(dfs.get('clientes', pd.DataFrame()), use_container_width=True)

# 3. PROCEDIMENTOS
elif menu == "Procedimentos":
    st.title("Procedimentos")
    with st.form("proc_form"):
        n = st.text_input("Nome");
        v = st.number_input("Valor");
        d = st.number_input("Minutos")
        if st.form_submit_button("Salvar"):
            df = dfs.get('procedimentos', pd.DataFrame())
            nid = 1 if df.empty else df['id'].max() + 1
            novo = pd.DataFrame([{"id": nid, "nome": n, "valor": v, "duracao_min": d, "categoria": "Geral"}])
            dfs['procedimentos'] = pd.concat([df, novo], ignore_index=True)
            save_data(dfs)
            st.success("Salvo!");
            time.sleep(1);
            st.rerun()
    st.dataframe(dfs.get('procedimentos', pd.DataFrame()), use_container_width=True)

# 4. AGENDA
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Agendar", "Ver Agenda"])
    df_cli = dfs.get('clientes', pd.DataFrame())
    df_proc = dfs.get('procedimentos', pd.DataFrame())

    with t1:
        if not df_cli.empty and not df_proc.empty:
            with st.form("ag_form"):
                cnome = st.selectbox("Cliente", df_cli['nome'].unique())
                pnome = st.selectbox("Procedimento", df_proc['nome'].unique())
                dt = st.date_input("Data")
                hr = st.time_input("Hora")
                if st.form_submit_button("Agendar"):
                    cid = df_cli[df_cli['nome'] == cnome]['id'].values[0]
                    pid = df_proc[df_proc['nome'] == pnome]['id'].values[0]
                    df = dfs.get('agenda', pd.DataFrame())
                    nid = 1 if df.empty else df['id'].max() + 1
                    novo = pd.DataFrame([{
                        "id": nid, "cliente_id": cid, "cliente_nome": cnome,
                        "procedimento_id": pid, "procedimento_nome": pnome,
                        "data_agendamento": str(dt), "hora_agendamento": str(hr), "status": "Agendado"
                    }])
                    dfs['agenda'] = pd.concat([df, novo], ignore_index=True)
                    save_data(dfs)
                    st.success("Agendado!");
                    time.sleep(1);
                    st.rerun()
        else:
            st.warning("Cadastre clientes e procedimentos antes.")
    with t2:
        st.dataframe(dfs.get('agenda', pd.DataFrame()), use_container_width=True)

# 5. FINANCEIRO
elif menu == "Financeiro":
    st.title("Financeiro")
    with st.form("fin_form"):
        desc = st.text_input("Descrição");
        val = st.number_input("Valor")
        dt = st.date_input("Data");
        cat = st.selectbox("Categoria", ["Geral", "Produtos", "Aluguel"])
        if st.form_submit_button("Lançar"):
            df = dfs.get('despesas', pd.DataFrame())
            nid = 1 if df.empty else df['id'].max() + 1
            novo = pd.DataFrame([{
                "id": nid, "descricao": desc, "valor": val, "data_despesa": str(dt),
                "categoria": cat, "created_at": str(datetime.now())
            }])
            dfs['despesas'] = pd.concat([df, novo], ignore_index=True)
            save_data(dfs)
            st.success("Lançado!");
            time.sleep(1);
            st.rerun()
    st.dataframe(dfs.get('despesas', pd.DataFrame()), use_container_width=True)

# 6. RELATÓRIOS
elif menu == "Relatórios":
    st.title("Relatórios")
    df_ag = dfs.get('agenda', pd.DataFrame())
    df_proc = dfs.get('procedimentos', pd.DataFrame())
    total_rec = 0
    if not df_ag.empty and not df_proc.empty:
        m = pd.merge(df_ag, df_proc, left_on='procedimento_id', right_on='id', suffixes=('', '_p'))
        total_rec = m['valor'].sum()
    st.metric("Receita Estimada", f"R$ {total_rec:.2f}")

# 7. INSIGHTS
elif menu == "Insights 🎂":
    st.title("Aniversariantes")
    df = dfs.get('clientes', pd.DataFrame())
    if not df.empty and 'data_nascimento' in df.columns:
        df['dt'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
        mes = date.today().month
        aniv = df[df['dt'].dt.month == mes]
        if not aniv.empty:
            st.balloons()
            st.dataframe(aniv[['nome', 'telefone', 'data_nascimento']])
        else:
            st.info("Nenhum aniversariante no mês.")