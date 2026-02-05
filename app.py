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
from streamlit_calendar import calendar

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Bárbara Castro Estética", layout="wide", page_icon="✨")

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
                    if user == st.secrets["admin"]["usuario"] and password == st.secrets["admin"]["senha"]:
                        st.session_state["logado"] = True
                        st.rerun()
                    else:
                        st.error("Incorreto.")
                except:
                    st.error("Configure secrets.toml")


if not st.session_state["logado"]:
    check_login()
    st.stop()

# --- CSS ---
st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #D4AF37; text-align: center; font-weight: bold;}
    .metric-box {border: 1px solid #e6e6e6; padding: 20px; border-radius: 10px; background-color: #f9f9f9;}
    div[data-testid="stMetricValue"] {color: #D4AF37;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


def data_hoje_br(): return (datetime.utcnow() - timedelta(hours=3)).date()


try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except:
    st.error("Erro Supabase"); st.stop()


# --- FUNÇÕES ---
def limpar_telefone(t): return ''.join(filter(str.isdigit, str(t))) if t else ""


def get_data(t):
    try:
        return pd.DataFrame(supabase.table(t).select("*").order("id").execute().data)
    except:
        return pd.DataFrame()


def add_data(t, d):
    try:
        supabase.table(t).insert(d).execute(); return True
    except:
        return False


def update_data(t, i, d):
    try:
        supabase.table(t).update(d).eq("id", i).execute(); return True
    except:
        return False


def delete_data(t, i):
    try:
        supabase.table(t).delete().eq("id", i).execute(); return True
    except:
        return False


def gerar_ficha_individual(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 18);
    pdf.cell(0, 10, "Bárbara Castro Estética Avançada", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12);
    pdf.cell(0, 10, "Ficha de Anamnese", ln=True, align='C')
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "DADOS:", ln=True);
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Nome: {dados['nome']}", ln=True)
    pdf.cell(0, 8, f"Telefone: {dados['telefone']}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "ANAMNESE:", ln=True);
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(5)
    pdf.set_font("Arial", size=11);
    pdf.multi_cell(0, 8, txt=str(dados.get('anamnese', '')))
    pdf.ln(40)
    pdf.set_font("Arial", size=10);
    pdf.cell(0, 5, "___________________________________", ln=True, align='C')
    pdf.cell(0, 5, "Bárbara Castro", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')


def to_excel(df):
    o = io.BytesIO()
    with pd.ExcelWriter(o, engine='xlsxwriter') as w: df.to_excel(w, index=False)
    return o.getvalue()


def enviar_agenda_email():
    try:
        df = get_data("agenda")
        hj = str(data_hoje_br())
        df = df[df['data_agendamento'] == hj] if not df.empty else df
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE;
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"Agenda {hj}"
        html = "<h2>Agenda do Dia</h2>" + (df.to_html() if not df.empty else "Livre")
        msg.attach(MIMEText(html, 'html'))
        s = smtplib.SMTP('smtp.gmail.com', 587);
        s.starttls();
        s.login(EMAIL_REMETENTE, EMAIL_SENHA)
        s.send_message(msg);
        s.quit()
        return "Enviado!"
    except Exception as e:
        return f"Erro: {e}"


if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email": st.write(
    enviar_agenda_email()); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=150)
    elif os.path.exists("barbara.jpeg"):
        st.image("barbara.jpeg", width=150)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)
    st.markdown("### Bárbara Castro")
    if st.button("🚪 Sair"): st.session_state["logado"] = False; st.rerun()
    st.markdown("---")
    menu = st.radio("MENU", ["📊 Dashboard", "📅 Agenda", "👥 Clientes", "💉 Procedimentos", "💰 Financeiro", "📑 Relatórios",
                             "🎂 Insights"])
    st.markdown("---")
    if st.button("🔄 Atualizar"): st.rerun()

