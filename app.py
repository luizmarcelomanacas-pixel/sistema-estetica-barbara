import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.express as px
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Bárbara Castro Estética", layout="wide", page_icon="✨")

# --- SISTEMA DE LOGIN (O PORTEIRO) ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False


def check_login():
    st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Sistema de Gestão - Bárbara Castro</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar no Sistema", type="primary")

            if submit:
                # Verifica se as credenciais batem com o secrets.toml
                try:
                    segredo_user = st.secrets["admin"]["usuario"]
                    segredo_pass = st.secrets["admin"]["senha"]

                    if user == segredo_user and password == segredo_pass:
                        st.session_state["logado"] = True
                        st.success("Login realizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception:
                    st.error("Erro: Configure [admin] no secrets.toml")


# Se não estiver logado, mostra o login e PARA O CÓDIGO AQUI
if not st.session_state["logado"]:
    check_login()
    st.stop()  # 🛑 NADA ABAIXO DAQUI RODA SE NÃO TIVER LOGADO

# ==============================================================================
# DAQUI PARA BAIXO É O SISTEMA COMPLETO (SÓ CARREGA SE LOGADO)
# ==============================================================================

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #D4AF37; text-align: center; font-weight: bold;}
    .metric-box {border: 1px solid #e6e6e6; padding: 20px; border-radius: 10px; background-color: #f9f9f9;}
    div[data-testid="stMetricValue"] {color: #D4AF37;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DE E-MAIL ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


# --- FUNÇÃO DATA BRASIL ---
def data_hoje_br():
    return (datetime.utcnow() - timedelta(hours=3)).date()


# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except:
    st.error("Erro de conexão. Verifique os Segredos no Streamlit.")
    st.stop()


# --- FUNÇÕES ÚTEIS ---
def limpar_telefone(telefone):
    if not telefone: return ""
    nums = ''.join(filter(str.isdigit, str(telefone)))
    return nums


def get_data(table):
    try:
        response = supabase.table(table).select("*").order("id").execute()
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
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False


def delete_data(table, id_):
    try:
        supabase.table(table).delete().eq("id", id_).execute()
        return True
    except:
        return False


# --- GERADOR DE PDF ---
def gerar_ficha_individual(dados_cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "Bárbara Castro Estética Avançada", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, "Ficha de Anamnese e Histórico", ln=True, align='C')
    pdf.ln(15)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "DADOS DO CLIENTE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Nome: {dados_cliente['nome']}", ln=True)
    pdf.cell(0, 8, f"Telefone: {dados_cliente['telefone']}", ln=True)
    pdf.cell(0, 8, f"E-mail: {dados_cliente['email']}", ln=True)

    nasc = dados_cliente.get('data_nascimento', '')
    if nasc:
        try:
            d = datetime.strptime(nasc, '%Y-%m-%d').strftime('%d/%m/%Y')
            pdf.cell(0, 8, f"Data de Nascimento: {d}", ln=True)
        except:
            pass
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "HISTÓRICO / ANAMNESE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, txt=str(dados_cliente.get('anamnese', 'Nenhuma observação.')))

    pdf.ln(40)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, "________________________________________________________", ln=True, align='C')
    pdf.cell(0, 5, "Bárbara Castro - Estética Avançada", ln=True, align='C')
    pdf.cell(0, 5, f"Gerado em: {date.today().strftime('%d/%m/%Y')}", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')


def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()


def enviar_agenda_email():
    try:
        df_ag = get_data("agenda")
        hoje_bd = str(data_hoje_br())
        hoje_br = data_hoje_br().strftime('%d/%m/%Y')
        df_hoje = pd.DataFrame()
        if not df_ag.empty and 'data_agendamento' in df_ag.columns:
            df_hoje = df_ag[df_ag['data_agendamento'] == hoje_bd].sort_values('hora_agendamento')

        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda do Dia - {hoje_br}"

        if df_hoje.empty:
            html = f"""<h2 style="color: #D4AF37;">Bom dia! ☀️</h2><p>Agenda livre para hoje ({hoje_br}).</p>"""
        else:
            tabela_html = """<table style='width:100%; border-collapse: collapse; font-family: Arial;'>
                <tr style='background-color: #D4AF37; color: white;'>
                    <th style='padding:12px;'>Hora</th><th>Cliente</th><th>Procedimento</th><th>Status</th></tr>"""
            for _, row in df_hoje.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela_html += f"""<tr><td style='padding:10px; border: 1px solid #ddd;'><b>{hora}</b></td>
                    <td style='padding:10px; border: 1px solid #ddd;'>{row['cliente_nome']}</td>
                    <td style='padding:10px; border: 1px solid #ddd;'>{row['procedimento_nome']}</td>
                    <td style='padding:10px; border: 1px solid #ddd;'>{row['status']}</td></tr>"""
            tabela_html += "</table>"
            html = f"""<h2 style="color: #D4AF37;">Agenda de Hoje ({hoje_br}) ✨</h2>{tabela_html}"""

        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro: {e}"


if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# --- MENU LATERAL (SÓ APARECE SE LOGADO) ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=150)
    elif os.path.exists("barbara.jpeg"):
        st.image("barbara.jpeg", width=150)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)

    st.markdown("### Bárbara Castro")
    st.markdown("Estética Avançada")

    # Botão de Logout
    if st.button("🚪 Sair do Sistema"):
        st.session_state["logado"] = False
        st.rerun()

    st.markdown("---")
    menu = st.radio("MENU", ["📊 Dashboard", "📅 Agenda", "👥 Clientes", "💉 Procedimentos", "💰 Financeiro", "📑 Relatórios",
                             "🎂 Insights (Aniversários)"])
    st.markdown("---")
    if st.button("📧 Testar E-mail"):
        res = enviar_agenda_email()
        if "Sucesso" in res:
            st.success(res)
        else:
            st.error(res)
    st.markdown("---")
    if st.button("🔄 Atualizar Dados"): st.rerun()

# --- CONTEÚDO PRINCIPAL ---

if menu == "📊 Dashboard":
    st.markdown("<div class='main-header'>Painel de Controle</div>", unsafe_allow_html=True)
    st.markdown("---")
    df_ag = get_data("agenda")
    df_fin = get_data("financeiro")
    hoje = str(data_hoje_br())
    ag_hoje = len(df_ag[df_ag['data_agendamento'] == hoje]) if not df_ag.empty else 0
    receita = df_fin[df_fin['tipo'] == 'Receita']['valor'].sum() if not df_fin.empty else 0
    despesa = df_fin[df_fin['tipo'] == 'Despesa']['valor'].sum() if not df_fin.empty else 0
    lucro = receita - despesa

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📅 Agenda Hoje", f"{ag_hoje}")
    c2.metric("💰 Receita Total", f"R$ {receita:,.2f}")
    c3.metric("💸 Despesas", f"R$ {despesa:,.2f}")
    c4.metric("📈 Lucro Líquido", f"R$ {lucro:,.2f}")

    if not df_fin.empty:
        st.markdown("### 📊 Fluxo de Caixa")
        fig = px.bar(df_fin, x='categoria', y='valor', color='tipo', barmode='group',
                     color_discrete_map={'Receita': '#00CC96', 'Despesa': '#EF553B'})
        st.plotly_chart(fig, use_container_width=True)

elif menu == "📅 Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo", "Gerenciar"])
    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")
    with t1:
        if df_cli.empty or df_proc.empty:
            st.warning("Cadastre clientes/procedimentos.")
        else:
            with st.form("nova_agenda"):
                c1, c2 = st.columns(2)
                cli = c1.selectbox("Cliente", df_cli['nome'].unique())
                proc = c2.selectbox("Procedimento", df_proc['nome'].unique())
                c3, c4 = st.columns(2)
                dt_ag = c3.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
                hr_ag = c4.time_input("Hora")
                obs = st.text_area("Obs")
                if st.form_submit_button("Agendar"):
                    cid = df_cli[df_cli['nome'] == cli]['id'].values[0]
                    pid = df_proc[df_proc['nome'] == proc]['id'].values[0]
                    val = df_proc[df_proc['nome'] == proc]['valor'].values[0]
                    add_data("agenda", {"cliente_id": int(cid), "cliente_nome": cli, "procedimento_id": int(pid),
                                        "procedimento_nome": proc, "valor_cobrado": float(val),
                                        "data_agendamento": str(dt_ag), "hora_agendamento": str(hr_ag),
                                        "status": "Agendado", "observacoes": obs})
                    st.success("Agendado!");
                    time.sleep(1);
                    st.rerun()
    with t2:
        df_ag = get_data("agenda")
        if not df_ag.empty:
            st.info("Para ir pro caixa, marque como **Concluído** e salve.")
            edited = st.data_editor(df_ag[['id', 'data_agendamento', 'hora_agendamento', 'cliente_nome',
                                           'procedimento_nome', 'status', 'valor_cobrado']], column_config={
                "status": st.column_config.SelectboxColumn("Status", options=["Agendado", "Concluído", "Cancelado"],
                                                           required=True)}, hide_index=True, use_container_width=True,
                                    key="ag_ed")
            if st.button("💾 Salvar Alterações"):
                for i, row in edited.iterrows():
                    orig = df_ag[df_ag['id'] == row['id']].iloc[0]
                    if row['status'] != orig['status'] or row['valor_cobrado'] != orig['valor_cobrado']:
                        update_data("agenda", int(row['id']),
                                    {"status": row['status'], "valor_cobrado": float(row['valor_cobrado'])})
                        if row['status'] == "Concluído" and orig['status'] != "Concluído":
                            add_data("financeiro", {"descricao": f"Atendimento: {row['cliente_nome']}",
                                                    "valor": float(row['valor_cobrado']), "tipo": "Receita",
                                                    "categoria": "Atendimento", "data_movimento": str(data_hoje_br()),
                                                    "forma_pagamento": "Indefinido"})
                            st.toast("💰 Receita lançada!");
                            time.sleep(1)
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
            st.divider()
            item = st.selectbox("Excluir Agendamento:",
                                df_ag.apply(lambda x: f"ID {x['id']}: {x['cliente_nome']}", axis=1))
            if st.button("🗑️ Apagar"): delete_data("agenda", int(item.split(":")[0].replace("ID ", ""))); st.rerun()

