import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulador Petrográfico Avanzado", layout="wide")

st.title("🔬 Simulador Petrográfico de Sección Delgada")
st.write("Configurá tu paragénesis mineral, hábitos cristalinos y recorré la muestra con la platina móvil del microscopio.")

# --- INICIALIZACIÓN DE ESTADO ---
if 'minerales' not in st.session_state:
    st.session_state.minerales = [
        {"nombre": "Plagioclasa / Sanidino", "pct": 35.0, "habito": "Tabular (2:1)", "color": "#d9822b"},
        {"nombre": "Anfíbol / Piroxeno", "pct": 20.0, "habito": "Prismático (3.5:1)", "color": "#262626"},
        {"nombre": "Cuarzo", "pct": 25.0, "habito": "Anhedral / Intersticial", "color": "#a8c5da"},
        {"nombre": "Titanita (Accesorio)", "pct": 3.0, "habito": "Prismático (3.5:1)", "color": "#8a5a2b"},
    ]

if 'semilla_roca' not in st.session_state:
    st.session_state.semilla_roca = 42

# --- PANEL LATERAL: CONFIGURACIÓN DE PARAGÉNESIS ---
st.sidebar.header("⚙️ Paragénesis Mineral")

if st.sidebar.button("+ Agregar Mineral"):
    st.session_state.minerales.append(
        {"nombre": f"Mineral {len(st.session_state.minerales)+1}", "pct": 5.0, "habito": "Prismático (3.5:1)", "color": "#555555"}
    )

indices_a_eliminar = []

for idx, min_item in enumerate(st.session_state.minerales):
    with st.sidebar.expander(f"💎 {min_item['nombre']}", expanded=False):
        min_item['nombre'] = st.text_input("Nombre", min_item['nombre'], key=f"nom_{idx}")
        min_item['pct'] = st.slider("Porcentaje (%)", 0.0, 60.0, float(min_item['pct']), step=1.0, key=f"pct_{idx}")
        min_item['habito'] = st.selectbox(
            "Hábito Cristalino", 
            ["Prismático (3.5:1)", "Tabular (2:1)", "Equidimensional (1:1)", "Anhedral / Intersticial"],
            index=["Prismático (3.5:1)", "Tabular (2:1)", "Equidimensional (1:1)", "Anhedral / Intersticial"].index(min_item['habito']),
            key=f"hab_{idx}"
        )
        min_item['color'] = st.color_picker("Color de Interferencias/PPL", min_item['color'], key=f"col_{idx}")
        
        if st.button("Eliminar Mineral", key=f"del_{idx}"):
            indices_a_eliminar.append(idx)

for idx in reversed(indices_a_eliminar):
    st.session_state.minerales.pop(idx)
    st.rerun()

st.sidebar.markdown("---")
granulometria_global = st.sidebar.selectbox("Granulometría Global", ["Fino", "Medio", "Grueso"], index=1)
if st.sidebar.button("🎲 Regenerar Muestra Aleatoria"):
    st.session_state.semilla_roca = np.random.randint(1, 99999)

# --- GENERACIÓN DE LA MATRIZ DE LA SECCIÓN DELGADA ---
np.random.seed(st.session_state.semilla_roca)
tam_muestra = 700
y_m, x_m = np.ogrid[0:tam_muestra, 0:tam_muestra]
matriz_completa = np.zeros((tam_muestra, tam_muestra), dtype=int)

escala_grano = {"Fino": 25, "Medio": 45, "Grueso": 80}[granulometria_global]

dict_habito = {
    "Prismático (3.5:1)": (3.5, 0.8, 'rect'),
    "Tabular (2:1)": (2.0, 1.0, 'rect'),
    "Equidimensional (1:1)": (1.1, 1.1, 'rect'),
    "Anhedral / Intersticial": (1.2, 1.2, 'oval')
}

colores_rgb = [[0.95, 0.95, 0.95]]  # ID 0: Matriz/Pasta (Gris muy claro)

