import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Estética Avançada", layout="wide", page_icon="✨")

# --- CONEXÃO COM SUPABASE ---
# Pega as senhas dos Segredos
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro ao conectar no Supabase. Verifique os Secrets.")
    st.stop()


# --- FUNÇÕES DE DADOS (SUPABASE) ---
def get_data(table_name):
    """Busca todos os dados de uma tabela"""
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        return pd.DataFrame()


def add_data(table_name, data_dict):
    """Adiciona uma nova linha"""
    try:
        # O ID é gerado automaticamente pelo Supabase, não enviamos ele
        supabase.table(table_name).insert(data_dict).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


# --- CONFIGURAÇÃO DE E-MAIL ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'senha_de_app_google'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'

# --- ENVIO DE E-MAIL (ROBÔ) ---
def enviar_agenda_email():
    try:
        hoje = str(date.today())
        df_agenda = get_data("agenda")

        df_hoje = pd.DataFrame()
        if not df_agenda.empty and 'data_agendamento' in df_agenda.columns:
            df_hoje = df_agenda[
                (df_agenda['data_agendamento'] == hoje) & (df_agenda['status'] == 'Agendado')].sort_values(
                'hora_agendamento')

        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda Supabase - {datetime.now().strftime('%d/%m/%Y')}"

        if df_hoje.empty:
            html = f"<h3>Agenda livre hoje ({datetime.now().strftime('%d/%m')}) ✨</h3>"
        else:
            tabela = """<table style='width:100%; border-collapse: collapse; font-family: Arial;'>
            <tr style='background-color: #6C63FF; color: white;'><th style='padding:10px;'>Hora</th><th>Cliente</th><th>Procedimento</th></tr>"""
            for _, row in df_hoje.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding:10px; text-align:center'><b>{hora}</b></td><td>{row['cliente_nome']}</td><td>{row['procedimento_nome']}</td></tr>"
            tabela += "</table>"
            html = f"<h3>Agenda do Dia:</h3>{tabela}"

        msg.attach(MIMEText(html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso (Via Supabase)!"
    except Exception as e:
        return f"❌ Erro: {e}"


# --- GATILHO EXTERNO ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# --- INTERFACE ---
with st.sidebar:
    st.title("✨ Sistema Supabase")
    menu = st.radio("MENU",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "Insights 🎂"])
    st.markdown("---")
    if st.button("🔄 Atualizar"): st.rerun()

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("Visão Geral")
    df_ag = get_data("agenda")
    hoje = 0
    if not df_ag.empty:
        hoje = len(df_ag[df_ag['data_agendamento'] == str(date.today())])

    c1, c2 = st.columns(2)
    c1.metric("Agendamentos Hoje", hoje)
    c2.success("Banco de Dados: Supabase (Nuvem) 🟢")

# 2. AGENDA
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo", "Visualizar"])
    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")

    with t1:
        with st.form("form_ag"):
            # Listas para selectbox
            clientes = df_cli['nome'].tolist() if not df_cli.empty else []
            procs = df_proc['nome'].tolist() if not df_proc.empty else []

            c_nome = st.selectbox("Cliente", clientes)
            p_nome = st.selectbox("Procedimento", procs)
            d_ag = st.date_input("Data")
            h_ag = st.time_input("Hora")

            if st.form_submit_button("Agendar"):
                if c_nome and p_nome:
                    c_id = df_cli[df_cli['nome'] == c_nome]['id'].values[0]
                    p_id = df_proc[df_proc['nome'] == p_nome]['id'].values[0]

                    dados = {
                        "cliente_id": int(c_id), "cliente_nome": c_nome,
                        "procedimento_id": int(p_id), "procedimento_nome": p_nome,
                        "data_agendamento": str(d_ag), "hora_agendamento": str(h_ag),
                        "status": "Agendado"
                    }
                    if add_data("agenda", dados):
                        st.success("Agendado!")
                        time.sleep(1);
                        st.rerun()
                else:
                    st.warning("Cadastre clientes primeiro.")
    with t2:
        st.dataframe(get_data("agenda"), use_container_width=True)

# 3. CLIENTES
elif menu == "Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Cadastro", "Lista"])
    with t1:
        with st.form("form_cli"):
            nome = st.text_input("Nome")
            tel = st.text_input("Telefone")
            email = st.text_input("Email")
            nasc = st.date_input("Nascimento", min_value=date(1920, 1, 1))
            anamnese = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                if nome:
                    dados = {
                        "nome": nome, "telefone": tel, "email": email,
                        "data_nascimento": str(nasc), "anamnese": anamnese
                    }
                    if add_data("clientes", dados):
                        st.success("Cliente Salvo!")
                        time.sleep(1);
                        st.rerun()
                else:
                    st.error("Nome obrigatório.")
    with t2:
        st.dataframe(get_data("clientes"), use_container_width=True)

# 4. PROCEDIMENTOS
elif menu == "Procedimentos":
    st.title("Procedimentos")
    with st.form("form_proc"):
        n = st.text_input("Nome");
        v = st.number_input("Valor");
        d = st.number_input("Minutos")
        if st.form_submit_button("Salvar"):
            if add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d, "categoria": "Geral"}):
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
    st.dataframe(get_data("procedimentos"), use_container_width=True)

# 5. FINANCEIRO
elif menu == "Financeiro":
    st.title("Financeiro")
    with st.form("form_fin"):
        d = st.text_input("Descrição");
        v = st.number_input("Valor")
        dt = st.date_input("Data");
        c = st.selectbox("Cat", ["Geral", "Aluguel", "Produtos"])
        if st.form_submit_button("Lançar"):
            if add_data("despesas", {"descricao": d, "valor": v, "data_despesa": str(dt), "categoria": c}):
                st.success("Lançado!");
                time.sleep(1);
                st.rerun()
    st.dataframe(get_data("despesas"), use_container_width=True)

# 6. RELATÓRIOS
elif menu == "Relatórios":
    st.title("Relatórios")
    df_ag = get_data("agenda")
    df_proc = get_data("procedimentos")
    rec = 0
    if not df_ag.empty and not df_proc.empty:
        merged = pd.merge(df_ag, df_proc, left_on='procedimento_id', right_on='id', suffixes=('', '_p'))
        rec = merged['valor'].sum()
    st.metric("Receita Estimada", f"R$ {rec:.2f}")

# 7. INSIGHTS
elif menu == "Insights 🎂":
    st.title("Aniversariantes")
    df = get_data("clientes")
    if not df.empty and 'data_nascimento' in df.columns:
        df['dt'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
        mes = date.today().month
        aniv = df[df['dt'].dt.month == mes]
        if not aniv.empty:
            st.balloons();
            st.dataframe(aniv[['nome', 'telefone', 'data_nascimento']])
        else:
            st.info("Ninguém faz aniversário este mês.")