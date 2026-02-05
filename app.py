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
# 1. CONFIGURAÇÕES INICIAIS
# ==============================================================================
st.set_page_config(page_title="Bárbara Castro Estética", layout="wide", page_icon="✨")

st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #D4AF37; text-align: center; font-weight: bold;}
    .metric-box {border: 1px solid #e6e6e6; padding: 20px; border-radius: 10px; background-color: #f9f9f9;}
    div[data-testid="stMetricValue"] {color: #D4AF37;}
    </style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False


def check_login():
    st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login"):
            u = st.text_input("Usuário");
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                try:
                    if u == st.secrets["admin"]["usuario"] and p == st.secrets["admin"]["senha"]:
                        st.session_state["logado"] = True;
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")
                except:
                    st.error("Erro no secrets.toml")


if not st.session_state["logado"]: check_login(); st.stop()

# ==============================================================================
# 2. CONEXÃO E FUNÇÕES
# ==============================================================================
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'


def data_hoje_br(): return (datetime.utcnow() - timedelta(hours=3)).date()


@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None


supabase = init_supabase()


def get_data(t): return pd.DataFrame(
    supabase.table(t).select("*").order("id").execute().data) if supabase else pd.DataFrame()


def add_data(t, d): supabase.table(t).insert(d).execute() if supabase else None; return True


def update_data(t, i, d): supabase.table(t).update(d).eq("id", i).execute() if supabase else None; return True


def delete_data(t, i): supabase.table(t).delete().eq("id", i).execute() if supabase else None; return True


def limpar_telefone(t): return ''.join(filter(str.isdigit, str(t))) if t else ""


# --- INTELIGÊNCIA: CÁLCULO DE RISCO DE ABANDONO (CHURN) ---
def calcular_churn(df_agenda, df_clientes):
    """
    Analisa o histórico de cada cliente para prever quem está sumido.
    Retorna: DataFrame com clientes em risco.
    """
    if df_agenda.empty: return pd.DataFrame()

    # 1. Prepara os dados
    df = df_agenda.copy()
    df['dt'] = pd.to_datetime(df['data_agendamento'])
    df = df[df['status'] == 'Concluído'].sort_values('dt')  # Só conta visitas reais

    risco_lista = []
    hoje = pd.to_datetime(data_hoje_br())

    # 2. Analisa cliente por cliente
    for nome_cli in df['cliente_nome'].unique():
        historico = df[df['cliente_nome'] == nome_cli]

        # Só analisa quem veio pelo menos 2 vezes (senão não tem média)
        if len(historico) >= 2:
            datas = historico['dt'].dt.date.tolist()
            # Calcula a diferença média entre visitas (Ciclo da Cliente)
            diferencas = [(datas[i] - datas[i - 1]).days for i in range(1, len(datas))]
            media_frequencia = sum(diferencas) / len(diferencas)

            # Última visita
            ultima_visita = historico['dt'].max()
            dias_sem_vir = (hoje - ultima_visita).days

            # A REGRA DE OURO: Se sumiu por mais de 2x o ciclo normal dela = RISCO ALTO
            # Se sumiu por mais de 1.5x o ciclo = RISCO MÉDIO
            # (Adicionamos +15 dias de margem mínima para não alarmar à toa)
            limite_alerta = max(media_frequencia * 1.5, 30)

            if dias_sem_vir > limite_alerta:
                # Busca telefone
                tel = df_clientes[df_clientes['nome'] == nome_cli]['telefone'].values
                tel = tel[0] if len(tel) > 0 else ""

                risco_lista.append({
                    "Cliente": nome_cli,
                    "Última Visita": ultima_visita.strftime('%d/%m/%Y'),
                    "Dias Sumida": dias_sem_vir,
                    "Frequência Normal": f"A cada {int(media_frequencia)} dias",
                    "Telefone": tel,
                    "Risco": "ALTO" if dias_sem_vir > (media_frequencia * 2) else "Médio"
                })

    return pd.DataFrame(risco_lista).sort_values('Dias Sumida', ascending=False)


def gerar_ficha_individual(d):
    pdf = FPDF();
    pdf.add_page();
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 18);
    pdf.cell(0, 10, "Bárbara Castro Estética Avançada".encode('latin-1', 'replace').decode('latin-1'), ln=True,
             align='C')
    pdf.set_font("Arial", 'I', 12);
    pdf.cell(0, 10, "Ficha de Anamnese".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(15);
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "DADOS:", ln=True);
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(5)
    pdf.set_font("Arial", size=12);
    pdf.cell(0, 8, f"Nome: {d['nome']}".encode('latin-1', 'replace').decode('latin-1'), ln=True)
    pdf.ln(10);
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "HISTÓRICO:", ln=True);
    pdf.line(10, pdf.get_y(), 200, pdf.get_y());
    pdf.ln(5)
    pdf.set_font("Arial", size=11);
    pdf.multi_cell(0, 8, txt=str(d.get('anamnese', '')).encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')


def to_excel(df):
    o = io.BytesIO();
    with pd.ExcelWriter(o, engine='xlsxwriter') as w: df.to_excel(w, index=False)
    return o.getvalue()


def enviar_agenda_email():
    try:
        df = get_data("agenda");
        hj = str(data_hoje_br())
        df = df[df['data_agendamento'] == hj] if not df.empty else pd.DataFrame()
        msg = MIMEMultipart();
        msg['Subject'] = f"Agenda {hj}";
        msg['From'] = EMAIL_REMETENTE;
        msg['To'] = EMAIL_DESTINATARIO
        html = f"<h3>Agenda {hj}</h3>" + (df.to_html() if not df.empty else "Livre")
        msg.attach(MIMEText(html, 'html'));
        s = smtplib.SMTP('smtp.gmail.com', 587);
        s.starttls();
        s.login(EMAIL_REMETENTE, EMAIL_SENHA);
        s.send_message(msg);
        s.quit()
        return "✅ Enviado!"
    except Exception as e:
        return f"❌ Erro: {e}"


if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email": st.write(
    enviar_agenda_email()); st.stop()