for i, min_item in enumerate(st.session_state.minerales, start=1):
    hex_c = min_item['color'].lstrip('#')
    rgb = [int(hex_c[j:j+2], 16)/255.0 for j in (0, 2, 4)]
    colores_rgb.append(rgb)

    pct_target = min_item['pct']
    if pct_target <= 0:
        continue

    px_target = (pct_target / 100.0) * (tam_muestra ** 2)
    px_acum = 0
    intentos = 0
    max_intentos = 2000

    aspect_w, aspect_h, tipo_f = dict_habito[min_item['habito']]

    while px_acum < px_target and intentos < max_intentos:
        intentos += 1
        cx, cy = np.random.randint(40, tam_muestra-40), np.random.randint(40, tam_muestra-40)

        w = np.random.uniform(escala_grano * 0.7, escala_grano * 1.3) * aspect_w
        h = np.random.uniform(escala_grano * 0.7, escala_grano * 1.3) * aspect_h
        ang = np.random.uniform(0, np.pi)

        xr = (x_m - cx) * np.cos(ang) + (y_m - cy) * np.sin(ang)
        yr = -(x_m - cx) * np.sin(ang) + (y_m - cy) * np.cos(ang)

        if tipo_f == 'oval':
            figura = ((xr / (w/2))**2 + (yr / (h/2))**2) <= 1.0
        else:
            figura = (np.abs(xr) <= w/2) & (np.abs(yr) <= h/2)

        nuevos_px = figura & (matriz_completa == 0)
        if np.any(nuevos_px):
            matriz_completa[nuevos_px] = i
            px_acum += np.sum(nuevos_px)

# --- CONTROLES DE LA PLATINA DEL MICROSCOPIO ---
col_visor, col_panel = st.columns([1.2, 1])

with col_panel:
    st.subheader("🕹️ Platina del Microscopio")
    pos_x = st.slider("Eje X (Izquierda / Derecha)", 80, tam_muestra - 80, tam_muestra // 2)
    pos_y = st.slider("Eje Y (Arriba / Abajo)", 80, tam_muestra - 80, tam_muestra // 2)
    radio_fov = st.slider("Campo Visual / Aumento (Diámetro)", 50, 180, 90)

    st.markdown("---")
    st.subheader("👁️ Modo Desafío (Entrenamiento)")
    modo_ciego = st.checkbox("Ocultar porcentajes reales para evaluar mi ojo")

# --- RENDERIZADO DEL CAMPO VISUAL (OCULAR) ---
fov_mask = ((x_m - pos_x)**2 + (y_m - pos_y)**2) <= radio_fov**2

canvas_fov = np.zeros((tam_muestra, tam_muestra, 3))
for id_m, color in enumerate(colores_rgb):
    canvas_fov[matriz_completa == id_m] = color

canvas_fov[~fov_mask] = [0.05, 0.05, 0.05]

margin = radio_fov + 25
ymin, ymax = max(0, pos_y - margin), min(tam_muestra, pos_y + margin)
xmin, xmax = max(0, pos_x - margin), min(tam_muestra, pos_x + margin)

with col_visor:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(canvas_fov[ymin:ymax, xmin:xmax])
    ax.axis('off')
    st.pyplot(fig)

# --- RESULTADOS Y MEDICIÓN REAL ---
if not modo_ciego:
    st.markdown("---")
    st.subheader("📊 Composición Modal Real de la Sección Delgada")
    if len(st.session_state.minerales) > 0:
        cols_res = st.columns(min(len(st.session_state.minerales) + 1, 5))
        total_area = tam_muestra * tam_muestra
        for idx, min_item in enumerate(st.session_state.minerales, start=1):
            px_m = np.sum(matriz_completa == idx)
            pct_m = (px_m / total_area) * 100
            col_target = cols_res[(idx-1) % len(cols_res)]
            col_target.metric(label=min_item['nombre'], value=f"{pct_m:.1f}%")
            
        px_pasta = np.sum(matriz_completa == 0)
        col_target = cols_res[len(st.session_state.minerales) % len(cols_res)]
        col_target.metric(label="Matriz / Pasta de Roca", value=f"{(px_pasta/total_area)*100:.1f}%")
