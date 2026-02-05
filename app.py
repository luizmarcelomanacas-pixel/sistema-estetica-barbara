import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from supabase import create_client, Client
from streamlit_calendar import calendar

# ==============================================================================
# 1. CONFIGURAÇÕES INICIAIS E SEGURANÇA
# ==============================================================================
st.set_page_config(page_title="Bárbara Castro Estética", layout="wide", page_icon="✨")

# --- CSS PERSONALIZADO (Visual) ---
st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #D4AF37; text-align: center; font-weight: bold;}
    .metric-box {border: 1px solid #e6e6e6; padding: 20px; border-radius: 10px; background-color: #f9f9f9;}
    div[data-testid="stMetricValue"] {color: #D4AF37;}
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN (Proteção) ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False


def check_login():
    st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                try:
                    # Verifica se as senhas batem
                    if user == st.secrets["admin"]["usuario"] and password == st.secrets["admin"]["senha"]:
                        st.session_state["logado"] = True
                        st.toast("Login realizado com sucesso!", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception:
                    st.error("Erro Crítico: Configure o arquivo secrets.toml.")


if not st.session_state["logado"]:
    check_login()
    st.stop()  # Para a execução aqui se não estiver logado

# ==============================================================================
# 2. CONEXÃO COM BANCO DE DADOS E CONFIGURAÇÕES
# ==============================================================================

# Configurações de E-mail
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


# Função Data Brasil (UTC-3)
def data_hoje_br():
    return (datetime.utcnow() - timedelta(hours=3)).date()


# Conexão Supabase Segura
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar no Supabase: {e}")
        return None


supabase = init_supabase()


# ==============================================================================
# 3. FUNÇÕES CRUD (CRIAR, LER, ATUALIZAR, DELETAR)
# ==============================================================================

def get_data(table):
    """Busca dados de forma segura, retornando DataFrame vazio se der erro"""
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table(table).select("*").order("id").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()


def add_data(table, data):
    """Adiciona dados e retorna True/False"""
    if not supabase: return False
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def update_data(table, id_, data):
    """Atualiza dados"""
    if not supabase: return False
    try:
        supabase.table(table).update(data).eq("id", id_).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False


def delete_data(table, id_):
    """Remove dados"""
    if not supabase: return False
    try:
        supabase.table(table).delete().eq("id", id_).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False


def limpar_telefone(telefone):
    if not telefone: return ""
    return ''.join(filter(str.isdigit, str(telefone)))


# ==============================================================================
# 4. GERADORES (PDF, EXCEL, EMAIL)
# ==============================================================================

def gerar_ficha_individual(dados_cliente):
    pdf = FPDF()
    pdf.add_page()

    # Cabeçalho
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "Bárbara Castro Estética Avançada".encode('latin-1', 'replace').decode('latin-1'), ln=True,
             align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, "Ficha de Anamnese".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(15)

    # Dados Pessoais
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "DADOS DO CLIENTE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Arial", size=12)
    nome = str(dados_cliente['nome']).encode('latin-1', 'replace').decode('latin-1')
    email = str(dados_cliente['email']).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 8, f"Nome: {nome}", ln=True)
    pdf.cell(0, 8, f"Telefone: {dados_cliente['telefone']}", ln=True)
    pdf.cell(0, 8, f"E-mail: {email}", ln=True)

    # Data Nascimento
    nasc = dados_cliente.get('data_nascimento', '')
    if nasc:
        try:
            d = datetime.strptime(nasc, '%Y-%m-%d').strftime('%d/%m/%Y')
            pdf.cell(0, 8, f"Data de Nascimento: {d}", ln=True)
        except:
            pass
    pdf.ln(10)

    # Anamnese
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "HISTÓRICO / ANAMNESE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    texto_anamnese = str(dados_cliente.get('anamnese', 'Nenhuma observação.')).encode('latin-1', 'replace').decode(
        'latin-1')
    pdf.multi_cell(0, 8, txt=texto_anamnese)

    # Assinatura
    pdf.ln(40)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, "________________________________________________________", ln=True, align='C')
    pdf.cell(0, 5, "Bárbara Castro - Estética Avançada".encode('latin-1', 'replace').decode('latin-1'), ln=True,
             align='C')
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
            df_hoje = df_ag[df_ag['data_agendamento'] == hoje_bd]

        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"Agenda do Dia - {hoje_br}"

        html = f"<h2>Resumo da Agenda - {hoje_br}</h2>"
        if df_hoje.empty:
            html += "<p>Agenda livre hoje.</p>"
        else:
            html += df_hoje[['hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status']].to_html()

        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro ao enviar: {e}"


