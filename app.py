import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import io
import os
import smtplib
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from supabase import create_client, Client
from streamlit_calendar import calendar

# ==============================================================================
# 1. CONFIGURAÇÕES INICIAIS E SEGURANÇA
# ==============================================================================
st.set_page_config(page_title="Bárbara Castro Estética", layout="wide", page_icon="✨")

st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #D4AF37; text-align: center; font-weight: bold;}
    .metric-box {border: 1px solid #e6e6e6; padding: 20px; border-radius: 10px; background-color: #f9f9f9;}
    div[data-testid="stMetricValue"] {color: #D4AF37;}
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
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
                    admin_user = st.secrets["admin"]["usuario"] if "admin" in st.secrets else "admin"
                    admin_pass = st.secrets["admin"]["senha"] if "admin" in st.secrets else "1234"
                    if user == admin_user and password == admin_pass:
                        st.session_state["logado"] = True
                        st.toast("Login realizado com sucesso!", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception:
                    st.error("Erro no login.")


if not st.session_state["logado"]:
    check_login()
    st.stop()

# ==============================================================================
# 2. CONEXÃO COM BANCO DE DADOS
# ==============================================================================
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


def data_hoje_br():
    return (datetime.utcnow() - timedelta(hours=3)).date()


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
# 3. FUNÇÕES CRUD
# ==============================================================================
def get_data(table):
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table(table).select("*").order("id").execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()


def add_data(table, data):
    if not supabase: return False
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}");
        return False


def update_data(table, id_, data):
    if not supabase: return False
    try:
        supabase.table(table).update(data).eq("id", id_).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}");
        return False


def delete_data(table, id_):
    if not supabase: return False
    try:
        supabase.table(table).delete().eq("id", id_).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}");
        return False


def limpar_telefone(telefone):
    if not telefone: return ""
    return ''.join(filter(str.isdigit, str(telefone)))


# ==============================================================================
# 4. GERADORES
# ==============================================================================
def gerar_ficha_individual(dados_cliente):
    pdf = FPDF();
    pdf.add_page();
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "Bárbara Castro Saúde & Estética Integrativa".encode('latin-1', 'replace').decode('latin-1'),
             ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, "Ficha de Anamnese".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(15);
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "DADOS DO CLIENTE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    nome = str(dados_cliente['nome']).encode('latin-1', 'replace').decode('latin-1')
    email = str(dados_cliente.get('email', '')).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 8, f"Nome: {nome}", ln=True)
    pdf.cell(0, 8, f"Telefone: {dados_cliente['telefone']}", ln=True)
    pdf.cell(0, 8, f"E-mail: {email}", ln=True)
    nasc = dados_cliente.get('data_nascimento', '')
    if nasc:
        try:
            d = datetime.strptime(nasc, '%Y-%m-%d').strftime('%d/%m/%Y'); pdf.cell(0, 8, f"Data de Nascimento: {d}",
                                                                                   ln=True)
        except:
            pass
    pdf.ln(10);
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "HISTÓRICO / ANAMNESE:", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    texto_anamnese = str(dados_cliente.get('anamnese', 'Nenhuma observação.')).encode('latin-1', 'replace').decode(
        'latin-1')
    pdf.multi_cell(0, 8, txt=texto_anamnese)
    pdf.ln(40);
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, "________________________________________________________", ln=True, align='C')
    pdf.cell(0, 5, "Bárbara Castro - Estética Integrativa".encode('latin-1', 'replace').decode('latin-1'), ln=True,
             align='C')
    return pdf.output(dest='S').encode('latin-1')


