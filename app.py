import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.express as px
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Bárbara Castro Estética", layout="wide", page_icon="✨")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #D4AF37; text-align: center; font-weight: bold;}
    .metric-box {border: 1px solid #e6e6e6; padding: 20px; border-radius: 10px; background-color: #f9f9f9;}
    div[data-testid="stMetricValue"] {color: #D4AF37;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DE E-MAIL (PREENCHA AQUI) ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'

# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except:
    st.error("Erro de conexão. Verifique os Segredos.")
    st.stop()


# --- FUNÇÕES DE CRUD ---
def get_data(table):
    try:
        response = supabase.table(table).select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()


def add_data(table, data):
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False


def update_data(table, id_, data):
    try:
        supabase.table(table).update(data).eq("id", id_).execute()
        return True
    except:
        return False


def delete_data(table, id_):
    try:
        supabase.table(table).delete().eq("id", id_).execute()
        return True
    except:
        return False


# --- FUNÇÕES DE RELATÓRIO (PDF/EXCEL) ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()


def to_pdf(df, titulo):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Bárbara Castro Estética - {titulo}", ln=True, align='C')
    pdf.ln(5)

    # Cabeçalho dinâmico
    cols = df.columns[:6]
    pdf.set_font("Arial", size=10)
    col_width = 280 / len(cols)

    for col in cols:
        pdf.cell(col_width, 10, str(col).upper(), 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Arial", size=9)
    for i, row in df.iterrows():
        for col in cols:
            txt = str(row[col])[:25]
            pdf.cell(col_width, 10, txt, 1, 0, 'C')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')


# --- FUNÇÃO DE ENVIO DE E-MAIL (AGENDA DO DIA) ---
def enviar_agenda_email():
    try:
        # Busca agenda
        df_ag = get_data("agenda")
        hoje_bd = date.today().strftime('%Y-%m-%d')
        hoje_br = date.today().strftime('%d/%m/%Y')

        # Filtra dia atual
        df_hoje = pd.DataFrame()
        if not df_ag.empty and 'data_agendamento' in df_ag.columns:
            df_hoje = df_ag[df_ag['data_agendamento'] == hoje_bd].sort_values('hora_agendamento')

        # Monta E-mail
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda do Dia - {hoje_br}"

        if df_hoje.empty:
            html = f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #D4AF37;">Bom dia, Bárbara! ☀️</h2>
                <p>Sua agenda está livre para hoje ({hoje_br}). Aproveite para descansar ou adiantar tarefas!</p>
            </div>
            """
        else:
            tabela_html = """
            <table style='width:100%; border-collapse: collapse; font-family: Arial;'>
                <tr style='background-color: #D4AF37; color: white;'>
                    <th style='padding:12px; border: 1px solid #ddd;'>Hora</th>
                    <th style='padding:12px; border: 1px solid #ddd;'>Cliente</th>
                    <th style='padding:12px; border: 1px solid #ddd;'>Procedimento</th>
                    <th style='padding:12px; border: 1px solid #ddd;'>Status</th>
                </tr>
            """
            for _, row in df_hoje.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela_html += f"""
                <tr>
                    <td style='padding:10px; border: 1px solid #ddd; text-align:center'><b>{hora}</b></td>
                    <td style='padding:10px; border: 1px solid #ddd;'>{row['cliente_nome']}</td>
                    <td style='padding:10px; border: 1px solid #ddd;'>{row['procedimento_nome']}</td>
                    <td style='padding:10px; border: 1px solid #ddd;'>{row['status']}</td>
                </tr>
                """
            tabela_html += "</table>"

            html = f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #D4AF37;">Agenda de Hoje ({hoje_br}) ✨</h2>
                <p>Aqui estão seus atendimentos previstos:</p>
                {tabela_html}
                <br>
                <p><i>Sistema de Gestão - Bárbara Castro</i></p>
            </div>
            """

        msg.attach(MIMEText(html, 'html'))

        # Envia
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro ao enviar: {e}"


# --- GATILHO PARA ROBÔ (GITHUB ACTIONS) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# --- SIDEBAR (MENU LATERAL) ---
with st.sidebar:
    # FOTO (Troque o link abaixo pela sua foto real)
    st.image("Barbara.jpeg", width=150)
    st.markdown("### Bárbara Castro")
    st.markdown("Estética Avançada")
    st.markdown("---")

    menu = st.radio("MENU", [
        "📊 Dashboard",
        "📅 Agenda",
        "👥 Clientes",
        "💉 Procedimentos",
        "💰 Financeiro",
        "📑 Relatórios"
    ])
    st.markdown("---")

    # Botão de teste manual de e-mail
    if st.button("📧 Testar E-mail Agora"):
        res = enviar_agenda_email()
        if "Sucesso" in res:
            st.success(res)
        else:
            st.error(res)

    st.markdown("---")
    if st.button("🔄 Atualizar Dados"): st.rerun()

# ==============================================================================
# 1. DASHBOARD
# ==============================================================================
if menu == "📊 Dashboard":
    st.markdown("<div class='main-header'>Painel de Controle</div>", unsafe_allow_html=True)
    st.markdown("---")

    df_ag = get_data("agenda")
    df_fin = get_data("financeiro")

    hoje = date.today().strftime('%Y-%m-%d')
    ag_hoje = len(df_ag[df_ag['data_agendamento'] == hoje]) if not df_ag.empty else 0

    receita = df_fin[df_fin['tipo'] == 'Receita']['valor'].sum() if not df_fin.empty else 0
    despesa = df_fin[df_fin['tipo'] == 'Despesa']['valor'].sum() if not df_fin.empty else 0
    lucro = receita - despesa

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📅 Agenda Hoje", f"{ag_hoje} clientes")
    c2.metric("💰 Receita Total", f"R$ {receita:,.2f}")
    c3.metric("💸 Despesas", f"R$ {despesa:,.2f}")
    c4.metric("📈 Lucro Líquido", f"R$ {lucro:,.2f}", delta_color="normal")

    st.markdown("### 📊 Gráficos")
    if not df_fin.empty:
        fig = px.bar(df_fin, x='categoria', y='valor', color='tipo',
                     title="Fluxo Financeiro por Categoria", barmode='group',
                     color_discrete_map={'Receita': '#00CC96', 'Despesa': '#EF553B'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Cadastre receitas e despesas para ver os gráficos.")

# ==============================================================================
# 2. AGENDA
# ==============================================================================
elif menu == "📅 Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo", "Gerenciar"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")

    with t1:
        if df_cli.empty or df_proc.empty:
            st.warning("Cadastre Clientes e Procedimentos primeiro.")
        else:
            with st.form("nova_agenda"):
                c1, c2 = st.columns(2)
                cli = c1.selectbox("Cliente", df_cli['nome'].unique())
                proc = c2.selectbox("Procedimento", df_proc['nome'].unique())

                c3, c4 = st.columns(2)
                dt_ag = c3.date_input("Data", format="DD/MM/YYYY")
                hr_ag = c4.time_input("Hora")
                obs = st.text_area("Obs")

                if st.form_submit_button("Agendar"):
                    cid = df_cli[df_cli['nome'] == cli]['id'].values[0]
                    pid = df_proc[df_proc['nome'] == proc]['id'].values[0]
                    val = df_proc[df_proc['nome'] == proc]['valor'].values[0]

                    dados = {
                        "cliente_id": int(cid), "cliente_nome": cli,
                        "procedimento_id": int(pid), "procedimento_nome": proc,
                        "valor_cobrado": float(val), "data_agendamento": str(dt_ag),
                        "hora_agendamento": str(hr_ag), "status": "Agendado", "observacoes": obs
                    }
                    if add_data("agenda", dados):
                        st.success("Agendado!");
                        time.sleep(1);
                        st.rerun()

    with t2:
        df_ag = get_data("agenda")
        if not df_ag.empty:
            st.info("Edite o Status ou Valor diretamente na tabela.")
            df_edit = df_ag[
                ['id', 'data_agendamento', 'hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status',
                 'valor_cobrado']].copy()

            edited = st.data_editor(
                df_edit,
                column_config={
                    "status": st.column_config.SelectboxColumn("Status", options=["Agendado", "Concluído", "Cancelado"],
                                                               required=True),
                    "valor_cobrado": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
                },
                hide_index=True, use_container_width=True, key="ag_editor"
            )

            if st.button("💾 Salvar Alterações"):
                changes = 0
                for index, row in edited.iterrows():
                    orig = df_ag[df_ag['id'] == row['id']].iloc[0]
                    if row['status'] != orig['status'] or row['valor_cobrado'] != orig['valor_cobrado']:
                        update_data("agenda", int(row['id']),
                                    {"status": row['status'], "valor_cobrado": float(row['valor_cobrado'])})

                        if row['status'] == "Concluído" and orig['status'] != "Concluído":
                            fin_data = {
                                "descricao": f"Atendimento: {row['cliente_nome']}",
                                "valor": float(row['valor_cobrado']), "tipo": "Receita",
                                "categoria": "Atendimento", "data_movimento": str(date.today()),
                                "forma_pagamento": "Indefinido"
                            }
                            add_data("financeiro", fin_data)
                            st.toast(f"💰 R$ {row['valor_cobrado']} lançado no caixa!")
                        changes += 1
                if changes > 0: st.success("Atualizado!"); time.sleep(1); st.rerun()

# ==============================================================================
# 3. CLIENTES
# ==============================================================================
elif menu == "👥 Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Novo", "Lista"])

    with t1:
        with st.form("form_cli"):
            nome = st.text_input("Nome*")
            tel = st.text_input("Telefone")
            email = st.text_input("E-mail")
            nasc = st.date_input("Nascimento", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            anam = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                if nome:
                    add_data("clientes", {"nome": nome, "telefone": tel, "email": email, "data_nascimento": str(nasc),
                                          "anamnese": anam})
                    st.success("Salvo!");
                    time.sleep(1);
                    st.rerun()
                else:
                    st.error("Nome obrigatório.")

    with t2:
        df = get_data("clientes")
        if not df.empty:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.dataframe(df, use_container_width=True)
            with c2:
                to_del = st.selectbox("Excluir Cliente", df['nome'].unique())
                if st.button("🗑️ Confirmar"):
                    pid = df[df['nome'] == to_del]['id'].values[0]
                    delete_data("clientes", int(pid));
                    st.rerun()
            st.download_button("📥 Excel", to_excel(df), "clientes.xlsx")

# ==============================================================================
# 4. PROCEDIMENTOS
# ==============================================================================
elif menu == "💉 Procedimentos":
    st.title("Procedimentos")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("proc_form"):
            n = st.text_input("Nome");
            v = st.number_input("Valor", min_value=0.0);
            d = st.number_input("Minutos", value=30)
            cat = st.selectbox("Categoria", ["Facial", "Corporal", "Outros"])
            if st.form_submit_button("Salvar"):
                add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d, "categoria": cat})
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
    with c2:
        df = get_data("procedimentos")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            to_del = st.selectbox("Excluir", df['nome'].unique())
            if st.button("🗑️ Deletar"):
                pid = df[df['nome'] == to_del]['id'].values[0]
                delete_data("procedimentos", int(pid));
                st.rerun()

# ==============================================================================
# 5. FINANCEIRO
# ==============================================================================
elif menu == "💰 Financeiro":
    st.title("Financeiro")
    t1, t2 = st.tabs(["Lançamento", "Extrato"])

    with t1:
        with st.form("fin"):
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Tipo", ["Despesa", "Receita"])
            desc = c2.text_input("Descrição")
            val = c1.number_input("Valor", min_value=0.0)
            dt = c2.date_input("Data", format="DD/MM/YYYY")
            cat = c1.selectbox("Categoria", ["Atendimento", "Produtos", "Aluguel", "Outros"])
            pag = c2.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro"])
            if st.form_submit_button("Lançar"):
                add_data("financeiro",
                         {"descricao": desc, "valor": val, "tipo": tipo, "categoria": cat, "data_movimento": str(dt),
                          "forma_pagamento": pag})
                st.success("Lançado!");
                time.sleep(1);
                st.rerun()

    with t2:
        df = get_data("financeiro")
        if not df.empty:
            mes = st.slider("Filtrar Mês", 1, 12, date.today().month)
            df['dt'] = pd.to_datetime(df['data_movimento'])
            df_filtro = df[df['dt'].dt.month == mes]


            def color_row(val):
                return f'background-color: {"#d4edda" if val == "Receita" else "#f8d7da"}'


            st.dataframe(
                df_filtro[['data_movimento', 'tipo', 'descricao', 'valor']].style.map(color_row, subset=['tipo']),
                use_container_width=True)

            c1, c2 = st.columns(2)
            c1.download_button("📥 Excel", to_excel(df_filtro), "financeiro.xlsx")
            c2.download_button("📄 PDF", to_pdf(df_filtro, f"Mes {mes}"), "financeiro.pdf")

            to_del = st.number_input("ID para Excluir", min_value=0)
            if st.button("🗑️ Excluir por ID"):
                delete_data("financeiro", int(to_del));
                st.rerun()

# ==============================================================================
# 6. RELATÓRIOS
# ==============================================================================
elif menu == "📑 Relatórios":
    st.title("Relatórios")
    tipo = st.selectbox("Tipo", ["Faturamento", "Atendimentos"])
    d1 = st.date_input("Início", value=date.today().replace(day=1), format="DD/MM/YYYY")
    d2 = st.date_input("Fim", format="DD/MM/YYYY")

    if st.button("Gerar"):
        if tipo == "Faturamento":
            df = get_data("financeiro")
            if not df.empty:
                res = df[(df['data_movimento'] >= str(d1)) & (df['data_movimento'] <= str(d2))]
                st.dataframe(res)
                st.download_button("📥 Excel", to_excel(res), "fat.xlsx")
        elif tipo == "Atendimentos":
            df = get_data("agenda")
            if not df.empty:
                res = df[(df['data_agendamento'] >= str(d1)) & (df['data_agendamento'] <= str(d2))]
                st.dataframe(res)
                st.download_button("📥 Excel", to_excel(res), "atendimentos.xlsx")