# Gatilho Robô (para automação futura)
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email())
    st.stop()

# ==============================================================================
# 5. INTERFACE DO USUÁRIO (SIDEBAR E MENUS)
# ==============================================================================

with st.sidebar:
    # Tenta carregar imagem com segurança
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=150)
    elif os.path.exists("barbara.jpeg"):
        st.image("barbara.jpeg", width=150)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)

    # --- NOME ATUALIZADO ---
    st.markdown("### Barbara Castro Saúde & Estética integrativa")

    # Botão de Sair
    if st.button("🚪 Sair", type="secondary"):
        st.session_state["logado"] = False
        st.rerun()

    st.markdown("---")
    menu = st.radio("MENU", ["📊 Dashboard", "📅 Agenda", "👥 Clientes", "💉 Procedimentos", "💰 Financeiro", "📑 Relatórios",
                             "🎂 Insights"])
    st.markdown("---")

    # --- BOTÕES DE AÇÃO ---
    if st.button("🔄 Atualizar"): st.rerun()

    if st.button("📧 Enviar Agenda Email"):
        with st.spinner("Enviando..."):
            retorno = enviar_agenda_email()
            if "Erro" in retorno:
                st.error(retorno)
            else:
                st.success(retorno)

# --- PÁGINA: DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown("<div class='main-header'>Painel de Controle</div>", unsafe_allow_html=True)

    df_ag = get_data("agenda")
    df_fin = get_data("financeiro")
    hj = str(data_hoje_br())

    # Filtros de Data
    data_atual = data_hoje_br()
    mes_atual = data_atual.month
    ano_atual = data_atual.year
    nome_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                  7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

    # 1. KPI Agenda (Dia)
    ag = 0
    if not df_ag.empty and 'data_agendamento' in df_ag.columns:
        ag = len(df_ag[df_ag['data_agendamento'] == hj])

    # 2. KPI Financeiro (Mês Atual)
    rec, des = 0.0, 0.0
    if not df_fin.empty and 'data_movimento' in df_fin.columns:
        df_fin['dt_obj'] = pd.to_datetime(df_fin['data_movimento'], errors='coerce')
        df_mes = df_fin[
            (df_fin['dt_obj'].dt.month == mes_atual) &
            (df_fin['dt_obj'].dt.year == ano_atual)
            ]
        rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
        des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()

    lucro = rec - des

    # Exibição dos Cards
    st.markdown(f"### 🗓️ Visão Mensal: {nome_meses[mes_atual]} / {ano_atual}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agenda Hoje", ag)
    c2.metric("Receita (Mês)", f"R$ {rec:,.2f}")
    c3.metric("Despesas (Mês)", f"R$ {des:,.2f}")
    c4.metric("Lucro Líquido", f"R$ {lucro:,.2f}")

    st.markdown("---")

    # Lista de Contas a Pagar (HOJE)
    st.subheader("🛑 Contas a Pagar (HOJE)")
    if not df_fin.empty:
        hoje_dt = pd.to_datetime(data_hoje_br())
        # Filtro seguro
        df_fin['dt_obj'] = pd.to_datetime(df_fin['data_movimento'], errors='coerce')
        mask = (df_fin['tipo'] == 'Despesa') & (df_fin['dt_obj'] == hoje_dt)
        df_vencendo = df_fin[mask].sort_values('dt_obj')

        if not df_vencendo.empty:
            for i, row in df_vencendo.iterrows():
                st.error(f"💸 **Vence Hoje:** {row['descricao']} — **R$ {row['valor']:,.2f}**")
        else:
            st.success("Tudo pago! Nenhuma despesa vence hoje. ✅")
    else:
        st.info("Nenhum registro financeiro encontrado.")