# --- PÁGINAS ---
if menu == "📊 Dashboard":
    st.markdown("<div class='main-header'>Painel de Controle</div>", unsafe_allow_html=True)

    df_ag = get_data("agenda")
    df_fin = get_data("financeiro")
    hj = str(data_hoje_br())

    data_atual = data_hoje_br()
    mes_atual = data_atual.month
    ano_atual = data_atual.year
    nome_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                  9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

    ag = len(df_ag[df_ag['data_agendamento'] == hj]) if not df_ag.empty else 0
    rec = 0.0
    des = 0.0

    if not df_fin.empty:
        df_fin['dt_obj'] = pd.to_datetime(df_fin['data_movimento'])
        df_mes = df_fin[(df_fin['dt_obj'].dt.month == mes_atual) & (df_fin['dt_obj'].dt.year == ano_atual)]
        rec = df_mes[df_mes['tipo'] == 'Receita']['valor'].sum()
        des = df_mes[df_mes['tipo'] == 'Despesa']['valor'].sum()

    lucro = rec - des
    st.markdown(f"### 🗓️ Visão Mensal: {nome_meses[mes_atual]} / {ano_atual}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agenda Hoje", ag)
    c2.metric("Receita (Mês)", f"R$ {rec:,.2f}")
    c3.metric("Despesas (Mês)", f"R$ {des:,.2f}")
    c4.metric("Lucro (Mês)", f"R$ {lucro:,.2f}")

    st.markdown("---")
    st.subheader("🛑 Contas a Pagar (HOJE)")
    if not df_fin.empty:
        hoje_dt = pd.to_datetime(data_hoje_br())
        mask = (df_fin['tipo'] == 'Despesa') & (df_fin['dt_obj'] == hoje_dt)
        df_vencendo = df_fin[mask].sort_values('dt_obj')
        if not df_vencendo.empty:
            for i, row in df_vencendo.iterrows():
                d_fmt = row['dt_obj'].strftime('%d/%m/%Y')
                st.error(f"📅 **{d_fmt}** — {row['descricao']} — **R$ {row['valor']:,.2f}**")
        else:
            st.success("Tudo pago! Nenhuma despesa vence hoje. ✅")
    else:
        st.info("Nenhum lançamento financeiro ainda.")

elif menu == "📅 Agenda":
    st.title("Agenda")
    t_cal, t_lista, t_novo = st.tabs(["📅 Calendário Visual", "📝 Lista & Edição", "➕ Novo Agendamento"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")
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
                    h, m, s = map(int, str(row['hora_agendamento']).split(':'))
                    end_h = h + 1
                    end = f"{row['data_agendamento']}T{end_h:02d}:{m:02d}:00"
                except:
                    end = start
                events.append(
                    {"title": f"{row['cliente_nome']} - {row['procedimento_nome']}", "start": start, "end": end,
                     "backgroundColor": cor, "borderColor": cor})

            calendar_options = {
                "headerToolbar": {"left": "today prev,next", "center": "title",
                                  "right": "timeGridDay,timeGridWeek,dayGridMonth"},
                "buttonText": {"today": "Hoje", "month": "Mês", "week": "Semana", "day": "Dia", "list": "Lista"},
                "initialView": "dayGridMonth",
                "slotMinTime": "07:00:00",
                "slotMaxTime": "21:00:00",
                "locale": "pt-br",
                "allDaySlot": False
            }
            # CORREÇÃO CRÍTICA AQUI: O 'key' força a atualização
            calendar(events=events, options=calendar_options, key=f"cal_{len(events)}")
            st.caption("🔵 Agendado | 🟢 Concluído | 🔴 Cancelado")
        else:
            st.info("Agenda vazia.")

    with t_lista:
        if not df_ag.empty:
            st.info("Mude para **Concluído** e salve para lançar no Caixa.")
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
            if st.button("🗑️ Apagar"):
                delete_data("agenda", int(item.split(":")[0].replace("ID ", "")))
                st.success("Apagado!");
                time.sleep(1);
                st.rerun()
        else:
            st.info("Nenhum agendamento.")

    with t_novo:
        if df_cli.empty or df_proc.empty:
            st.warning("Cadastre clientes e procedimentos antes.")
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

elif menu == "👥 Clientes":
    st.title("Clientes")
    op = st.radio("Ação:", ["Novo", "Gerenciar"], horizontal=True)
    if op == "Novo":
        with st.form("nc"):
            n = st.text_input("Nome");
            t = st.text_input("Zap");
            e = st.text_input("Email")
            d = st.date_input("Nasc", min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            a = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"): add_data("clientes", {"nome": n, "telefone": t, "email": e,
                                                                      "data_nascimento": str(d),
                                                                      "anamnese": a}); st.rerun()
    else:
        df = get_data("clientes")
        if not df.empty:
            s = st.selectbox("Cliente:", df['nome'].unique())
            d = df[df['nome'] == s].iloc[0]
            with st.form("ec"):
                nn = st.text_input("Nome", d['nome']);
                nt = st.text_input("Zap", d['telefone'])
                ne = st.text_input("Email", d['email']);
                na = st.text_area("Anamnese", d['anamnese'])
                if st.form_submit_button("Salvar"): update_data("clientes", int(d['id']),
                                                                {"nome": nn, "telefone": nt, "email": ne,
                                                                 "anamnese": na}); st.rerun()
            c1, c2 = st.columns(2)
            c1.download_button("📄 PDF", gerar_ficha_individual(d), f"{s}.pdf", "application/pdf")
            if c2.button("🗑️ Excluir"): delete_data("clientes", int(d['id'])); st.rerun()

elif menu == "💉 Procedimentos":
    st.title("Procedimentos")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("np"):
            n = st.text_input("Nome");
            v = st.number_input("R$");
            min = st.number_input("Min", 30)
            if st.form_submit_button("Salvar"): add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": min,
                                                                           "categoria": "Geral"}); st.rerun()
    with c2:
        df = get_data("procedimentos")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            d = st.selectbox("Excluir:", df['nome'].unique())
            if st.button("Deletar"): delete_data("procedimentos", int(df[df['nome'] == d]['id'].values[0])); st.rerun()

