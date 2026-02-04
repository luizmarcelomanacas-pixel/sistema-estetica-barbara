import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada", layout="wide", page_icon="✨")

# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro de conexão com o Banco de Dados. Verifique os Segredos.")
    st.stop()

# --- CONFIGURAÇÃO DE E-MAIL (PREENCHA AQUI) ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


# --- FUNÇÕES DE DADOS ---
def get_data(table):
    """Busca dados do Supabase"""
    try:
        response = supabase.table(table).select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()


def add_data(table, data):
    """Salva dados no Supabase"""
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


# --- FUNÇÕES DE EXPORTAÇÃO (PDF/EXCEL) ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()


def gerar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')
    pdf.ln(10)
    colunas = df.columns[:4]
    for col in colunas:
        pdf.cell(45, 10, str(col).upper(), 1)
    pdf.ln()
    for i, row in df.iterrows():
        for col in colunas:
            txt = str(row[col])[:20]
            pdf.cell(45, 10, txt, 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')


# --- FUNÇÃO DE E-MAIL (AGENDA) ---
def enviar_agenda_email():
    try:
        # Busca agenda do banco
        df_ag = get_data("agenda")
        hoje_bd = date.today().strftime('%Y-%m-%d')  # Formato do banco (YYYY-MM-DD)
        hoje_br = date.today().strftime('%d/%m/%Y')  # Formato visual (DD/MM/YYYY)

        # Filtra apenas hoje
        df_hoje = pd.DataFrame()
        if not df_ag.empty and 'data_agendamento' in df_ag.columns:
            df_hoje = df_ag[df_ag['data_agendamento'] == hoje_bd].sort_values('hora_agendamento')

        # Monta o e-mail
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda do Dia - {hoje_br}"

        if df_hoje.empty:
            html = f"<h3>Bom dia! ☀️</h3><p>Agenda livre para hoje ({hoje_br}).</p>"
        else:
            tabela = """<table style='width:100%; border-collapse: collapse; font-family: Arial;'>
            <tr style='background-color: #6C63FF; color: white;'><th style='padding:10px;'>Hora</th><th>Cliente</th><th>Procedimento</th></tr>"""
            for _, row in df_hoje.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding:10px; text-align:center'><b>{hora}</b></td><td>{row['cliente_nome']}</td><td>{row['procedimento_nome']}</td></tr>"
            tabela += "</table>"
            html = f"<h3>Agenda de Hoje ({hoje_br}):</h3>{tabela}"

        msg.attach(MIMEText(html, 'html'))

        # Envia
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro ao enviar e-mail: {e}"


# --- GATILHO AUTOMÁTICO (ROBÔ) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# --- MENU LATERAL ---
with st.sidebar:
    st.title("✨ Gestão Estética")
    menu = st.radio("NAVEGAÇÃO",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "Insights 🎂"])
    st.markdown("---")
    if st.button("🔄 Atualizar"): st.rerun()

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("Visão Geral")
    df_ag = get_data("agenda")
    hoje_str = date.today().strftime('%Y-%m-%d')
    hoje_qtd = len(df_ag[df_ag['data_agendamento'] == hoje_str]) if not df_ag.empty else 0

    c1, c2 = st.columns(2)
    c1.metric("Agendamentos Hoje", hoje_qtd)
    c2.metric("Data Atual", date.today().strftime('%d/%m/%Y'))