def gerar_prescricao_pdf(nome_cliente, texto_prescricao):
    pdf = FPDF();
    pdf.set_auto_page_break(auto=True, margin=15);
    pdf.add_page();
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Bárbara Castro".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 8, "Saúde & Estética Integrativa".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(5);
    pdf.set_draw_color(180, 180, 180);
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12);
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Paciente: {nome_cliente}".encode('latin-1', 'replace').decode('latin-1'), ln=True);
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    texto_safe = texto_prescricao.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=texto_safe)
    if pdf.get_y() > 220: pdf.add_page()
    pdf.set_y(-60);
    data_hj = date.today().strftime('%d/%m/%Y')
    pdf.set_font("Arial", 'I', 11);
    pdf.cell(0, 8, f"Rio de Janeiro, {data_hj}", ln=True, align='C');
    pdf.ln(10)
    pdf.cell(0, 5, "________________________________________________________", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 8, "Bárbara Castro", ln=True, align='C')
    pdf.set_font("Arial", size=10);
    pdf.cell(0, 5, "Saúde & Estética Integrativa".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')


def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()


def enviar_agenda_email():
    try:
        df_ag = get_data("agenda");
        hoje_bd = str(data_hoje_br());
        hoje_br = data_hoje_br().strftime('%d/%m/%Y')
        df_hoje = pd.DataFrame()
        if not df_ag.empty and 'data_agendamento' in df_ag.columns: df_hoje = df_ag[
            df_ag['data_agendamento'] == hoje_bd]
        msg = MIMEMultipart();
        msg['From'] = EMAIL_REMETENTE;
        msg['To'] = EMAIL_DESTINATARIO;
        msg['Subject'] = f"Agenda do Dia - {hoje_br}"
        html = f"<h2>Resumo da Agenda - {hoje_br}</h2>"
        if df_hoje.empty:
            html += "<p>Agenda livre hoje.</p>"
        else:
            html += df_hoje[['hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status']].to_html()
        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587);
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA);
        server.send_message(msg);
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro ao enviar: {e}"


if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    st.write(enviar_agenda_email());
    st.stop()

# ==============================================================================
# 5. INTERFACE DO USUÁRIO
# ==============================================================================
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=150)
    elif os.path.exists("barbara.jpeg"):
        st.image("barbara.jpeg", width=150)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)
    st.markdown("### Barbara Castro Saúde & Estética integrativa")
    if st.button("🚪 Sair", type="secondary"): st.session_state["logado"] = False; st.rerun()
    st.markdown("---")
    menu = st.radio("MENU", ["📊 Dashboard", "📅 Agenda", "👥 Clientes", "💉 Procedimentos", "💰 Financeiro", "📑 Relatórios",
                             "🎂 Insights"])
    st.markdown("---")
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
    df_ag = get_data("agenda");
    df_fin = get_data("financeiro");
    hj = str(data_hoje_br())
    data_atual = data_hoje_br();
    mes_atual = data_atual.month;
    ano_atual = data_atual.year
    nome_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                  9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

    ag = len(df_ag[df_ag['data_agendamento'] == hj]) if not df_ag.empty and 'data_agendamento' in df_ag.columns else 0
    rec, des = 0.0, 0.0
    if not df_fin.empty and 'data_movimento' in df_fin.columns:
        df_fin['dt_obj'] = pd.to_datetime(df_fin['data_movimento'], errors='coerce')
        df_mes = df_fin[(df_fin['dt_obj'].dt.month == mes_atual) & (df_fin['dt_obj'].dt.year == ano_atual)]
        rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
        des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()
    lucro = rec - des

    st.markdown(f"### 🗓️ Visão Mensal: {nome_meses[mes_atual]} / {ano_atual}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agenda Hoje", ag);
    c2.metric("Receita (Mês)", f"R$ {rec:,.2f}");
    c3.metric("Despesas (Mês)", f"R$ {des:,.2f}");
    c4.metric("Lucro Líquido", f"R$ {lucro:,.2f}")

    st.markdown("---");
    st.subheader("🛑 Contas a Pagar (HOJE)")
    if not df_fin.empty:
        hoje_dt = pd.to_datetime(data_hoje_br());
        df_fin['dt_obj'] = pd.to_datetime(df_fin['data_movimento'], errors='coerce')
        mask = (df_fin['tipo'] == 'Despesa') & (df_fin['dt_obj'] == hoje_dt)
        df_vencendo = df_fin[mask].sort_values('dt_obj')
        if not df_vencendo.empty:
            for i, row in df_vencendo.iterrows():
                if row.get('status', 'Pendente') == 'Pago':
                    st.success(f"✅ **Pago:** {row['descricao']} — R$ {row['valor']:,.2f}")
                else:
                    st.error(f"💸 **Vence Hoje:** {row['descricao']} — **R$ {row['valor']:,.2f}**")
        else:
            st.success("Tudo pago! Nenhuma despesa vence hoje. ✅")
    else:
        st.info("Nenhum registro financeiro encontrado.")