elif menu == "💰 Financeiro":
    st.title("Financeiro")
    t1, t2 = st.tabs(["Lançar", "Extrato"])
    with t1:
        with st.form("nf"):
            tp = st.selectbox("Tipo", ["Receita", "Despesa"]);
            ds = st.text_input("Desc")
            vl = st.number_input("Valor");
            dt = st.date_input("Data", value=data_hoje_br(), format="DD/MM/YYYY")
            ct = st.selectbox("Cat", ["Atendimento", "Custo Fixo", "Outros"])
            if st.form_submit_button("Lançar"): add_data("financeiro",
                                                         {"descricao": ds, "valor": vl, "tipo": tp, "categoria": ct,
                                                          "data_movimento": str(dt),
                                                          "forma_pagamento": "Dinheiro"}); st.rerun()
    with t2:
        df = get_data("financeiro")
        if not df.empty:
            m = st.slider("Mês", 1, 12, data_hoje_br().month)
            df['d'] = pd.to_datetime(df['data_movimento']);
            r = df[df['d'].dt.month == m]
            st.dataframe(r[['id', 'data_movimento', 'tipo', 'descricao', 'valor']], use_container_width=True)
            st.download_button("Excel", to_excel(r), "fin.xlsx")
            i = st.number_input("ID Excluir", min_value=0)
            if st.button("Apagar"): delete_data("financeiro", int(i)); st.rerun()

elif menu == "📑 Relatórios":
    st.title("Relatórios")
    d1 = st.date_input("De", value=data_hoje_br().replace(day=1), format="DD/MM/YYYY")
    d2 = st.date_input("Até", value=data_hoje_br(), format="DD/MM/YYYY")
    if st.button("Gerar"):
        df = get_data("financeiro");
        r = df[(df['data_movimento'] >= str(d1)) & (df['data_movimento'] <= str(d2))]
        st.dataframe(r);
        st.download_button("Excel", to_excel(r), "rel.xlsx")

elif menu == "🎂 Insights":
    st.title("Aniversariantes")
    df = get_data("clientes")
    if not df.empty:
        meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        m = data_hoje_br().month
        df['dob'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
        ani = df[df['dob'].dt.month == m].sort_values('dob')
        if not ani.empty:
            st.balloons();
            st.success(f"{len(ani)} aniversariantes em {meses[m]}!")
            for i, r in ani.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.markdown(f"**Dia {r['dob'].day}:** {r['nome']}");
                    c2.markdown(f"📞 {r['telefone']}")
                    if r['telefone']: c3.link_button("🎁 Zap",
                                                     f"https://wa.me/55{limpar_telefone(r['telefone'])}?text=Parabéns {r['nome']}!")
        else:
            st.info(f"Ninguém em {meses[m]}.")