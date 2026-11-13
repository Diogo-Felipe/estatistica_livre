"""Identidade visual do aplicativo (CSS injetado uma vez por execução).

Modo claro/escuro: o Streamlit define `color-scheme` em `.stApp` conforme o tema ativo
(sistema ou escolha manual em ⋮ > Settings). Os tokens abaixo usam `light-dark()`,
que acompanha esse valor sem depender de detecção no Python. Navegadores sem
`light-dark()` mantêm a paleta clara.
"""
import streamlit as st

CSS = """
<style>
.stApp{
  --el-primary-dark:#145a6b; --el-primary:#1C7C92; --el-accent:#145a6b;
  --el-ink:#142C36; --el-muted:#5b707b; --el-line:#dce8ec; --el-soft:#f4f9fa; --el-card:#ffffff;
  --el-ok:#1f7a4d; --el-ok-bg:#eaf6ef; --el-ok-ink:#124a2f;
  --el-warn:#9a5b00; --el-warn-bg:#fff4e0; --el-warn-ink:#5f3800;
  --el-neutral:#7d93a0; --el-neutral-bg:#eef3f6; --el-neutral-ink:#24313c;
}
@supports (color: light-dark(#000, #fff)){
  .stApp{
    --el-primary-dark:light-dark(#145a6b,#0f4452); --el-primary:light-dark(#1C7C92,#17697c);
    --el-accent:light-dark(#145a6b,#7fd0e2);
    --el-ink:light-dark(#142C36,#E6EEF1); --el-muted:light-dark(#5b707b,#9db3bd);
    --el-line:light-dark(#dce8ec,#2a3f49); --el-soft:light-dark(#f4f9fa,#16262E); --el-card:light-dark(#ffffff,#13222a);
    --el-ok:light-dark(#1f7a4d,#3fae78); --el-ok-bg:light-dark(#eaf6ef,#12301f); --el-ok-ink:light-dark(#124a2f,#c4ecd6);
    --el-warn:light-dark(#9a5b00,#e0a030); --el-warn-bg:light-dark(#fff4e0,#3a2a08); --el-warn-ink:light-dark(#5f3800,#f6dba8);
    --el-neutral:light-dark(#7d93a0,#6f8795); --el-neutral-bg:light-dark(#eef3f6,#1c2c35); --el-neutral-ink:light-dark(#24313c,#dce6eb);
  }
}
/* margens: a barra de ferramentas do Streamlit fica transparente e baixa; o conteúdo sobe */
[data-testid='stHeader']{background:transparent;height:2.4rem;min-height:2.4rem}
.block-container{padding-top:1.4rem;padding-bottom:2rem;max-width:1400px}
[data-testid='stSidebarHeader']{height:2.4rem;padding:0 .75rem}
[data-testid='stSidebarUserContent']{padding-top:.25rem}
h1,h2,h3,h4,h5{letter-spacing:-.02em}
h5{margin-top:0}

/* cabeçalho compacto */
.el-header{display:flex;align-items:center;justify-content:space-between;gap:10px 18px;flex-wrap:wrap;
  padding:8px 16px;border-radius:12px;margin:0 0 10px;color:#fff;
  background:linear-gradient(120deg,var(--el-primary-dark),var(--el-primary))}
.el-title{display:flex;align-items:center;gap:8px}
.el-title h1{color:#fff;margin:0;padding:0;font-size:1.25rem;line-height:1.2;font-weight:700}
.el-logo{font-size:1.2rem}
.el-ver{background:rgba(255,255,255,.2);border-radius:6px;padding:1px 7px;font-size:.72rem}
.el-chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.el-chip{background:rgba(255,255,255,.17);border-radius:999px;padding:3px 11px;font-size:.8rem;white-space:nowrap}
.el-chip b{font-weight:700}
.el-chip-nome{max-width:26rem;overflow:hidden;text-overflow:ellipsis}

/* indicadores */
[data-testid='stMetric']{border:1px solid var(--el-line);border-radius:12px;padding:10px 14px;background:var(--el-soft)}
[data-testid='stMetricLabel']{opacity:.75}

/* abas e botões */
[data-testid='stTabs'] button{font-size:.95rem;font-weight:600;padding:10px 14px}
.stButton button,.stDownloadButton button{border-radius:8px;font-weight:600}
/* botão primário: texto escuro sobre o turquesa claro do modo escuro (contraste) */
[data-testid='stBaseButton-primary']:not(:disabled),[data-testid='stBaseButton-primary']:not(:disabled) p{color:light-dark(#ffffff,#0b1a20) !important}

/* gráficos: painel claro nos dois temas (a imagem tem fundo branco; o PNG exportado também) */
[data-testid='stImage'] img{background:#fff;border:1px solid var(--el-line);border-radius:10px;padding:4px}

/* cartões de resultado */
.el-card{border:1px solid var(--el-line);border-radius:14px;padding:16px 20px;background:var(--el-card);margin:6px 0 12px}
.el-card h4{margin:0 0 2px}
.el-sub{color:var(--el-muted);font-size:.86rem}
.el-concl{border-radius:10px;padding:12px 16px;margin:10px 0;font-size:.98rem;line-height:1.5;border-left:5px solid}
.el-concl.sucesso{background:var(--el-ok-bg);border-color:var(--el-ok);color:var(--el-ok-ink)}
.el-concl.aviso{background:var(--el-warn-bg);border-color:var(--el-warn);color:var(--el-warn-ink)}
.el-concl.neutro{background:var(--el-neutral-bg);border-color:var(--el-neutral);color:var(--el-neutral-ink)}
.el-guia{margin-bottom:14px;background:var(--el-soft);border:1px solid var(--el-line);border-radius:10px;padding:10px 14px;font-size:.9rem;line-height:1.55}
.el-guia b{color:var(--el-accent)}
.el-vazio{border:2px dashed var(--el-line);border-radius:14px;padding:28px;text-align:center;color:var(--el-muted)}
.small-note{font-size:.86rem;color:var(--el-muted)}
</style>
"""


def aplicar():
    st.markdown(CSS, unsafe_allow_html=True)