elif menu == "👥 Clientes":
    st.title("Gestão de Clientes")
    modo = st.radio("Ação:", ["👤 Cadastrar", "🔍 Editar / Ficha"], horizontal=True)
    st.markdown("---")
    if modo == "👤 Cadastrar":
        with st.form("form_cli_novo"):
            nome = st.text_input("Nome*")
            tel = st.text_input("Zap")
            email = st.text_input("Email")
            nasc = st.date_input("Nascimento", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            anam = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                if nome:
                    add_data("clientes", {"nome": nome, "telefone": tel, "email": email, "data_nascimento": str(nasc),
                                          "anamnese": anam})
                    st.success("Cadastrado!");
                    time.sleep(1);
                    st.rerun()
                else:
                    st.error("Nome obrigatório.")
    else:
        df = get_data("clientes")
        if not df.empty:
            sel = st.selectbox("Selecione:", df['nome'].unique())
            dados = df[df['nome'] == sel].iloc[0]
            st.subheader(f"Editando: {sel}")
            with st.form("ed_cli"):
                nn = st.text_input("Nome", value=dados['nome'])
                nt = st.text_input("Zap", value=dados['telefone'])
                ne = st.text_input("Email", value=dados['email'])
                try:
                    da = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
                except:
                    da = date.today()
                nna = st.date_input("Nascimento", value=da, format="DD/MM/YYYY")
                nan = st.text_area("Anamnese", value=dados['anamnese'])
                if st.form_submit_button("💾 Salvar"):
                    update_data("clientes", int(dados['id']),
                                {"nome": nn, "telefone": nt, "email": ne, "data_nascimento": str(nna), "anamnese": nan})
                    st.success("Atualizado!");
                    time.sleep(1);
                    st.rerun()
            c1, c2 = st.columns(2)
            c1.download_button("📄 Baixar Ficha PDF", data=gerar_ficha_individual(dados), file_name=f"Ficha_{sel}.pdf",
                               mime="application/pdf")
            with c2:
                with st.expander("🗑️ Excluir"):
                    if st.button("Confirmar Exclusão", type="primary"): delete_data("clientes",
                                                                                    int(dados['id'])); st.rerun()

elif menu == "💉 Procedimentos":
    st.title("Procedimentos")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("pf"):
            n = st.text_input("Nome");
            v = st.number_input("R$", min_value=0.0);
            d = st.number_input("Min", value=30)
            if st.form_submit_button("Salvar"): add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d,
                                                                           "categoria": "Geral"}); st.rerun()
    with c2:
        df = get_data("procedimentos")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            dele = st.selectbox("Excluir:", df['nome'].unique())
            if st.button("🗑️ Deletar"): delete_data("procedimentos",
                                                    int(df[df['nome'] == dele]['id'].values[0])); st.rerun()