# --- PÁGINA: AGENDA ---
elif menu == "📅 Agenda":
    st.title("Agenda")
    t_cal, t_lista, t_novo, t_robo = st.tabs(["📅 Calendário", "📝 Lista & Edição", "➕ Novo", "🤖 Robô Confirmador"])
    df_cli = get_data("clientes");
    df_proc = get_data("procedimentos");
    df_ag = get_data("agenda")

    with t_cal:
        if not df_ag.empty:
            events = []
            for i, row in df_ag.iterrows():
                cor = "#3788d8"
                if row['status'] == "Concluído":
                    cor = "#28a745"
                elif row['status'] == "Cancelado":
                    cor = "#dc3545"
                start = f"{row['data_agendamento']}T{row['hora_agendamento']}"
                try:
                    h, m = map(int, str(row['hora_agendamento']).split(':')[
                        :2]); end = f"{row['data_agendamento']}T{h + 1:02d}:{m:02d}:00"
                except:
                    end = start
                events.append(
                    {"title": f"{row['cliente_nome']} - {row['procedimento_nome']}", "start": start, "end": end,
                     "backgroundColor": cor, "borderColor": cor})
            calendar(events=events, options={"headerToolbar": {"left": "today prev,next", "center": "title",
                                                               "right": "timeGridDay,timeGridWeek,dayGridMonth"},
                                             "initialView": "dayGridMonth"}, key=f"cal_{len(events)}")
        else:
            st.info("Agenda vazia.")

    with t_lista:
        if not df_ag.empty:
            st.info("💡 Mude para **Concluído** e salve para lançar a Receita.")
            cols_show = ['id', 'data_agendamento', 'hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status',
                         'valor_cobrado']
            edited = st.data_editor(df_ag[cols_show], column_config={
                "status": st.column_config.SelectboxColumn("Status", options=["Agendado", "Concluído", "Cancelado"],
                                                           required=True)}, hide_index=True, use_container_width=True,
                                    key="ag_editor_safe")
            if st.button("💾 Salvar Alterações na Lista"):
                for i, row in edited.iterrows():
                    original = df_ag[df_ag['id'] == row['id']].iloc[0];
                    changed = False
                    if row['status'] != original['status']: changed = True
                    if float(row['valor_cobrado']) != float(original['valor_cobrado']): changed = True
                    if changed:
                        update_data("agenda", int(row['id']),
                                    {"status": row['status'], "valor_cobrado": float(row['valor_cobrado'])})
                        if row['status'] == "Concluído" and original['status'] != "Concluído":
                            add_data("financeiro", {"descricao": f"Atendimento: {row['cliente_nome']}",
                                                    "valor": float(row['valor_cobrado']), "tipo": "Receita",
                                                    "categoria": "Atendimento", "data_movimento": str(data_hoje_br()),
                                                    "forma_pagamento": "Indefinido", "status": "Pago"})
                            st.toast("💰 Receita lançada no caixa!", icon="🤑");
                            time.sleep(1)
                st.success("Agenda atualizada!");
                time.sleep(1);
                st.rerun()
            st.divider();
            item = st.selectbox("Excluir Agendamento:",
                                df_ag.apply(lambda x: f"ID {x['id']}: {x['cliente_nome']}", axis=1))
            if st.button("🗑️ Apagar Agendamento"):
                delete_data("agenda", int(item.split(":")[0].replace("ID ", "")));
                st.success("Apagado!");
                time.sleep(1);
                st.rerun()

    with t_novo:
        if df_cli.empty or df_proc.empty:
            st.warning("Cadastre clientes e procedimentos.")
        else:
            with st.form("new_ag"):
                c1, c2 = st.columns(2);
                cli = c1.selectbox("Cliente", df_cli['nome'].unique());
                proc = c2.selectbox("Proc", df_proc['nome'].unique())
                d = c1.date_input("Data", data_hoje_br());
                h = c2.time_input("Hora");
                obs = st.text_area("Obs")
                if st.form_submit_button("Agendar"):
                    cid = df_cli[df_cli['nome'] == cli]['id'].values[0];
                    p = df_proc[df_proc['nome'] == proc].iloc[0]
                    add_data("agenda", {"cliente_id": int(cid), "cliente_nome": cli, "procedimento_id": int(p['id']),
                                        "procedimento_nome": proc, "valor_cobrado": float(p['valor']),
                                        "data_agendamento": str(d), "hora_agendamento": str(h), "status": "Agendado",
                                        "observacoes": obs})
                    st.success("Agendado!");
                    time.sleep(1);
                    st.rerun()

    with t_robo:
        st.subheader("🤖 Robô de Confirmação (Manual)")
        st.info("Clientes agendados para **AMANHÃ**.")
        if not df_ag.empty:
            amanha = data_hoje_br() + timedelta(days=1)
            df_amanha = df_ag[(df_ag['data_agendamento'] == str(amanha)) & (df_ag['status'] == 'Agendado')]
            if not df_amanha.empty:
                df_amanha = df_amanha.sort_values('hora_agendamento')
                st.write(f"**{len(df_amanha)} confirmações para {amanha.strftime('%d/%m/%Y')}**")
                for i, row in df_amanha.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([0.5, 3, 1])
                        c1.checkbox("Ok", key=f"chk_{row['id']}")
                        c2.markdown(
                            f"**{row['hora_agendamento']}** - {row['cliente_nome']} ({row['procedimento_nome']})")
                        tel = "";
                        dc = df_cli[df_cli['nome'] == row['cliente_nome']] if not df_cli.empty else pd.DataFrame()
                        if not dc.empty: tel = dc.iloc[0]['telefone']
                        if tel:
                            msg = f"Olá {row['cliente_nome']}, tudo bem? Sou a assistente da Bárbara Castro. Confirmando seu horário de {row['procedimento_nome']} amanhã às {row['hora_agendamento']}. Podemos confirmar?"
                            link = f"https://wa.me/55{limpar_telefone(tel)}?text={urllib.parse.quote(msg)}"
                            c3.link_button("📲 Enviar", link)
                        else:
                            c3.error("Sem Tel")
            else:
                st.success("Nada para confirmar amanhã.")
        else:
            st.info("Agenda vazia.")

