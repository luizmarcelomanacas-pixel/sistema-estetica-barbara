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


# --- FUNÇÕES DE CRUD ---
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


# --- GERADOR DE PDF INDIVIDUAL (FICHA COMPLETA) ---
def gerar_ficha_individual(dados_cliente):
    pdf = FPDF()
    pdf.add_page()

    # 1. Logo (Tenta achar a foto)
    if os.path.exists("Barbara.jpeg"):
        pdf.image("Barbara.jpeg", x=10, y=8, w=30)
    elif os.path.exists("barbara.jpeg"):
        pdf.image("barbara.jpeg", x=10, y=8, w=30)

    # 2. Cabeçalho
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Ficha de Anamnese - Estética Avançada", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, "Bárbara Castro", ln=True, align='C')
    pdf.ln(20)  # Espaço

    # 3. Dados do Cliente
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "DADOS DO CLIENTE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Linha horizontal
    pdf.ln(5)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Nome: {dados_cliente['nome']}", ln=True)
    pdf.cell(0, 8, f"Telefone: {dados_cliente['telefone']}", ln=True)
    pdf.cell(0, 8, f"E-mail: {dados_cliente['email']}", ln=True)

    # Data formatada
    nasc = dados_cliente.get('data_nascimento', '')
    if nasc:
        try:
            d = datetime.strptime(nasc, '%Y-%m-%d').strftime('%d/%m/%Y')
            pdf.cell(0, 8, f"Data de Nascimento: {d}", ln=True)
        except:
            pdf.cell(0, 8, f"Data de Nascimento: {nasc}", ln=True)

    pdf.ln(10)

    # 4. Anamnese
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "HISTÓRICO / ANAMNESE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, txt=str(dados_cliente.get('anamnese', 'Nenhuma observação registrada.')))

    # 5. Assinatura no Rodapé
    pdf.ln(40)  # Espaço grande para descer
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, "________________________________________________________", ln=True, align='C')
    pdf.cell(0, 5, "Bárbara Castro - Estética Avançada", ln=True, align='C')
    pdf.cell(0, 5, f"Gerado em: {date.today().strftime('%d/%m/%Y')}", ln=True, align='C')

    return pdf.output(dest='S').encode('latin-1')


# --- GERADOR DE RELATÓRIO GERAL (EXCEL) ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()


# --- FUNÇÃO E-MAIL ---
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
        return f"❌ Erro ao enviar: {e}"


# --- GATILHO ROBÔ ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=150)
    elif os.path.exists("barbara.jpeg"):
        st.image("barbara.jpeg", width=150)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)

    st.markdown("### Bárbara Castro")
    st.markdown("Estética Avançada")
    st.markdown("---")
    menu = st.radio("MENU",
                    ["📊 Dashboard", "📅 Agenda", "👥 Clientes", "💉 Procedimentos", "💰 Financeiro", "📑 Relatórios"])
    st.markdown("---")
    if st.button("📧 Testar E-mail"):
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

# ==============================================================================
# 2. AGENDA
# ==============================================================================
elif menu == "📅 Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo Agendamento", "Gerenciar Agenda"])

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
                dt_ag = c3.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
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
            st.info("⚠️ Para lançar no caixa, mude para **Concluído** e Salve.")
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
                                "categoria": "Atendimento", "data_movimento": str(data_hoje_br()),
                                "forma_pagamento": "Indefinido"
                            }
                            add_data("financeiro", fin_data)
                            st.toast(f"💰 Receita lançada!", icon="✅")
                        changes += 1
                if changes > 0: st.success("Salvo!"); time.sleep(1); st.rerun()

            st.divider()
            c1, c2 = st.columns([3, 1])
            with c1:
                item_del = st.selectbox("Excluir Agendamento:", df_ag.apply(
                    lambda x: f"ID {x['id']}: {x['data_agendamento']} - {x['cliente_nome']}", axis=1))
            with c2:
                st.write("");
                st.write("")
                if st.button("🗑️ Apagar"):
                    id_real = int(item_del.split(":")[0].replace("ID ", ""))
                    delete_data("agenda", id_real);
                    st.rerun()
        else:
            st.info("Vazia.")