elif menu == "💰 Financeiro":
    st.title("Financeiro")
    t1, t2 = st.tabs(["Lançar", "Extrato"])
    with t1:
        with st.form("ff"):
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            desc = st.text_input("Descrição")
            val = st.number_input("Valor")
            dt = st.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
            cat = st.selectbox("Categoria", ["Atendimento", "Produto", "Custo Fixo", "Outros"])
            if st.form_submit_button("Lançar"): add_data("financeiro", {"descricao": desc, "valor": val, "tipo": tipo,
                                                                        "categoria": cat, "data_movimento": str(dt),
                                                                        "forma_pagamento": "Dinheiro"}); st.success(
                "Ok!"); st.rerun()
    with t2:
        df = get_data("financeiro")
        if not df.empty:
            mes = st.slider("Mês", 1, 12, data_hoje_br().month)
            df['d'] = pd.to_datetime(df['data_movimento'])
            res = df[df['d'].dt.month == mes]
            st.dataframe(res[['id', 'data_movimento', 'tipo', 'descricao', 'valor']], use_container_width=True)
            st.download_button("📥 Excel", to_excel(res), "fin.xlsx")
            st.divider()
            idel = st.number_input("ID para excluir:", min_value=0)
            if st.button("🗑️ Excluir Item"): delete_data("financeiro", int(idel)); st.rerun()