# --- PÁGINA: CLIENTES ---
elif menu == "👥 Clientes":
    st.title("Gestão de Clientes")
    t1, t2, t3 = st.tabs(["Novo Cadastro", "Gerenciar Clientes", "💊 Prescrição"])
    with t1:
        with st.form("fc"):
            n = st.text_input("Nome*");
            t = st.text_input("Zap");
            e = st.text_input("Email");
            dt = st.date_input("Nasc", date(1980, 1, 1));
            a = st.text_area("Anamnese")
            if st.form_submit_button("Salvar") and n:
                add_data("clientes", {"nome": n, "telefone": t, "email": e, "data_nascimento": str(dt), "anamnese": a});
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()

    with t2:
        df = get_data("clientes")
        if not df.empty:
            s = st.selectbox("Cliente", df['nome'].unique());
            d = df[df['nome'] == s].iloc[0]
            with st.form("fe"):
                nn = st.text_input("Nome", d['nome']);
                nt = st.text_input("Zap", d['telefone']);
                ne = st.text_input("Email", d['email'])

                # CORREÇÃO CLIENTES: DATA DE NASCIMENTO
                data_nasc_valor = date(1980, 1, 1)
                if d['data_nascimento']:
                    try:
                        data_nasc_valor = datetime.strptime(d['data_nascimento'], '%Y-%m-%d').date()
                    except:
                        pass

                ndt = st.date_input("Nascimento", data_nasc_valor)
                na = st.text_area("Anamnese", d['anamnese'])

                if st.form_submit_button("Atualizar"):
                    update_data("clientes", int(d['id']),
                                {"nome": nn, "telefone": nt, "email": ne, "data_nascimento": str(ndt), "anamnese": na})
                    st.success("Atualizado!");
                    time.sleep(1);
                    st.rerun()
            c1, c2 = st.columns(2);
            c1.download_button("PDF Ficha", gerar_ficha_individual(d), "ficha.pdf")
            if c2.button("Excluir Cliente"): delete_data("clientes", int(d['id'])); st.success("Excluído!"); time.sleep(
                1); st.rerun()

    with t3:
        st.subheader("Nova Prescrição")
        dfc = get_data("clientes")
        if not dfc.empty:
            cp = st.selectbox("Paciente", dfc['nome'].unique(), key="sb_p")
            if "presc_txt" not in st.session_state: st.session_state["presc_txt"] = ""


            def gerar_pdf_callback():
                t = st.session_state["presc_txt"];
                c = st.session_state["sb_p"]
                if t:
                    pdf = gerar_prescricao_pdf(c, t)
                    st.session_state["last_pdf"] = pdf;
                    st.session_state["last_cli"] = c;
                    st.session_state["presc_txt"] = ""


            st.text_area("Texto da Prescrição:", height=200, key="presc_txt")
            st.button("Gerar PDF", on_click=gerar_pdf_callback)
            if "last_pdf" in st.session_state:
                st.success(f"Gerado para {st.session_state['last_cli']}")
                c1, c2 = st.columns(2)
                c1.download_button("📥 Baixar PDF", st.session_state["last_pdf"], "prescricao.pdf", "application/pdf")
                info = dfc[dfc['nome'] == st.session_state['last_cli']]
                if not info.empty and info.iloc[0]['telefone']:
                    link = f"https://wa.me/55{limpar_telefone(info.iloc[0]['telefone'])}?text=Sua prescrição"
                    c2.link_button("💚 Enviar Zap", link)

