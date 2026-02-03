import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada", layout="wide", page_icon="✨")

# --- CONEXÃO BLINDADA (USANDO O NOME "gsheets" DOS SEGREDOS) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro de conexão: {e}")


# --- FUNÇÕES DE DADOS ---
def get_data(worksheet):
    try:
        # ttl=0 obriga a ler dados frescos do Google e não do cache
        return conn.read(worksheet=worksheet, ttl=0)
    except Exception:
        return pd.DataFrame()


def add_data(worksheet, new_data_dict):
    try:
        df = get_data(worksheet)

        # Lógica de ID automático seguro
        if not df.empty and 'id' in df.columns:
            # Garante que o ID é número, tratando erros
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0)
            new_id = int(df['id'].max()) + 1
        else:
            new_id = 1

        new_data_dict['id'] = new_id
        new_row = pd.DataFrame([new_data_dict])

        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)

        conn.update(worksheet=worksheet, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


# --- CONFIGURAÇÃO DE E-MAIL (PREENCHA SEUS DADOS AQUI OU NOS SECRETS) ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'  # Senha de App do Google
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


# --- FUNÇÃO DE ENVIO DE E-MAIL (AGENDA) ---
def enviar_agenda_email():
    try:
        hoje = str(date.today())
        df_agenda = get_data("agenda")

        # Filtra agenda de hoje
        df_hoje = pd.DataFrame()
        if not df_agenda.empty and 'data_agendamento' in df_agenda.columns:
            df_agenda['data_agendamento'] = df_agenda['data_agendamento'].astype(str)
            df_hoje = df_agenda[
                (df_agenda['data_agendamento'] == hoje) & (df_agenda['status'] == 'Agendado')].sort_values(
                'hora_agendamento')

        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda Bárbara Castro - {datetime.now().strftime('%d/%m/%Y')}"

        if df_hoje.empty:
            corpo_html = f"<h3>Bom dia! ☀️</h3><p>Não há clientes agendados para hoje ({datetime.now().strftime('%d/%m')}). Aproveite o dia! ✨</p>"
        else:
            tabela_html = """<table style='width:100%; border-collapse: collapse; font-family: Arial;'>
            <tr style='background-color: #d4af37; color: white;'><th style='padding:10px;'>Hora</th><th style='padding:10px;'>Cliente</th><th style='padding:10px;'>Procedimento</th></tr>"""

            for i, row in df_hoje.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela_html += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding:10px; text-align:center'><b>{hora}</b></td><td style='padding:10px;'>{row['cliente_nome']}</td><td style='padding:10px;'>{row['procedimento_nome']}</td></tr>"
            tabela_html += "</table>"

            corpo_html = f"<h3>Agenda de Hoje:</h3>{tabela_html}<br><p>Sistema de Gestão ✨</p>"

        msg.attach(MIMEText(corpo_html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro ao enviar e-mail: {e}"


# --- GATILHO PARA O ROBÔ (GITHUB ACTIONS) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    resultado = enviar_agenda_email()
    st.write(resultado)
    st.stop()

# --- INTERFACE (SIDEBAR) ---
with st.sidebar:
    st.title("✨ Gestão Estética")
    menu = st.radio("MENU",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "Insights 🎂"])
    st.markdown("---")
    if st.button("🔄 Reiniciar Sistema"):
        st.cache_data.clear()
        st.rerun()

# --- PÁGINAS ---

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("Visão Geral")
    df_ag = get_data("agenda")
    hoje_str = str(date.today())
    qtd_hoje = 0
    if not df_ag.empty and 'data_agendamento' in df_ag.columns:
        qtd_hoje = len(df_ag[df_ag['data_agendamento'].astype(str) == hoje_str])

    st.metric("Agendamentos Hoje", qtd_hoje)
    st.info("O sistema está conectado à planilha segura.")

# 2. AGENDA
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo Agendamento", "Visualizar"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")

    with t1:
        with st.form("form_agenda"):
            # Carrega listas para seleção
            clientes_lista = df_cli['nome'].unique().tolist() if not df_cli.empty else []
            procs_lista = df_proc['nome'].unique().tolist() if not df_proc.empty else []

            c_nome = st.selectbox("Cliente", clientes_lista)
            p_nome = st.selectbox("Procedimento", procs_lista)
            d_ag = st.date_input("Data")
            h_ag = st.time_input("Hora")

            if st.form_submit_button("Agendar"):
                if c_nome and p_nome:
                    # Busca IDs
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
                    st.warning("Cadastre clientes e procedimentos antes.")
    with t2:
        st.dataframe(get_data("agenda"), use_container_width=True)

# 3. CLIENTES (O TESTE DE FOGO)
elif menu == "Clientes":
    st.title("Gestão de Clientes")
    t1, t2 = st.tabs(["Cadastrar", "Lista"])

    with t1:
        with st.form("form_cli"):
            nome = st.text_input("Nome Completo")
            tel = st.text_input("Telefone")
            email = st.text_input("E-mail")
            nasc = st.date_input("Data de Nascimento", min_value=date(1920, 1, 1))
            anamnese = st.text_area("Anamnese")

            if st.form_submit_button("Salvar Cliente"):
                if nome:
                    dados = {
                        "nome": nome, "telefone": tel, "email": email,
                        "data_nascimento": str(nasc), "anamnese": anamnese,
                        "created_at": str(datetime.now())
                    }
                    if add_data("clientes", dados):
                        st.success("Cliente Salvo com Sucesso!")
                        time.sleep(1);
                        st.rerun()
                else:
                    st.warning("Nome é obrigatório.")
    with t2:
        st.dataframe(get_data("clientes"), use_container_width=True)

# 4. PROCEDIMENTOS
elif menu == "Procedimentos":
    st.title("Procedimentos")
    with st.form("form_proc"):
        n = st.text_input("Nome");
        v = st.number_input("Valor", min_value=0.0)
        if st.form_submit_button("Salvar"):
            if add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": 60, "categoria": "Geral"}):
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
    st.dataframe(get_data("procedimentos"), use_container_width=True)

# 5. FINANCEIRO
elif menu == "Financeiro":
    st.title("Financeiro")
    with st.form("form_desp"):
        d = st.text_input("Descrição");
        v = st.number_input("Valor", min_value=0.0)
        dt = st.date_input("Data")
        if st.form_submit_button("Lançar"):
            if add_data("despesas", {"descricao": d, "valor": v, "data_despesa": str(dt), "categoria": "Geral"}):
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
    if not df_ag.empty and not df_proc.empty and 'procedimento_id' in df_ag.columns:
        merged = pd.merge(df_ag, df_proc, left_on='procedimento_id', right_on='id', suffixes=('', '_proc'))
        if not merged.empty: rec = merged['valor'].sum()
    st.metric("Receita Estimada (Agenda)", f"R$ {rec:.2f}")

# 7. INSIGHTS
elif menu == "Insights 🎂":
    st.title("Aniversariantes do Mês")
    df_cli = get_data("clientes")
    if not df_cli.empty and 'data_nascimento' in df_cli.columns:
        df_cli['nasc_dt'] = pd.to_datetime(df_cli['data_nascimento'], errors='coerce')
        mes = date.today().month
        aniversariantes = df_cli[df_cli['nasc_dt'].dt.month == mes]
        if not aniversariantes.empty:
            st.balloons()
            st.dataframe(aniversariantes[['nome', 'telefone', 'data_nascimento']])
        else:
            st.info("Ninguém faz aniversário este mês.")