elif menu == "📑 Relatórios":
    st.title("Relatórios")
    d1 = st.date_input("Início", value=data_hoje_br().replace(day=1), format="DD/MM/YYYY")
    d2 = st.date_input("Fim", value=data_hoje_br(), format="DD/MM/YYYY")
    if st.button("Gerar Faturamento"):
        df = get_data("financeiro")
        if not df.empty:
            res = df[(df['data_movimento'] >= str(d1)) & (df['data_movimento'] <= str(d2))]
            st.dataframe(res)
            st.download_button("📥 Baixar Excel", to_excel(res), "faturamento.xlsx")

elif menu == "🎂 Insights (Aniversários)":
    st.title("🎂 Aniversariantes do Mês")
    st.markdown("Aqui você vê quem faz aniversário este mês e já pode mandar um 'Parabéns' no WhatsApp!")
    df = get_data("clientes")
    if not df.empty:
        meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho",
                    8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        mes_atual = data_hoje_br().month
        nome_mes = meses_pt[mes_atual]
        df['dt_obj'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
        aniversariantes = df[df['dt_obj'].dt.month == mes_atual].sort_values(by="dt_obj")
        if not aniversariantes.empty:
            st.balloons()
            st.success(f"Temos {len(aniversariantes)} aniversariantes em {nome_mes}! 🎉")
            for index, row in aniversariantes.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.markdown(f"**Dia {row['dt_obj'].day}:** {row['nome']}")
                    c2.markdown(f"📞 {row['telefone']}")
                    if row['telefone']:
                        link_zap = f"https://wa.me/55{limpar_telefone(row['telefone'])}?text=Olá {row['nome']}! Parabéns! 🎉"
                        c3.link_button("🎁 Enviar Zap", link_zap)
                    else:
                        c3.write("Sem nº")
        else:
            st.info(f"Nenhum aniversariante em {nome_mes}.")
    else:
        st.warning("Cadastre clientes para ver os aniversariantes.")