# --- PÁGINA: PROCEDIMENTOS ---
elif menu == "💉 Procedimentos":
    st.title("Procedimentos")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("fp"):
            n = st.text_input("Nome");
            v = st.number_input("R$");
            m = st.number_input("Min", 30)
            if st.form_submit_button("Salvar") and n: add_data("procedimentos",
                                                               {"nome": n, "valor": v, "duracao_min": m,
                                                                "categoria": "Geral"}); st.success(
                "Salvo!"); time.sleep(1); st.rerun()
    with c2:
        df = get_data("procedimentos")
        if not df.empty:
            st.dataframe(df[['nome', 'valor', 'duracao_min']], use_container_width=True)
            d = st.selectbox("Excluir:", df['nome'].unique())
            if st.button("Deletar"): delete_data("procedimentos", int(df[df['nome'] == d]['id'].values[0])); st.success(
                "Deletado!"); time.sleep(1); st.rerun()

# --- PÁGINA: FINANCEIRO (CORRIGIDA E RECONSTRUÍDA) ---
elif menu == "💰 Financeiro":
    st.title("Fluxo de Caixa")
    t1, t2 = st.tabs(["Lançar Movimento", "Extrato Completo"])

    with t1:
        with st.form("ff"):
            c1, c2 = st.columns(2)
            tp = c1.selectbox("Tipo", ["Despesa", "Receita"])
            ds = c2.text_input("Descrição")
            vl = c1.number_input("Valor (R$)", min_value=0.0, step=0.01)
            dt = c2.date_input("Data", data_hoje_br())
            ct = c1.selectbox("Categoria", ["Atendimento", "Custo Fixo", "Produto", "Impostos"])
            stt = c2.selectbox("Status", ["Pago", "Pendente"])
            if st.form_submit_button("Lançar") and ds:
                add_data("financeiro",
                         {"descricao": ds, "valor": vl, "tipo": tp, "categoria": ct, "data_movimento": str(dt),
                          "status": stt, "forma_pagamento": "Manual"})
                st.success("Lançado!");
                time.sleep(1);
                st.rerun()

    with t2:
        df = get_data("financeiro")
        if not df.empty:
            mes = st.slider("Mês", 1, 12, data_hoje_br().month)
            if 'data_movimento' not in df.columns: df['data_movimento'] = str(data_hoje_br())
            df['dt_obj'] = pd.to_datetime(df['data_movimento'], errors='coerce')
            df_view = df[df['dt_obj'].dt.month == mes].sort_values('dt_obj', ascending=False)

            # --- RECONSTRUÇÃO TOTAL DA TABELA (ANTI-CRASH) ---
            # Em vez de tentar converter o dataframe existente (que pode ter tipos mistos),
            # criamos uma lista nova limpa, garantindo que tudo é int, float ou str.
            clean_rows = []
            for idx, row in df_view.iterrows():
                # Tratamento seguro de cada campo
                safe_id = int(row.get('id', 0)) if pd.notnull(row.get('id')) else 0

                raw_val = row.get('valor', 0.0)
                try:
                    safe_val = float(raw_val)
                except:
                    safe_val = 0.0

                raw_stat = row.get('status', 'Pendente')
                safe_stat = str(raw_stat) if raw_stat and str(raw_stat) in ["Pago", "Pendente"] else "Pendente"

                clean_rows.append({
                    "id": safe_id,
                    "data_movimento": row.get('data_movimento'),
                    "tipo": str(row.get('tipo', '')),
                    "descricao": str(row.get('descricao', '')),
                    "valor": safe_val,
                    "status": safe_stat,
                    "categoria": str(row.get('categoria', ''))
                })

            # Cria DataFrame novo e limpo
            df_clean = pd.DataFrame(clean_rows)

            col_cfg = {
                "id": st.column_config.NumberColumn(disabled=True, width="small"),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0.0),
                "status": st.column_config.SelectboxColumn("Status", options=["Pago", "Pendente"], width="medium",
                                                           required=True),
                "tipo": st.column_config.TextColumn(disabled=True),
                "data_movimento": st.column_config.DateColumn("Data", format="DD/MM/YYYY")
            }

            if not df_clean.empty:
                edited = st.data_editor(df_clean, column_config=col_cfg, hide_index=True, use_container_width=True,
                                        key="fin_ed_safe")

                if st.button("💾 Salvar Alterações Financeiras"):
                    changes = 0
                    for i, row in edited.iterrows():
                        orig_row = df[df['id'] == row['id']]
                        if not orig_row.empty:
                            orig = orig_row.iloc[0]
                            # Compara usando os mesmos tipos seguros
                            orig_val = float(orig.get('valor', 0.0) or 0.0)
                            orig_stat = str(orig.get('status', 'Pendente'))

                            if row['status'] != orig_stat or abs(row['valor'] - orig_val) > 0.01 or row[
                                'descricao'] != orig.get('descricao', ''):
                                update_data("financeiro", int(row['id']), {
                                    "status": row['status'],
                                    "valor": float(row['valor']),
                                    "descricao": row['descricao']
                                })
                                changes += 1
                    if changes:
                        st.success("Atualizado!"); time.sleep(1); st.rerun()
                    else:
                        st.info("Nada mudou.")

                st.download_button("Excel", to_excel(edited), "financeiro.xlsx")
                d_id = st.selectbox("Excluir ID:", df_clean.apply(lambda x: f"{x['id']}: {x['descricao']}", axis=1))
                if st.button("🗑️ Apagar Item"):
                    delete_data("financeiro", int(d_id.split(":")[0]));
                    st.success("Apagado!");
                    time.sleep(1);
                    st.rerun()
            else:
                st.info("Nenhum registro encontrado neste mês.")
        else:
            st.info("Nenhum registro financeiro encontrado.")

# --- PÁGINA: RELATÓRIOS ---
elif menu == "📑 Relatórios":
    st.title("Relatórios");
    d1 = st.date_input("De");
    d2 = st.date_input("Até")
    if st.button("Gerar"):
        df = get_data("financeiro")
        if not df.empty:
            df = df[(df['data_movimento'] >= str(d1)) & (df['data_movimento'] <= str(d2))]
            st.dataframe(df)
            st.download_button("Baixar Excel", to_excel(df), "relatorio.xlsx")

# --- PÁGINA: INSIGHTS ---
elif menu == "🎂 Insights":
    st.title("Aniversariantes");
    df = get_data("clientes")
    if not df.empty:
        df['dob'] = pd.to_datetime(df['data_nascimento'], errors='coerce');
        m = data_hoje_br().month
        ani = df[df['dob'].dt.month == m].sort_values('dob')
        if not ani.empty:
            for i, r in ani.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1]);
                    c1.write(f"🎉 **Dia {r['dob'].day}:** {r['nome']}")
                    if r['telefone']: c2.link_button("Zap",
                                                     f"https://wa.me/55{limpar_telefone(r['telefone'])}?text=Parabéns")
        else:
            st.info("Ninguém este mês.")