# --- PÁGINA: AGENDA ---
elif menu == "📅 Agenda":
    st.title("Agenda")
    t_cal, t_lista, t_novo = st.tabs(["📅 Calendário Visual", "📝 Lista & Edição", "➕ Novo Agendamento"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")
    df_ag = get_data("agenda")

    # Aba 1: Calendário
    with t_cal:
        if not df_ag.empty:
            events = []
            for i, row in df_ag.iterrows():
                cor = "#3788d8"  # Azul
                if row['status'] == "Concluído":
                    cor = "#28a745"
                elif row['status'] == "Cancelado":
                    cor = "#dc3545"

                start = f"{row['data_agendamento']}T{row['hora_agendamento']}"
                try:
                    # Tenta calcular hora fim (1h depois)
                    h_str = str(row['hora_agendamento']).split(':')
                    h, m = int(h_str[0]), int(h_str[1])
                    end = f"{row['data_agendamento']}T{h + 1:02d}:{m:02d}:00"
                except:
                    end = start

                events.append({
                    "title": f"{row['cliente_nome']} - {row['procedimento_nome']}",
                    "start": start, "end": end,
                    "backgroundColor": cor, "borderColor": cor
                })

            calendar_options = {
                "headerToolbar": {"left": "today prev,next", "center": "title",
                                  "right": "timeGridDay,timeGridWeek,dayGridMonth"},
                "buttonText": {"today": "Hoje", "month": "Mês", "week": "Semana", "day": "Dia", "list": "Lista"},
                "initialView": "dayGridMonth",
                "slotMinTime": "07:00:00", "slotMaxTime": "21:00:00",
                "locale": "pt-br", "allDaySlot": False
            }
            # KEY IMPORTANTE: Força recarregar quando muda dados
            calendar(events=events, options=calendar_options, key=f"cal_{len(events)}")
            st.caption("Legenda: 🔵 Agendado | 🟢 Concluído | 🔴 Cancelado")
        else:
            st.info("Agenda vazia.")

    # Aba 2: Lista
    with t_lista:
        if not df_ag.empty:
            st.info("💡 Mude para **Concluído** e salve para lançar a Receita automaticamente.")

            cols_show = ['id', 'data_agendamento', 'hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status',
                         'valor_cobrado']
            edited = st.data_editor(
                df_ag[cols_show],
                column_config={
                    "status": st.column_config.SelectboxColumn("Status", options=["Agendado", "Concluído", "Cancelado"],
                                                               required=True)},
                hide_index=True, use_container_width=True, key="ag_editor_safe"
            )

            if st.button("💾 Salvar Alterações na Lista"):
                for i, row in edited.iterrows():
                    # Lógica de atualização e lançamento financeiro
                    original = df_ag[df_ag['id'] == row['id']].iloc[0]
                    changed = False

                    if row['status'] != original['status']: changed = True
                    if float(row['valor_cobrado']) != float(original['valor_cobrado']): changed = True

                    if changed:
                        update_data("agenda", int(row['id']), {
                            "status": row['status'],
                            "valor_cobrado": float(row['valor_cobrado'])
                        })

                        # Se virou Concluído, lança receita
                        if row['status'] == "Concluído" and original['status'] != "Concluído":
                            add_data("financeiro", {
                                "descricao": f"Atendimento: {row['cliente_nome']}",
                                "valor": float(row['valor_cobrado']),
                                "tipo": "Receita", "categoria": "Atendimento",
                                "data_movimento": str(data_hoje_br()), "forma_pagamento": "Indefinido"
                            })
                            st.toast("💰 Receita lançada no caixa!", icon="🤑")
                            time.sleep(1)

                st.success("Agenda atualizada!")
                time.sleep(1)
                st.rerun()

            st.divider()
            # Botão Excluir Robusto
            lista_opcoes = df_ag.apply(lambda x: f"ID {x['id']}: {x['cliente_nome']} ({x['data_agendamento']})", axis=1)
            item_del = st.selectbox("Selecione para excluir:", lista_opcoes)

            if st.button("🗑️ Excluir Agendamento"):
                if item_del:
                    id_real = int(item_del.split(":")[0].replace("ID ", ""))
                    delete_data("agenda", id_real)
                    st.success("Agendamento removido!")
                    time.sleep(1)  # Espera o banco processar
                    st.rerun()  # Recarrega a tela limpa

    # Aba 3: Novo
    with t_novo:
        if df_cli.empty or df_proc.empty:
            st.warning("⚠️ Você precisa cadastrar Clientes e Procedimentos primeiro.")
        else:
            with st.form("form_novo_ag"):
                c1, c2 = st.columns(2)
                cli = c1.selectbox("Cliente", df_cli['nome'].unique())
                proc = c2.selectbox("Procedimento", df_proc['nome'].unique())
                c3, c4 = st.columns(2)
                dt_ag = c3.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
                hr_ag = c4.time_input("Hora")
                obs = st.text_area("Observações")

                if st.form_submit_button("✅ Agendar"):
                    # Busca IDs
                    cid = df_cli[df_cli['nome'] == cli]['id'].values[0]
                    dados_proc = df_proc[df_proc['nome'] == proc].iloc[0]
                    pid = dados_proc['id']
                    val = dados_proc['valor']

                    add_data("agenda", {
                        "cliente_id": int(cid), "cliente_nome": cli,
                        "procedimento_id": int(pid), "procedimento_nome": proc,
                        "valor_cobrado": float(val),
                        "data_agendamento": str(dt_ag), "hora_agendamento": str(hr_ag),
                        "status": "Agendado", "observacoes": obs
                    })
                    st.success("Agendado com sucesso!")
                    time.sleep(1)
                    st.rerun()

# --- PÁGINA: CLIENTES ---
elif menu == "👥 Clientes":
    st.title("Gestão de Clientes")
    tab1, tab2 = st.tabs(["Novo Cadastro", "Gerenciar Clientes"])

    with tab1:
        with st.form("form_cli"):
            nome = st.text_input("Nome Completo*")
            tel = st.text_input("Telefone (WhatsApp)")
            email = st.text_input("E-mail")
            nasc = st.date_input("Data Nascimento", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            anam = st.text_area("Anamnese / Histórico")

            if st.form_submit_button("Salvar Cliente"):
                if nome:
                    add_data("clientes", {
                        "nome": nome, "telefone": tel, "email": email,
                        "data_nascimento": str(nasc), "anamnese": anam
                    })
                    st.success("Cliente salvo!")
                    time.sleep(1);
                    st.rerun()
                else:
                    st.error("Nome é obrigatório.")

    with tab2:
        df = get_data("clientes")
        if not df.empty:
            sel_cli = st.selectbox("Selecione o Cliente:", df['nome'].unique())
            dados = df[df['nome'] == sel_cli].iloc[0]

            with st.form("form_edit_cli"):
                col_a, col_b = st.columns(2)
                novo_nome = col_a.text_input("Nome", dados['nome'])
                novo_tel = col_b.text_input("Telefone", dados['telefone'])
                novo_email = col_a.text_input("E-mail", dados['email'])

                # Tratamento data seguro
                try:
                    d_nasc = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
                except:
                    d_nasc = date.today()

                novo_nasc = col_b.date_input("Nascimento", d_nasc, format="DD/MM/YYYY")
                nova_anam = st.text_area("Anamnese", dados['anamnese'])

                if st.form_submit_button("💾 Atualizar Dados"):
                    update_data("clientes", int(dados['id']), {
                        "nome": novo_nome, "telefone": novo_tel,
                        "email": novo_email, "data_nascimento": str(novo_nasc),
                        "anamnese": nova_anam
                    })
                    st.success("Atualizado!")
                    time.sleep(1);
                    st.rerun()

            # Botões Extras
            c1, c2 = st.columns(2)
            c1.download_button("📄 Baixar Ficha PDF", data=gerar_ficha_individual(dados),
                               file_name=f"Ficha_{sel_cli}.pdf", mime="application/pdf")

            if c2.button("🗑️ Excluir Cliente"):
                delete_data("clientes", int(dados['id']))
                st.success("Cliente removido.")
                time.sleep(1);
                st.rerun()  # Refresh seguro

# --- PÁGINA: PROCEDIMENTOS ---
elif menu == "💉 Procedimentos":
    st.title("Procedimentos")
    c1, c2 = st.columns([1, 2])

    with c1:
        st.subheader("Novo")
        with st.form("form_proc"):
            n = st.text_input("Nome")
            v = st.number_input("Valor (R$)", min_value=0.0)
            m = st.number_input("Duração (min)", value=30, step=5)
            if st.form_submit_button("Salvar"):
                if n:
                    add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": m, "categoria": "Geral"})
                    st.success("Salvo!")
                    time.sleep(1);
                    st.rerun()

    with c2:
        st.subheader("Lista")
        df = get_data("procedimentos")
        if not df.empty:
            st.dataframe(df[['nome', 'valor', 'duracao_min']], use_container_width=True)

            to_del = st.selectbox("Excluir Procedimento:", df['nome'].unique())
            if st.button("🗑️ Excluir"):
                pid = df[df['nome'] == to_del]['id'].values[0]
                delete_data("procedimentos", int(pid))
                st.success("Deletado!")
                time.sleep(1);
                st.rerun()  # Refresh seguro

# --- PÁGINA: FINANCEIRO ---
elif menu == "💰 Financeiro":
    st.title("Fluxo de Caixa")
    t1, t2 = st.tabs(["Lançar Movimento", "Extrato Completo"])

    with t1:
        with st.form("form_fin"):
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Tipo", ["Despesa", "Receita"])
            desc = c2.text_input("Descrição (Ex: Conta de Luz)")
            val = c1.number_input("Valor (R$)", min_value=0.0)
            dt = c2.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
            cat = c1.selectbox("Categoria", ["Atendimento", "Produto", "Custo Fixo", "Impostos", "Outros"])

            if st.form_submit_button("✅ Lançar no Caixa"):
                if desc:
                    add_data("financeiro", {
                        "descricao": desc, "valor": val, "tipo": tipo,
                        "categoria": cat, "data_movimento": str(dt),
                        "forma_pagamento": "Manual"
                    })
                    st.success("Lançado!")
                    time.sleep(1);
                    st.rerun()
                else:
                    st.error("Preencha a descrição.")

    with t2:
        df = get_data("financeiro")
        if not df.empty:
            # Filtro de Mês
            mes_sel = st.slider("Filtrar Mês:", 1, 12, data_hoje_br().month)
            df['dt_obj'] = pd.to_datetime(df['data_movimento'])
            df_view = df[df['dt_obj'].dt.month == mes_sel].sort_values('dt_obj', ascending=False)


            # Tabela Colorida
            def color_tipo(val):
                color = '#d4edda' if val == 'Receita' else '#f8d7da'
                return f'background-color: {color}'


            st.dataframe(
                df_view[['data_movimento', 'tipo', 'descricao', 'valor', 'categoria']].style.map(color_tipo,
                                                                                                 subset=['tipo']),
                use_container_width=True
            )

            c_ex, c_del = st.columns([1, 1])
            c_ex.download_button("📥 Baixar Excel", to_excel(df_view), "extrato.xlsx")

            # Exclusão Segura
            with c_del:
                lista_del = df_view.apply(lambda x: f"ID {x['id']}: {x['descricao']} - R$ {x['valor']}", axis=1)
                item_del = st.selectbox("Selecionar para excluir:", lista_del)
                if st.button("🗑️ Apagar Lançamento"):
                    id_real = int(item_del.split(":")[0].replace("ID ", ""))
                    delete_data("financeiro", id_real)
                    st.success("Apagado!")
                    time.sleep(1);
                    st.rerun()

# --- PÁGINA: RELATÓRIOS ---
elif menu == "📑 Relatórios":
    st.title("Relatórios Personalizados")
    d1 = st.date_input("Data Início", value=data_hoje_br().replace(day=1), format="DD/MM/YYYY")
    d2 = st.date_input("Data Fim", value=data_hoje_br(), format="DD/MM/YYYY")

    tipo_rel = st.radio("Tipo:", ["Financeiro", "Atendimentos"], horizontal=True)

    if st.button("Gerar Relatório"):
        if tipo_rel == "Financeiro":
            df = get_data("financeiro")
            if not df.empty:
                filtro = df[(df['data_movimento'] >= str(d1)) & (df['data_movimento'] <= str(d2))]
                st.dataframe(filtro)
                st.download_button("📥 Baixar Excel", to_excel(filtro), "relatorio_financeiro.xlsx")
            else:
                st.warning("Sem dados.")

        elif tipo_rel == "Atendimentos":
            df = get_data("agenda")
            if not df.empty:
                filtro = df[(df['data_agendamento'] >= str(d1)) & (df['data_agendamento'] <= str(d2))]
                st.dataframe(filtro)
                st.download_button("📥 Baixar Excel", to_excel(filtro), "relatorio_agenda.xlsx")
            else:
                st.warning("Sem dados.")

# --- PÁGINA: INSIGHTS ---
elif menu == "🎂 Insights":
    st.title("Aniversariantes do Mês")
    df = get_data("clientes")

    if not df.empty:
        meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

        mes_atual = data_hoje_br().month
        nome_mes = meses_pt[mes_atual]

        df['dt_obj'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
        ani = df[df['dt_obj'].dt.month == mes_atual].sort_values('dt_obj')

        if not ani.empty:
            st.balloons()
            st.success(f"🥳 {len(ani)} clientes fazem aniversário em {nome_mes}!")

            for i, row in ani.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    try:
                        dia = row['dt_obj'].day
                    except:
                        dia = "?"

                    c1.markdown(f"**Dia {dia}:** {row['nome']}")
                    c2.markdown(f"📞 {row['telefone']}")

                    if row['telefone']:
                        zap = limpar_telefone(row['telefone'])
                        msg = f"Olá {row['nome']}! Parabéns pelo seu dia! 🎉 Muita saúde e beleza para você!"
                        link = f"https://wa.me/55{zap}?text={msg}"
                        c3.link_button("🎁 Enviar Zap", link)
        else:
            st.info(f"Nenhum aniversariante em {nome_mes}.")
    else:
        st.warning("Cadastre seus clientes primeiro!")