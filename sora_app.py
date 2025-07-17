import streamlit as st
import pandas as pd
import json
from PIL import Image

# --- CONFIGURACIÓN DE LA PÁGINA E INICIALIZACIÓN DE ESTADO ---
st.set_page_config(page_title="SORA App - Lector de Remisiones", layout="wide")

# Inicializamos las variables en el estado de la sesión si no existen
if 'last_product' not in st.session_state:
    st.session_state.last_product = None
if 'last_barcode' not in st.session_state:
    st.session_state.last_barcode = None
# Este contador nos ayudará a generar un script de audio único cada vez
if 'run_id' not in st.session_state:
    st.session_state.run_id = 0


# --- CARGAR LOGO ---
try:
    col_logo1, col_logo2, col_logo3 = st.columns([1,3,1])
    with col_logo2:
        logo = Image.open("logo_transparente.png")
        # CORRECCIÓN 1: Cambiamos 'use_column_width' por 'use_container_width'
        st.image(logo, use_container_width=True)
except FileNotFoundError:
    st.warning("No se encontró el archivo 'logo_transparente.png'. Asegúrate de que esté en la misma carpeta que la app.")


# --- FUNCIONES AUXILIARES ---

def load_excel(file):
    """Carga y valida el archivo Excel."""
    try:
        df = pd.read_excel(file)
        expected_columns = ['tbc', 'codigo de barras', 'descripcion del producto', 'cantidad', 'pvp']
        df.columns = [str(col).lower().strip() for col in df.columns]
        if not all(col in df.columns for col in expected_columns):
            st.error(f"El archivo Excel debe contener las columnas: {', '.join(expected_columns)}")
            st.info(f"Columnas encontradas en tu archivo: {', '.join(df.columns)}")
            return None
        df['codigo de barras'] = df['codigo de barras'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo Excel: {e}")
        return None

def find_product(df, barcode):
    """Busca un producto en el DataFrame por su código de barras."""
    barcode = str(barcode).strip()
    result = df[df['codigo de barras'] == barcode]
    if not result.empty:
        return result.iloc[0]
    return None

def generate_speech_script(description, quantity, pvp, run_id):
    """Genera un script de JavaScript para leer el texto en voz alta en el navegador."""
    text_to_speak = f"Descripción, {description}. Cantidad, {quantity}. Precio, {pvp}."
    safe_text = json.dumps(text_to_speak)
    speech_rate = 0.9
    
    # CORRECCIÓN 2: Añadimos un comentario con el 'run_id' para hacer el script único
    return f"""
        <script>
            // Run ID: {run_id} 
            window.speechSynthesis.cancel();
            var msg = new SpeechSynthesisUtterance();
            msg.text = {safe_text};
            msg.lang = 'es-ES';
            msg.rate = {speech_rate};
            window.speechSynthesis.speak(msg);
        </script>
    """

def process_barcode():
    """
    Se ejecuta al presionar el botón del formulario. Procesa el código de barras.
    """
    barcode = st.session_state.get("barcode_input", "").strip()
    if barcode:
        df = st.session_state.get("dataframe")
        if df is not None:
            product_info = find_product(df, barcode)
            st.session_state.last_product = product_info
            st.session_state.last_barcode = barcode
            # Incrementamos nuestro contador para la siguiente ejecución
            st.session_state.run_id += 1
    
    st.session_state.barcode_input = ""


# --- INTERFAZ PRINCIPAL DE LA APLICACIÓN ---

st.title("✅ SORA App - Procesador de Remisiones")

uploaded_file = st.file_uploader("1. Sube la remisión de tu proveedor (archivo Excel)", type=["xlsx", "xls"])

if uploaded_file:
    if 'dataframe' not in st.session_state or st.session_state.get('uploaded_filename') != uploaded_file.name:
        with st.spinner("Procesando archivo..."):
            st.session_state.dataframe = load_excel(uploaded_file)
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.last_product = None
            st.session_state.last_barcode = None

if 'dataframe' in st.session_state and st.session_state.dataframe is not None:
    st.success(f"Archivo '{st.session_state.uploaded_filename}' cargado. ¡Listo para escanear!")
    
    with st.expander("Ver contenido de la remisión"):
        st.dataframe(st.session_state.dataframe, use_container_width=True)

    st.markdown("---")
    st.header("2. Escanea los productos")

    with st.form(key="scan_form"):
        st.text_input(
            "Escanea el código de barras (el cursor debe estar aquí)",
            placeholder="El lector USB ingresará el código aquí...",
            key="barcode_input"
        )
        st.form_submit_button(
            "🔍 Buscar Producto", 
            on_click=process_barcode
        )

    if st.session_state.last_product is not None:
        product = st.session_state.last_product
        barcode = st.session_state.last_barcode
        
        st.markdown(f"## <p style='color:green;'>Código encontrado: {barcode}</p>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Descripción", str(product['descripcion del producto']))
        col2.metric("🔢 Cantidad", str(product['cantidad']))
        col3.metric("💲 PVP", f"${product['pvp']:,.2f}")

        speech_script = generate_speech_script(
            product['descripcion del producto'],
            product['cantidad'],
            product['pvp'],
            run_id=st.session_state.run_id # Pasamos el ID único
        )
        # CORRECCIÓN 2: Quitamos el argumento 'key' que no es válido
        st.components.v1.html(speech_script, height=0)

    elif st.session_state.last_barcode is not None:
        st.error(f"**Código no encontrado:** `{st.session_state.last_barcode}` no está en la remisión.")