# ==============================================================================
# 3. INTERFACE (SIDEBAR)
# ==============================================================================
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=150)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)
    st.markdown("### Bárbara Castro")
    if st.button("🚪 Sair"): st.session_state["logado"] = False; st.rerun()
    st.markdown("---")
    menu = st.radio("MENU", ["📊 Dashboard", "📅 Agenda", "👥 Clientes", "💉 Procedimentos", "💰 Financeiro", "📑 Relatórios",
                             "🧠 Insights IA"])
    st.markdown("---")
    if st.button("🔄 Atualizar"): st.rerun()

# ==============================================================================
# 4. PÁGINAS DO SISTEMA
# ==============================================================================

if menu == "📊 Dashboard":
    st.markdown("<div class='main-header'>Painel de Controle</div>", unsafe_allow_html=True)
    df_ag = get_data("agenda");
    df_fin = get_data("financeiro");
    hj = str(data_hoje_br())

    ag = len(df_ag[df_ag['data_agendamento'] == hj]) if not df_ag.empty else 0
    rec, des = 0.0, 0.0

    if not df_fin.empty:
        df_fin['dt'] = pd.to_datetime(df_fin['data_movimento'])
        mes_atual = df_fin[df_fin['dt'].dt.month == data_hoje_br().month]
        rec = mes_atual[mes_atual['tipo'] == 'Receita']['valor'].sum()
        des = mes_atual[mes_atual['tipo'] == 'Despesa']['valor'].sum()

    st.markdown(f"### 🗓️ Fevereiro / {data_hoje_br().year}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agenda Hoje", ag);
    c2.metric("Receita Mês", f"R$ {rec:,.2f}")
    c3.metric("Despesas Mês", f"R$ {des:,.2f}");
    c4.metric("Lucro", f"R$ {rec - des:,.2f}")

    st.divider()
    st.subheader("🛑 Contas a Pagar (HOJE)")
    if not df_fin.empty:
        vence_hj = df_fin[(df_fin['tipo'] == 'Despesa') & (df_fin['dt'].dt.date == data_hoje_br())]
        if not vence_hj.empty:
            for i, r in vence_hj.iterrows(): st.error(f"💸 {r['descricao']} - R$ {r['valor']}")
        else:
            st.success("Nenhuma conta vence hoje!")