# ==============================================================================
# 3. CLIENTES (TOTALMENTE RENOVADO)
# ==============================================================================
elif menu == "👥 Clientes":
    st.title("Gestão de Clientes")

    # Opção Principal
    modo = st.radio("O que você deseja fazer?", ["👤 Cadastrar Novo Cliente", "🔍 Pesquisar / Editar / Ficha"],
                    horizontal=True)
    st.markdown("---")

    # MODO 1: CADASTRAR NOVO
    if modo == "👤 Cadastrar Novo Cliente":
        st.subheader("Novo Cadastro")
        with st.form("form_cli_novo"):
            nome = st.text_input("Nome Completo*")
            tel = st.text_input("Telefone (WhatsApp)")
            email = st.text_input("E-mail")
            nasc = st.date_input("Data de Nascimento", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            anam = st.text_area("Ficha de Anamnese / Observações")

            if st.form_submit_button("💾 Salvar Novo Cliente"):
                if nome:
                    add_data("clientes", {"nome": nome, "telefone": tel, "email": email, "data_nascimento": str(nasc),
                                          "anamnese": anam})
                    st.success(f"Cliente {nome} cadastrado com sucesso!");
                    time.sleep(1);
                    st.rerun()
                else:
                    st.error("O nome é obrigatório.")

    # MODO 2: PESQUISAR E EDITAR (A PEDIDO: MESMA TELA)
    else:
        df = get_data("clientes")
        if df.empty:
            st.warning("Nenhum cliente cadastrado ainda.")
        else:
            # Seleção do Cliente
            lista_nomes = df['nome'].unique()
            cliente_sel = st.selectbox("📂 Selecione o Cliente para gerenciar:", lista_nomes)

            # Pega os dados do cliente selecionado
            dados = df[df['nome'] == cliente_sel].iloc[0]
            id_cli = int(dados['id'])

            # Formulário Preenchido (Para Editar)
            st.subheader(f"Editando: {cliente_sel}")
            with st.form("form_cli_edit"):
                # Campos vêm preenchidos com o 'value' atual
                novo_nome = st.text_input("Nome", value=dados['nome'])
                novo_tel = st.text_input("Telefone", value=dados['telefone'])
                novo_email = st.text_input("E-mail", value=dados['email'])

                # Tratamento de data para não dar erro se estiver vazia
                try:
                    data_atual = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
                except:
                    data_atual = date.today()

                novo_nasc = st.date_input("Data de Nascimento", value=data_atual, format="DD/MM/YYYY")
                nova_anam = st.text_area("Anamnese", value=dados['anamnese'], height=150)

                # Botões lado a lado
                c1, c2, c3 = st.columns([1, 1, 1])

                with c1:
                    if st.form_submit_button("💾 Salvar Alterações"):
                        update_data("clientes", id_cli, {
                            "nome": novo_nome, "telefone": novo_tel,
                            "email": novo_email, "data_nascimento": str(novo_nasc),
                            "anamnese": nova_anam
                        })
                        st.success("Dados atualizados!");
                        time.sleep(1);
                        st.rerun()

            # Ações Extras fora do Form (para não submeter o form ao clicar)
            c_pdf, c_del = st.columns([1, 1])

            with c_pdf:
                # Botão de PDF Individual
                pdf_bytes = gerar_ficha_individual(dados)
                st.download_button(
                    label="📄 Baixar Ficha Completa (PDF)",
                    data=pdf_bytes,
                    file_name=f"Ficha_{cliente_sel}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            with c_del:
                # Botão de Excluir com confirmação
                with st.expander("🗑️ Zona de Perigo (Excluir)"):
                    st.write("Tem certeza? Isso apaga o cliente para sempre.")
                    if st.button("Confirmar Exclusão do Cliente", type="primary"):
                        delete_data("clientes", id_cli)
                        st.success("Cliente apagado.");
                        time.sleep(1);
                        st.rerun()

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
            dt = c2.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
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
            mes = st.slider("Mês", 1, 12, data_hoje_br().month)
            df['dt'] = pd.to_datetime(df['data_movimento'])
            df_filtro = df[df['dt'].dt.month == mes]


            def color_row(val):
                return f'background-color: {"#d4edda" if val == "Receita" else "#f8d7da"}'


            st.dataframe(
                df_filtro[['id', 'data_movimento', 'tipo', 'descricao', 'valor']].style.map(color_row, subset=['tipo']),
                use_container_width=True)

            c1, c2 = st.columns(2)
            c1.download_button("📥 Excel", to_excel(df_filtro), "financeiro.xlsx")

            st.divider()
            c_del1, c_del2 = st.columns([3, 1])
            with c_del1:
                item_fin = st.selectbox("Excluir item:", df_filtro.apply(
                    lambda x: f"ID {x['id']}: {x['tipo']} - R$ {x['valor']} ({x['descricao']})", axis=1))
            with c_del2:
                st.write("");
                st.write("")
                if st.button("🗑️ Apagar"):
                    id_real = int(item_fin.split(":")[0].replace("ID ", ""))
                    delete_data("financeiro", id_real);
                    st.rerun()

# ==============================================================================
# 6. RELATÓRIOS
# ==============================================================================
elif menu == "📑 Relatórios":
    st.title("Relatórios Gerais")
    tipo = st.selectbox("Tipo", ["Faturamento", "Atendimentos"])
    d1 = st.date_input("Início", value=data_hoje_br().replace(day=1), format="DD/MM/YYYY")
    d2 = st.date_input("Fim", value=data_hoje_br(), format="DD/MM/YYYY")

    if st.button("Gerar Tabela"):
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