# 2. AGENDA
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["📅 Novo Agendamento", "📋 Visualizar"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")

    with t1:
        if df_cli.empty:
            st.warning("⚠️ Cadastre CLIENTES antes de agendar.")
        elif df_proc.empty:
            st.warning("⚠️ Cadastre PROCEDIMENTOS antes de agendar.")
        else:
            with st.form("form_ag"):
                c1, c2 = st.columns(2)
                with c1:
                    c_nome = st.selectbox("Cliente", df_cli['nome'].unique())
                    d_ag = st.date_input("Data", format="DD/MM/YYYY")
                with c2:
                    p_nome = st.selectbox("Procedimento", df_proc['nome'].unique())
                    h_ag = st.time_input("Hora")

                if st.form_submit_button("Agendar"):
                    cid = df_cli[df_cli['nome'] == c_nome]['id'].values[0]
                    pid = df_proc[df_proc['nome'] == p_nome]['id'].values[0]

                    dados = {
                        "cliente_id": int(cid), "cliente_nome": c_nome,
                        "procedimento_id": int(pid), "procedimento_nome": p_nome,
                        "data_agendamento": str(d_ag), "hora_agendamento": str(h_ag),
                        "status": "Agendado"
                    }
                    if add_data("agenda", dados):
                        st.success("Agendado!");
                        time.sleep(1);
                        st.rerun()

    with t2:
        df = get_data("agenda")
        if not df.empty:
            # Formata data para o Brasil na visualização
            if 'data_agendamento' in df.columns:
                df['data_br'] = pd.to_datetime(df['data_agendamento']).dt.strftime('%d/%m/%Y')
            st.dataframe(df[['data_br', 'hora_agendamento', 'cliente_nome', 'procedimento_nome']],
                         use_container_width=True)
            st.download_button("📥 Baixar Agenda (Excel)", data=converter_para_excel(df), file_name="agenda.xlsx")
        else:
            st.info("Agenda vazia.")

# 3. CLIENTES
elif menu == "Clientes":
    st.title("Gestão de Clientes")
    t1, t2 = st.tabs(["👤 Novo", "🗂️ Lista"])
    with t1:
        with st.form("form_cli"):
            nome = st.text_input("Nome")
            tel = st.text_input("Telefone")
            email = st.text_input("Email")
            nasc = st.date_input("Data Nascimento", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            anamnese = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                if nome:
                    dados = {"nome": nome, "telefone": tel, "email": email, "data_nascimento": str(nasc),
                             "anamnese": anamnese}
                    if add_data("clientes", dados): st.success("Salvo!"); time.sleep(1); st.rerun()
                else:
                    st.error("Nome obrigatório.")
    with t2:
        df = get_data("clientes")
        if not df.empty:
            if 'data_nascimento' in df.columns:
                df['nasc_br'] = pd.to_datetime(df['data_nascimento']).dt.strftime('%d/%m/%Y')
            st.dataframe(df[['nome', 'telefone', 'nasc_br']], use_container_width=True)
            c1, c2 = st.columns(2)
            c1.download_button("📥 Excel", data=converter_para_excel(df), file_name="clientes.xlsx")
            c2.download_button("📄 PDF", data=gerar_pdf(df, "Clientes"), file_name="clientes.pdf")

# 4. PROCEDIMENTOS
elif menu == "Procedimentos":
    st.title("Procedimentos")
    st.info("Cadastre aqui para aparecer na Agenda.")
    with st.form("form_proc"):
        n = st.text_input("Nome")
        v = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        d = st.number_input("Minutos", step=15, value=60)
        if st.form_submit_button("Salvar"):
            if add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d, "categoria": "Geral"}):
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
    st.dataframe(get_data("procedimentos"), use_container_width=True)

# 5. FINANCEIRO
elif menu == "Financeiro":
    st.title("Financeiro")
    t1, t2 = st.tabs(["💸 Lançar", "📊 Extrato"])
    with t1:
        with st.form("form_fin"):
            d = st.text_input("Descrição")
            v = st.number_input("Valor", min_value=0.0)
            dt = st.date_input("Data", format="DD/MM/YYYY")
            c = st.selectbox("Categoria", ["Geral", "Aluguel", "Produtos"])
            if st.form_submit_button("Lançar"):
                if add_data("despesas", {"descricao": d, "valor": v, "data_despesa": str(dt), "categoria": c}):
                    st.success("Lançado!");
                    time.sleep(1);
                    st.rerun()
    with t2:
        df = get_data("despesas")
        if not df.empty:
            df['data_br'] = pd.to_datetime(df['data_despesa']).dt.strftime('%d/%m/%Y')
            st.dataframe(df[['data_br', 'descricao', 'valor']], use_container_width=True)
            st.download_button("📥 Baixar Excel", data=converter_para_excel(df), file_name="financeiro.xlsx")

# 6. RELATÓRIOS
elif menu == "Relatórios":
    st.title("Relatórios")
    df_ag = get_data("agenda")
    if not df_ag.empty:
        st.download_button("📥 Baixar Relatório Completo", data=converter_para_excel(df_ag),
                           file_name="relatorio_geral.xlsx")
    else:
        st.info("Sem dados.")

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
            st.success(f"{len(aniv)} aniversariantes!")
            aniv['nasc_br'] = aniv['dt'].dt.strftime('%d/%m/%Y')
            st.dataframe(aniv[['nome', 'telefone', 'nasc_br']])
        else:
            st.info("Ninguém faz aniversário este mês.")