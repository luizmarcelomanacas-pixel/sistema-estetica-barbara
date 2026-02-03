import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DE E-MAIL ---
# Substitua pelos seus dados reais se não estiver usando st.secrets para email
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada", layout="wide", page_icon="✨")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet):
    try:
        return conn.read(worksheet=worksheet, ttl=0)
    except Exception:
        return pd.DataFrame()


def add_data(worksheet, new_data_dict):
    try:
        df = get_data(worksheet)
        if not df.empty and 'id' in df.columns:
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


# --- FUNÇÃO DE E-MAIL (RESTAURADA) ---
def enviar_agenda_email():
    try:
        hoje = str(date.today())
        df_agenda = get_data("agenda")

        # Filtra agenda de hoje
        if not df_agenda.empty and 'data_agendamento' in df_agenda.columns:
            # Garante que é string para comparar
            df_agenda['data_agendamento'] = df_agenda['data_agendamento'].astype(str)
            df_hoje = df_agenda[
                (df_agenda['data_agendamento'] == hoje) & (df_agenda['status'] == 'Agendado')].sort_values(
                'hora_agendamento')
        else:
            df_hoje = pd.DataFrame()

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

        # Conexão SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado!"
    except Exception as e:
        return f"❌ Erro ao enviar e-mail: {e}"


# --- GATILHO EXTERNO (ROBÔ GITHUB) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    res = enviar_agenda_email()
    st.write(res)
    st.stop()  # Para a execução aqui se for o robô

# --- SIDEBAR ---
with st.sidebar:
    st.title("✨ Gestão Estética")
    # MENU REORGANIZADO
    menu = st.radio("NAVEGAÇÃO",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "Insights 🎂"])
    st.markdown("---")
    if st.button("🔄 Atualizar Sistema"): st.rerun()

# --- PÁGINAS ---

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("Visão Geral")
    c1, c2, c3 = st.columns(3)

    df_ag = get_data("agenda")
    hoje = str(date.today())
    ag_hoje = 0
    if not df_ag.empty and 'data_agendamento' in df_ag.columns:
        ag_hoje = len(df_ag[df_ag['data_agendamento'].astype(str) == hoje])

    c1.metric("📅 Agendamentos Hoje", ag_hoje)
    c2.metric("✨ Data Atual", date.today().strftime('%d/%m/%Y'))
    c3.info("Sistema Conectado e Seguro 🔒")

# 2. AGENDA
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo Agendamento", "Visualizar Agenda"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")

    with t1:
        if not df_cli.empty and not df_proc.empty:
            with st.form("form_agenda"):
                # Ordena clientes alfabeticamente
                lista_clientes = sorted(df_cli['nome'].unique().tolist()) if 'nome' in df_cli.columns else []
                lista_procs = sorted(df_proc['nome'].unique().tolist()) if 'nome' in df_proc.columns else []

                c_nome = st.selectbox("Cliente", lista_clientes)
                p_nome = st.selectbox("Procedimento", lista_procs)
                d_ag = st.date_input("Data")
                h_ag = st.time_input("Hora")

                if st.form_submit_button("Agendar"):
                    # Pega IDs de forma segura
                    try:
                        c_id = df_cli[df_cli['nome'] == c_nome]['id'].values[0]
                        p_id = df_proc[df_proc['nome'] == p_nome]['id'].values[0]

                        dados = {
                            "cliente_id": int(c_id), "cliente_nome": c_nome,
                            "procedimento_id": int(p_id), "procedimento_nome": p_nome,
                            "data_agendamento": str(d_ag), "hora_agendamento": str(h_ag),
                            "status": "Agendado"
                        }
                        if add_data("agenda", dados):
                            st.success("Agendado!");
                            time.sleep(1);
                            st.rerun()
                    except:
                        st.error("Erro ao selecionar cliente/procedimento. Verifique os cadastros.")
        else:
            st.warning("Cadastre clientes e procedimentos primeiro.")

    with t2:
        df_ag = get_data("agenda")
        if not df_ag.empty:
            # Mostra colunas relevantes
            cols = ['data_agendamento', 'hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status']
            # Filtra colunas que realmente existem
            cols_existentes = [c for c in cols if c in df_ag.columns]
            st.dataframe(df_ag[cols_existentes], use_container_width=True)
        else:
            st.info("Nenhum agendamento encontrado.")

