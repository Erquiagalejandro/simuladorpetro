import streamlit as st
import numpy as np
import io
import base64
from PIL import Image
import streamlit.components.v1 as components

st.set_page_config(page_title="Simulador Petrográfico Táctil", layout="wide")

st.title("🔬 Simulador Petrográfico con Platina Táctil")
st.write("Configurá tu mineralogía en el menú lateral y **arrastrá con el dedo o mouse** sobre el ocular para recorrer la sección delgada.")

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

# --- PANEL LATERAL ---
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
        min_item['color'] = st.color_picker("Color PPL/XPL", min_item['color'], key=f"col_{idx}")
        
        if st.button("Eliminar Mineral", key=f"del_{idx}"):
            indices_a_eliminar.append(idx)

for idx in reversed(indices_a_eliminar):
    st.session_state.minerales.pop(idx)
    st.rerun()

st.sidebar.markdown("---")
granulometria_global = st.sidebar.selectbox("Granulometría Global", ["Fino", "Medio", "Grueso"], index=1)
if st.sidebar.button("🎲 Regenerar Muestra Aleatoria"):
    st.session_state.semilla_roca = np.random.randint(1, 99999)

# --- GENERACIÓN DE LA SECCIÓN DELGADA COMPLETA ---
np.random.seed(st.session_state.semilla_roca)
tam_muestra = 800
y_m, x_m = np.ogrid[0:tam_muestra, 0:tam_muestra]
matriz_completa = np.zeros((tam_muestra, tam_muestra), dtype=int)

escala_grano = {"Fino": 30, "Medio": 55, "Grueso": 95}[granulometria_global]

dict_habito = {
    "Prismático (3.5:1)": (3.5, 0.8, 'rect'),
    "Tabular (2:1)": (2.0, 1.0, 'rect'),
    "Equidimensional (1:1)": (1.1, 1.1, 'rect'),
    "Anhedral / Intersticial": (1.2, 1.2, 'oval')
}

colores_rgb = [[242, 242, 242]]  # ID 0: Pasta/Matriz

for i, min_item in enumerate(st.session_state.minerales, start=1):
    hex_c = min_item['color'].lstrip('#')
    rgb = [int(hex_c[j:j+2], 16) for j in (0, 2, 4)]
    colores_rgb.append(rgb)

    pct_target = min_item['pct']
    if pct_target <= 0:
        continue

    px_target = (pct_target / 100.0) * (tam_muestra ** 2)
    px_acum = 0
    intentos = 0
    max_intentos = 2500

    aspect_w, aspect_h, tipo_f = dict_habito[min_item['habito']]

    while px_acum < px_target and intentos < max_intentos:
        intentos += 1
        cx, cy = np.random.randint(50, tam_muestra-50), np.random.randint(50, tam_muestra-50)

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

# Convertir la matriz completa a Imagen RGB en memoria
img_rgb = np.zeros((tam_muestra, tam_muestra, 3), dtype=np.uint8)
for id_m, color in enumerate(colores_rgb):
    img_rgb[matriz_completa == id_m] = color

pil_img = Image.fromarray(img_rgb)
buffer = io.BytesIO()
pil_img.save(buffer, format="PNG")
img_b64 = base64.b64encode(buffer.getvalue()).decode()

# --- VISOR HTML5 TÁCTIL (PLATINA MÓVIL) ---
col_visor, col_info = st.columns([1.3, 1])

with col_visor:
    html_code = f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: sans-serif;">
        <p style="margin: 0 0 8px 0; font-size: 14px; color: #555; text-align: center;">
            👉 <b>Arrastrá sobre el ocular</b> para mover la platina en 2D.
        </p>
        
        <canvas id="stageCanvas" width="420" height="420" style="border-radius: 50%; border: 6px solid #222; box-shadow: 0 8px 20px rgba(0,0,0,0.3); cursor: grab; touch-action: none; background: #000;"></canvas>
        
        <div style="margin-top: 12px; display: flex; gap: 10px;">
            <button onclick="resetPos()" style="padding: 6px 14px; background: #333; color: white; border: none; border-radius: 6px; cursor: pointer;">Centrar Platina</button>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('stageCanvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        img.src = 'data:image/png;base64,{img_b64}';

        let isDragging = false;
        let startX, startY;
        let imgX = -190; // Posición inicial centrada
        let imgY = -190;
        let scale = 1.0;

        img.onload = () => {{ draw(); }};

        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Máscara Circular del Ocular
            ctx.save();
            ctx.beginPath();
            ctx.arc(canvas.width / 2, canvas.height / 2, canvas.width / 2, 0, Math.PI * 2);
            ctx.clip();

            // Fondo del campo
            ctx.fillStyle = "#f2f2f2";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Dibujar imagen de la roca desplazada
            ctx.drawImage(img, imgX, imgY, img.width * scale, img.height * scale);

            // Retículo / Cruz filar del ocular
            ctx.strokeStyle = "rgba(0, 0, 0, 0.25)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(canvas.width / 2, 0); ctx.lineTo(canvas.width / 2, canvas.height);
            ctx.moveTo(0, canvas.height / 2); ctx.lineTo(canvas.width, canvas.height / 2);
            ctx.stroke();

            ctx.restore();
        }}

        // EVENTOS TÁCTILES Y MOUSE (POINTER EVENTS NATIVOS)
        canvas.addEventListener('pointerdown', (e) => {{
            isDragging = true;
            startX = e.clientX - imgX;
            startY = e.clientY - imgY;
            canvas.style.cursor = 'grabbing';
            canvas.setPointerCapture(e.pointerId);
        }});

        canvas.addEventListener('pointermove', (e) => {{
            if (!isDragging) return;
            imgX = e.clientX - startX;
            imgY = e.clientY - startY;

            // Límites de la platina para no salirte de la preparación
            const maxOffset = 50;
            const minOffset = - (img.width * scale - canvas.width + 50);
            
            imgX = Math.min(maxOffset, Math.max(minOffset, imgX));
            imgY = Math.min(maxOffset, Math.max(minOffset, imgY));

            draw();
        }});

        canvas.addEventListener('pointerup', (e) => {{
            isDragging = false;
            canvas.style.cursor = 'grab';
            canvas.releasePointerCapture(e.pointerId);
        }});

        function resetPos() {{
            imgX = - (img.width * scale - canvas.width) / 2;
            imgY = - (img.height * scale - canvas.height) / 2;
            draw();
        }}
    </script>
    """
    components.html(html_code, height=490)

with col_info:
    st.subheader("📊 Composición Modal Real")
    st.caption("Recorré la muestra táctilmente y evaluá los porcentajes reales.")
    
    modo_ciego = st.checkbox("Ocultar leyenda (Modo Entrenamiento / Desafío)")
    
    if not modo_ciego:
        total_area = tam_muestra * tam_muestra
        if len(st.session_state.minerales) > 0:
            for idx, min_item in enumerate(st.session_state.minerales, start=1):
                px_m = np.sum(matriz_completa == idx)
                pct_m = (px_m / total_area) * 100
                st.write(f"**{min_item['nombre']}**: `{pct_m:.1f}%`")
                
            px_pasta = np.sum(matriz_completa == 0)
            st.write(f"**Matriz / Pasta de Roca**: `{(px_pasta/total_area)*100:.1f}%`")