elif menu == "📅 Agenda":
    st.title("Agenda")
    t1, t2, t3 = st.tabs(["Visual", "Lista", "Novo"])
    df_ag = get_data("agenda");
    df_cli = get_data("clientes");
    df_proc = get_data("procedimentos")

    with t1:
        if not df_ag.empty:
            ev = [{"title": f"{r['cliente_nome']}", "start": f"{r['data_agendamento']}T{r['hora_agendamento']}",
                   "backgroundColor": "#28a745" if r['status'] == "Concluído" else "#dc3545" if r[
                                                                                                    'status'] == "Cancelado" else "#3788d8"}
                  for i, r in df_ag.iterrows()]
            calendar(events=ev, options={
                "headerToolbar": {"left": "title", "center": "", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
                "initialView": "timeGridWeek", "locale": "pt-br"}, key=f"c{len(ev)}")
    with t2:
        if not df_ag.empty:
            ed = st.data_editor(df_ag[['id', 'data_agendamento', 'hora_agendamento', 'cliente_nome', 'status']],
                                hide_index=True, key="ed_ag")
            if st.button("💾 Salvar"):
                # Lógica simples de update
                for i, r in ed.iterrows(): update_data("agenda", int(r['id']), {"status": r['status']})
                st.success("Salvo!");
                time.sleep(1);
                st.rerun()
            i = st.selectbox("Excluir ID:", df_ag['id'].unique())
            if st.button("🗑️ Apagar"): delete_data("agenda", int(i)); time.sleep(1); st.rerun()
    with t3:
        with st.form("novo"):
            c = st.selectbox("Cliente", df_cli['nome'].unique()) if not df_cli.empty else None
            p = st.selectbox("Proc", df_proc['nome'].unique()) if not df_proc.empty else None
            d = st.date_input("Data", data_hoje_br());
            h = st.time_input("Hora")
            if st.form_submit_button("Agendar") and c and p:
                add_data("agenda", {"cliente_nome": c, "procedimento_nome": p, "data_agendamento": str(d),
                                    "hora_agendamento": str(h), "status": "Agendado", "valor_cobrado": 0})
                st.success("Ok!");
                time.sleep(1);
                st.rerun()

elif menu == "👥 Clientes":
    st.title("Clientes");
    t1, t2 = st.tabs(["Novo", "Gerenciar"])
    with t1:
        with st.form("nc"):
            n = st.text_input("Nome");
            t = st.text_input("Zap");
            e = st.text_input("Email");
            dt = st.date_input("Nasc", value=None)
            if st.form_submit_button("Salvar") and n: add_data("clientes", {"nome": n, "telefone": t, "email": e,
                                                                            "data_nascimento": str(dt)}); st.rerun()
    with t2:
        df = get_data("clientes")
        if not df.empty:
            s = st.selectbox("Editar:", df['nome'].unique())
            d = df[df['nome'] == s].iloc[0]
            with st.form("ec"):
                nn = st.text_input("Nome", d['nome']);
                nt = st.text_input("Zap", d['telefone']);
                ne = st.text_input("Email", d['email'])
                if st.form_submit_button("Salvar"): update_data("clientes", int(d['id']),
                                                                {"nome": nn, "telefone": nt, "email": ne}); st.rerun()
            c1, c2 = st.columns(2)
            c1.download_button("PDF", gerar_ficha_individual(d), "ficha.pdf")
            if c2.button("🗑️ Excluir"): delete_data("clientes", int(d['id'])); time.sleep(1); st.rerun()

elif menu == "💉 Procedimentos":
    st.title("Procedimentos")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("np"):
            n = st.text_input("Nome");
            v = st.number_input("Valor")
            if st.form_submit_button("Salvar"): add_data("procedimentos", {"nome": n, "valor": v}); st.rerun()
    with c2:
        df = get_data("procedimentos")
        if not df.empty:
            st.dataframe(df);
            d = st.selectbox("Del:", df['nome'].unique())
            if st.button("X"): delete_data("procedimentos", int(df[df['nome'] == d]['id'].values[0])); st.rerun()

elif menu == "💰 Financeiro":
    st.title("Financeiro");
    t1, t2 = st.tabs(["Lançar", "Extrato"])
    with t1:
        with st.form("nf"):
            tp = st.selectbox("Tipo", ["Receita", "Despesa"]);
            ds = st.text_input("Desc");
            vl = st.number_input("R$");
            dt = st.date_input("Data", data_hoje_br())
            if st.form_submit_button("Salvar"): add_data("financeiro", {"tipo": tp, "descricao": ds, "valor": vl,
                                                                        "data_movimento": str(dt)}); st.rerun()
    with t2:
        df = get_data("financeiro")
        if not df.empty: st.dataframe(df); st.download_button("Excel", to_excel(df), "fin.xlsx")

elif menu == "📑 Relatórios":
    st.title("Relatórios");
    d1 = st.date_input("De");
    d2 = st.date_input("Até")
    if st.button("Gerar Financeiro"):
        df = get_data("financeiro");
        st.dataframe(df[(df['data_movimento'] >= str(d1)) & (df['data_movimento'] <= str(d2))])

# --- NOVA ABA: INSIGHTS COM IA (RISCO DE CHURN + ANIVERSARIANTES) ---
elif menu == "🧠 Insights IA":
    st.title("🧠 Inteligência do Negócio")

    tab_ani, tab_churn = st.tabs(["🎂 Aniversariantes", "🚨 Risco de Abandono (Churn)"])

    # 1. Aniversariantes
    with tab_ani:
        df = get_data("clientes")
        if not df.empty:
            mes = data_hoje_br().month
            df['dob'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
            ani = df[df['dob'].dt.month == mes].sort_values('dob')
            if not ani.empty:
                st.balloons()
                for i, r in ani.iterrows():
                    st.info(
                        f"🎉 **Dia {r['dob'].day}:** {r['nome']} — [Enviar Zap](https://wa.me/55{limpar_telefone(r['telefone'])}?text=Parabéns!)")
            else:
                st.write("Sem aniversariantes este mês.")

    # 2. Risco de Churn (NOVO!)
    with tab_churn:
        st.markdown("### 🕵️‍♀️ Clientes com Risco de te Abandonar")
        st.markdown(
            "A IA analisou a frequência de cada cliente. Se ela sumiu por mais tempo que o normal dela, aparece aqui.")

        df_ag = get_data("agenda")
        df_cli = get_data("clientes")

        if not df_ag.empty and not df_cli.empty:
            tabela_risco = calcular_churn(df_ag, df_cli)

            if not tabela_risco.empty:
                for i, row in tabela_risco.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.markdown(f"**👤 {row['Cliente']}**")
                        c1.caption(f"Última visita: {row['Última Visita']}")

                        c2.markdown(f"⚠️ **Sumiu há {row['Dias Sumida']} dias**")
                        c2.caption(f"Costuma vir: {row['Frequência Normal']}")

                        # Botão de Ação (Recuperação)
                        zap = limpar_telefone(row['Telefone'])
                        msg = f"Olá {row['Cliente']}! Sentimos sua falta. Que tal agendar um retorno com condição especial?"
                        link = f"https://wa.me/55{zap}?text={msg}"
                        c3.link_button("💌 Recuperar Cliente", link)
            else:
                st.success("Maravilha! Todas as suas clientes recorrentes estão em dia. Ninguém em risco alto.")
        else:
            st.warning("Preciso de mais dados na Agenda para calcular a média de frequência.")