# 3. CLIENTES
elif menu == "Clientes":
    st.title("Gestão de Clientes")
    t1, t2 = st.tabs(["Cadastrar Novo", "Lista de Clientes"])

    with t1:
        with st.form("form_cli"):
            nome = st.text_input("Nome Completo")
            tel = st.text_input("Telefone")
            email = st.text_input("E-mail")
            nasc = st.date_input("Data de Nascimento", min_value=date(1920, 1, 1))
            anamnese = st.text_area("Anamnese / Observações")

            if st.form_submit_button("Salvar Cliente"):
                if nome:
                    dados = {
                        "nome": nome, "telefone": tel, "email": email,
                        "data_nascimento": str(nasc), "anamnese": anamnese,
                        "created_at": str(datetime.now())
                    }
                    if add_data("clientes", dados):
                        st.success("Cliente Salvo!");
                        time.sleep(1);
                        st.rerun()
                else:
                    st.error("Nome é obrigatório.")
    with t2:
        st.dataframe(get_data("clientes"), use_container_width=True)

# 4. PROCEDIMENTOS
elif menu == "Procedimentos":
    st.title("Procedimentos")
    with st.form("form_proc"):
        n = st.text_input("Nome");
        v = st.number_input("Valor", min_value=0.0);
        d = st.number_input("Minutos", step=15)
        if st.form_submit_button("Salvar"):
            if add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d, "categoria": "Geral"}):
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
    st.dataframe(get_data("procedimentos"), use_container_width=True)

# 5. FINANCEIRO
elif menu == "Financeiro":
    st.title("Financeiro")
    t1, t2 = st.tabs(["Lançar Despesa", "Extrato Geral"])

    with t1:
        with st.form("form_despesa"):
            desc = st.text_input("Descrição da Despesa")
            val = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            dt = st.date_input("Data do Pagamento")
            cat = st.selectbox("Categoria", ["Aluguel", "Produtos", "Marketing", "Impostos", "Outros"])

            if st.form_submit_button("Lançar Despesa"):
                if desc and val > 0:
                    dados = {
                        "descricao": desc, "valor": val, "data_despesa": str(dt),
                        "categoria": cat, "created_at": str(datetime.now())
                    }
                    if add_data("despesas", dados):
                        st.success("Despesa Lançada!");
                        time.sleep(1);
                        st.rerun()
    with t2:
        df_desp = get_data("despesas")
        if not df_desp.empty:
            st.dataframe(df_desp, use_container_width=True)
            if 'valor' in df_desp.columns:
                st.metric("Total de Despesas", f"R$ {df_desp['valor'].sum():.2f}")
        else:
            st.info("Nenhuma despesa lançada.")

# 6. RELATÓRIOS
elif menu == "Relatórios":
    st.title("Relatórios Gerenciais")

    df_ag = get_data("agenda")
    df_proc = get_data("procedimentos")
    df_desp = get_data("despesas")

    receita_total = 0.0
    despesa_total = 0.0

    # Receita
    if not df_ag.empty and not df_proc.empty and 'procedimento_id' in df_ag.columns:
        df_merged = pd.merge(df_ag, df_proc, left_on='procedimento_id', right_on='id', suffixes=('', '_proc'))
        if not df_merged.empty and 'valor' in df_merged.columns:
            receita_total = df_merged['valor'].sum()

    # Despesa
    if not df_desp.empty and 'valor' in df_desp.columns:
        despesa_total = df_desp['valor'].sum()

    lucro = receita_total - despesa_total

    c1, c2, c3 = st.columns(3)
    c1.metric("Entradas (Estimado)", f"R$ {receita_total:,.2f}")
    c2.metric("Saídas", f"R$ {despesa_total:,.2f}")
    c3.metric("Lucro Líquido", f"R$ {lucro:,.2f}", delta_color="normal")

# 7. INSIGHTS
elif menu == "Insights 🎂":
    st.title("Insights & Aniversariantes")
    df_cli = get_data("clientes")

    if not df_cli.empty and 'data_nascimento' in df_cli.columns:
        df_cli['nasc_dt'] = pd.to_datetime(df_cli['data_nascimento'], errors='coerce')
        mes_atual = date.today().month

        # Filtra (ignora datas inválidas)
        aniversariantes = df_cli[df_cli['nasc_dt'].dt.month == mes_atual]

        if not aniversariantes.empty:
            st.balloons()
            st.success(f"🎂 {len(aniversariantes)} Aniversariantes este mês!")
            st.dataframe(aniversariantes[['nome', 'telefone', 'data_nascimento']], use_container_width=True)
        else:
            st.info("Nenhum aniversariante neste mês.")