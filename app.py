import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# Tenta importar FPDF
try:
    from fpdf import FPDF
except:
    pass

# --- CONFIGURAÇÃO DE E-MAIL ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada Bárbara Castro", layout="wide", page_icon="✨")

# --- DESIGN VISUAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600;700&display=swap');
    .stApp { background: linear-gradient(135deg, #fffcf9 0%, #fcf5f0 50%, #f4eadd 100%); font-family: 'Inter', sans-serif; color: #4a4a4a; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #2c2c2c; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #f0e6d2; }
    .stButton>button { background: linear-gradient(90deg, #d4af37 0%, #e6c86e 100%); color: white; border: none; border-radius: 8px; font-weight: 500; width: 100%; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(212, 175, 55, 0.3); }
    [data-testid="stMetric"] { background-color: rgba(255,255,255,0.8); border-radius: 12px; border: 1px solid #f5efe6; padding: 10px; }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.9); border-radius: 15px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
# A conexão é criada uma vez e usada no app todo
conn = st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet):
    # ttl=0 garante que os dados sejam sempre frescos (sem cache)
    try:
        return conn.read(worksheet=worksheet, ttl=0)
    except Exception:
        return pd.DataFrame()


def add_data(worksheet, new_data_dict):
    try:
        df = get_data(worksheet)
        # Gera ID automático (Max ID + 1)
        if not df.empty and 'id' in df.columns:
            new_id = df['id'].max() + 1
        else:
            new_id = 1

        new_data_dict['id'] = new_id
        new_row = pd.DataFrame([new_data_dict])

        # Concatena e salva
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet=worksheet, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def update_data(worksheet, id_to_update, update_dict):
    try:
        df = get_data(worksheet)
        if df.empty: return False

        # Encontra a linha pelo ID e atualiza
        idx = df.index[df['id'] == id_to_update].tolist()
        if not idx: return False

        for key, value in update_dict.items():
            df.at[idx[0], key] = value

        conn.update(worksheet=worksheet, data=df)
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False


def delete_data(worksheet, id_to_delete):
    try:
        df = get_data(worksheet)
        if df.empty: return False

        # Filtra removendo o ID selecionado
        updated_df = df[df['id'] != id_to_delete]
        conn.update(worksheet=worksheet, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False


# --- FUNÇÃO DE E-MAIL (ADAPTADA PARA SHEETS) ---
def enviar_agenda_email():
    try:
        hoje = str(date.today())
        df_agenda = get_data("agenda")

        # Filtra agenda de hoje
        if not df_agenda.empty:
            # Converte coluna data para string para comparar
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
            corpo_html = f"<h3>Bom dia! ☀️</h3><p>Não há clientes agendados para hoje ({datetime.now().strftime('%d/%m')}).</p>"
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
        return "✅ E-mail enviado!"
    except Exception as e:
        return f"❌ Erro: {e}"


# --- GATILHO EXTERNO ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    res = enviar_agenda_email()
    st.write(res);
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=130)
    else:
        st.markdown("### 👑 Bárbara Castro")
    menu = st.radio("NAVEGAÇÃO", ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios"])
    st.markdown("---")
    if st.button("🔄 Forçar Atualização"): st.rerun()

# --- PÁGINAS ---
if menu == "Dashboard":
    st.title("Bem-vinda, Bárbara")
    df_ag = get_data("agenda")
    total_fat = 0.0
    ag_hoje = 0

    if not df_ag.empty:
        df_ag['data_agendamento'] = df_ag['data_agendamento'].astype(str)
        # Calcula faturamento (Status Concluído) - precisa cruzar com valor do procedimento se não salvou na agenda
        # Simplificação: Vamos pegar só os agendamentos e fazer métricas simples
        ag_hoje = len(df_ag[df_ag['data_agendamento'] == str(date.today())])

        # Para faturamento preciso, ideal é salvar o valor na tabela agenda na hora de criar.
        # Aqui faremos uma estimativa baseada nos procedimentos
        df_proc = get_data("procedimentos")
        if not df_proc.empty and 'valor' in df_proc.columns:
            # Merge para pegar valores
            df_merged = pd.merge(df_ag, df_proc, left_on='procedimento_id', right_on='id', suffixes=('', '_proc'))
            total_fat = df_merged[df_merged['status'] == 'Concluído']['valor'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Total", f"R$ {total_fat:,.2f}")
    c2.metric("Agendados Hoje", ag_hoje)
    c3.metric("Dia", date.today().strftime('%d/%m'))

elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Agendar", "Gerenciar"])

    with t1:
        c1, c2 = st.columns([1, 2])
        df_cli = get_data("clientes")
        df_proc = get_data("procedimentos")

        with c1:
            if not df_cli.empty and not df_proc.empty:
                with st.form("new_ag"):
                    # Cria dicionários para seleção
                    cli_dict = {f"{row['nome']}": row['id'] for i, row in df_cli.iterrows()}
                    proc_dict = {f"{row['nome']} - R$ {row['valor']}": row['id'] for i, row in df_proc.iterrows()}

                    c_nome = st.selectbox("Cliente", list(cli_dict.keys()))
                    p_nome = st.selectbox("Procedimento", list(proc_dict.keys()))
                    d = st.date_input("Data", format="DD/MM/YYYY")
                    h = st.time_input("Hora")

                    if st.form_submit_button("Agendar"):
                        # Salva ID e Nome para facilitar leitura (desnormalização leve para performance)
                        dados = {
                            "cliente_id": cli_dict[c_nome],
                            "cliente_nome": c_nome,
                            "procedimento_id": proc_dict[p_nome],
                            "procedimento_nome": p_nome.split(" - ")[0],
                            "data_agendamento": str(d),
                            "hora_agendamento": str(h),
                            "status": "Agendado"
                        }
                        if add_data("agenda", dados):
                            st.success("Agendado!");
                            time.sleep(1);
                            st.rerun()
            else:
                st.warning("Cadastre clientes e procedimentos primeiro.")

        with c2:
            df_ag = get_data("agenda")
            if not df_ag.empty:
                # Ordena por data e hora
                df_ag = df_ag.sort_values(by=['data_agendamento', 'hora_agendamento'], ascending=False)
                st.dataframe(
                    df_ag[['data_agendamento', 'hora_agendamento', 'cliente_nome', 'procedimento_nome', 'status']],
                    use_container_width=True, hide_index=True)

    with t2:
        df_ag = get_data("agenda")
        if not df_ag.empty:
            df_ag['display'] = df_ag.apply(lambda
                                               x: f"{x['data_agendamento']} - {str(x['hora_agendamento'])[:5]} - {x['cliente_nome']} ({x['status']})",
                                           axis=1)
            ag_selecionado = st.selectbox("Selecione para editar:", df_ag['display'].tolist())

            # Pega o ID do selecionado
            id_ag = df_ag[df_ag['display'] == ag_selecionado]['id'].values[0]

            c1, c2 = st.columns(2)
            if c1.button("✅ Marcar Concluído"):
                update_data("agenda", id_ag, {"status": "Concluído"})
                st.success("Atualizado!");
                time.sleep(1);
                st.rerun()

            if c2.button("🗑️ Excluir"):
                delete_data("agenda", id_ag)
                st.success("Excluído!");
                time.sleep(1);
                st.rerun()
        else:
            st.info("Nenhum agendamento.")

elif menu == "Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Novo", "Editar"])

    with t1:
        with st.form("nc"):
            n = st.text_input("Nome")
            t = st.text_input("Telefone")
            e = st.text_input("Email")
            d = st.date_input("Nascimento", min_value=date(1920, 1, 1))
            a = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                dados = {"nome": n, "telefone": t, "email": e, "data_nascimento": str(d), "anamnese": a,
                         "created_at": str(datetime.now())}
                if add_data("clientes", dados): st.success("Salvo!"); st.rerun()

    with t2:
        df = get_data("clientes")
        if not df.empty:
            c_sel = st.selectbox("Cliente", df['nome'].tolist())
            row = df[df['nome'] == c_sel].iloc[0]
            with st.form("ec"):
                nn = st.text_input("Nome", row['nome'])
                nt = st.text_input("Tel", row['telefone'])
                na = st.text_area("Anamnese", row['anamnese'])
                if st.form_submit_button("Atualizar"):
                    update_data("clientes", row['id'], {"nome": nn, "telefone": nt, "anamnese": na})
                    st.success("Atualizado!");
                    st.rerun()
            if st.button("Excluir Cliente"):
                delete_data("clientes", row['id'])
                st.rerun()

elif menu == "Procedimentos":
    st.title("Serviços")
    with st.form("np"):
        n = st.text_input("Nome");
        v = st.number_input("Valor");
        d = st.number_input("Minutos", step=15)
        if st.form_submit_button("Salvar"):
            if add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d, "categoria": "Geral"}):
                st.success("Salvo!");
                st.rerun()
    st.dataframe(get_data("procedimentos"), use_container_width=True)

elif menu == "Financeiro":
    st.title("Financeiro")
    t1, t2 = st.tabs(["Lançar Despesa", "Extrato"])
    with t1:
        with st.form("desp"):
            d = st.text_input("Descrição");
            v = st.number_input("Valor");
            dt = st.date_input("Data")
            if st.form_submit_button("Lançar"):
                if add_data("despesas", {"descricao": d, "valor": v, "data_despesa": str(dt), "categoria": "Geral",
                                         "created_at": str(datetime.now())}):
                    st.success("Lançado!");
                    st.rerun()
    with t2:
        st.dataframe(get_data("despesas"), use_container_width=True)

elif menu == "Relatórios":
    st.title("Relatórios")
    st.info("Para relatórios avançados, acesse diretamente a Planilha do Google conectada.")
    st.markdown(f"[Abrir Planilha no Google Sheets]({st.secrets['connections']['gsheets']['spreadsheet']})")