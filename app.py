import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# Importaciones para la generación del PDF con ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Configuración inicial de la página
st.set_page_config(page_title="Dashboard VIP", layout="wide")

st.title("Dashboard de Obsequios VIP")
st.markdown("Sube tu archivo de datos para procesar, visualizar el reporte y descargar el informe en PDF.")

# 2. Carga dinámica de archivos
archivo = st.file_uploader("Cargar archivo CSV", type=["csv"])

if archivo is not None:
    # --- PROCESAMIENTO DE DATOS ---
    df = pd.read_csv(archivo)

    # Identificación y limpieza de duplicados
    duplicados = df['Usuario'].duplicated()
    cantidad_usuarios_duplicados = df['Usuario'].duplicated().sum()
    nombres_usuarios_duplicados = df[duplicados]['Usuario']

    if cantidad_usuarios_duplicados > 0:
        st.warning(f"Se encontraron y omitieron {cantidad_usuarios_duplicados} usuarios duplicados.")
        with st.expander("Ver usuarios duplicados omitidos"):
            for u in nombres_usuarios_duplicados.tolist():
                st.write(f"- usuario: {u}")
    df = df.drop_duplicates(subset='Usuario')

    # Total Obsequios Acreditados
    total_acreditaciones = df['Usuario'].count()

    # Tratamiento de fechas y asignación de turnos
    df['Create_Time'] = pd.to_datetime(df['Create_Time'], format="%d/%m/%Y %H:%M:%S")
    df['Hora_Entera'] = df['Create_Time'].dt.hour

    limites = [0, 8, 14, 20, 24]
    etiquetas = ['Nocturno', 'AM', 'PM', 'Nocturno']
    df['Turno'] = pd.cut(df['Hora_Entera'], bins=limites, labels=etiquetas, right=False, ordered=False)
    
    # Agrupación por turno garantizando la presencia de las etiquetas principales
    turnos = df.groupby(by='Turno')["Usuario"].count()
    acred_am = turnos.get('AM', 0)
    acred_pm = turnos.get('PM', 0)
    acred_nocturno = turnos.get('Nocturno', 0)

    # Lógica de Monedas
    totales_moneda_serie = df.groupby(by='Moneda')['Usuario'].count().sort_values(ascending=False)
    moneda_mas_acreditada = totales_moneda_serie.iloc[0]
    nombre_moneda_mayor = totales_moneda_serie.index[0]
    porcentaje_moneda = (moneda_mas_acreditada / total_acreditaciones) * 100

    # Lógica de Secciones (Casino vs Deportes)
    cantidad_casino_deporte = df.groupby(by="Observaciones")['Usuario'].count().sort_values(ascending=False)
    etiqueta_mayor = cantidad_casino_deporte.index[0].split(maxsplit=3)[-1]
    cantidad_mayor = cantidad_casino_deporte.iloc[0]
    
    # Búsqueda dinámica de palabras clave para evitar errores por mayúsculas o variaciones
    acred_casino = 0
    acred_deportes = 0
    for obs, count in cantidad_casino_deporte.items():
        obs_lower = str(obs).lower()
        if 'casino' in obs_lower or 'slot' in obs_lower:
            acred_casino += count
        elif 'apuesta' in obs_lower or 'deport' in obs_lower:
            acred_deportes += count


    # --- GENERACIÓN DE GRÁFICOS (GUARDADOS EN MEMORIA PARA EL PDF) ---
    
    # Gráfico 1: Turnos
    fig1, ax1 = plt.subplots(figsize=(5, 3.5))
    turnos_ordenados = turnos.sort_values(ascending=False)
    ax1.bar(turnos_ordenados.index.astype(str), turnos_ordenados.values, color=['#1E3A8A', '#3B82F6', '#93C5FD'])
    ax1.set_title("Acreditaciones por Turno", fontweight='bold')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    for i, valor in enumerate(turnos_ordenados.values):
        ax1.text(i, valor + 0.5, str(valor), ha='center', fontweight='bold')
    plt.tight_layout()
    
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format='png', dpi=150)
    buf1.seek(0)

    # Gráfico 2: Monedas
    fig2, ax2 = plt.subplots(figsize=(5, 3.5))
    ax2.bar(totales_moneda_serie.index, totales_moneda_serie.values, color='#10B981')
    ax2.set_title("Acreditaciones por Moneda", fontweight='bold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    for i, valor in enumerate(totales_moneda_serie.values):
        ax2.text(i, valor + 0.5, str(valor), ha='center', fontweight='bold')
    plt.tight_layout()
    
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png', dpi=150)
    buf2.seek(0)

    # Gráfico 3: Proporción por Sección
    fig3, ax3 = plt.subplots(figsize=(5, 3.5))
    ax3.pie(
        [acred_casino, acred_deportes], 
        labels=['Casino Slot', 'Apuestas Deportivas'], 
        autopct='%1.1f%%', 
        colors=['#F59E0B', '#FCD34D'],
        startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
    )
    ax3.set_title("Distribución por Sección", fontweight='bold')
    plt.tight_layout()
    
    buf3 = io.BytesIO()
    fig3.savefig(buf3, format='png', dpi=150)
    buf3.seek(0)


    # --- CONSTRUCCIÓN DE LA CADENA DE TEXTO DEL REPORTE ---
    texto_monedas = "\n".join([f"{moneda} : {cant}" for moneda, cant in totales_moneda_serie.items()])

    reporte_texto = f"""Total de Obsequios Acreditados: {total_acreditaciones}
Acreditaciones Turno AM: {acred_am}
Acreditaciones Turno PM: {acred_pm}
Acreditaciones Turnos Nocturno: {acred_nocturno}
Moneda con más acreditaciones: {nombre_moneda_mayor} con un total de {moneda_mas_acreditada}, representa un {porcentaje_moneda:.2f}% del total acreditado

Total Acreditaciones por moneda:
{texto_monedas}

Obsequios acreditados en Casino Slot: {acred_casino}
Obsequios acreditados en APUESTAS DEPORTIVAS: {acred_deportes}"""


    # --- FUNCIÓN INTERNA PARA CREAR EL PDF EN MEMORIA ---
    def generar_pdf():
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()

        # Estilos personalizados
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#0F172A"), alignment=1, spaceAfter=15)
        subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor("#334155"), spaceAfter=10)
        texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#1E293B"))

        # Encabezado del documento
        story.append(Paragraph("Reporte Ejecutivo de Acreditaciones VIP", titulo_style))
        story.append(Spacer(1, 10))

        # Sección de texto con la información solicitada
        story.append(Paragraph("<b>Resumen de Métricas Operativas</b>", subtitulo_style))
        
        # Convertimos los saltos de línea a etiquetas <br/> para HTML/ReportLab
        reporte_html = reporte_texto.replace('\n', '<br/>')
        story.append(Paragraph(reporte_html, texto_style))
        story.append(Spacer(1, 15))

        # Sección visual con los gráficos integrados
        story.append(Paragraph("<b>Análisis Gráfico</b>", subtitulo_style))
        
        img1 = Image(buf1, width=240, height=168)
        img2 = Image(buf2, width=240, height=168)
        img3 = Image(buf3, width=240, height=168)

        # Organización de las imágenes en una tabla invisible para cuadrar el layout
        tabla_graficos = Table([
            [img1, img2],
            [img3, ""]
        ])
        tabla_graficos.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(tabla_graficos)

        # Construir el documento
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer


    # --- VISUALIZACIÓN EN LA PÁGINA WEB (STREAMLIT) ---

    # KPIs Principales
    st.subheader("📊 Métricas Generales")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Acreditaciones", total_acreditaciones)
    col2.metric("Moneda Principal", f"{nombre_moneda_mayor}", f"{porcentaje_moneda:.1f}% del total")
    col3.metric(f"Sección Principal", etiqueta_mayor.capitalize(), f"{cantidad_mayor} acreditaciones")
    col4.metric(f"Turno Mayoritario", turnos.index[0], f"{turnos.iloc[0]} acreditaciones")

    st.divider() # Línea divisoria visual

    # Reporte Consolidado
    st.subheader("📋 Reporte Consolidado")
    
    # Imprime en pantalla la salida requerida respetando el formato solicitado
    st.code(reporte_texto, language=None)

    # Botón de descarga del reporte PDF
    pdf_bytes = generar_pdf()
    st.download_button(
        label="📄 Descargar Reporte en PDF",
        data=pdf_bytes,
        file_name="Reporte_Acreditaciones_VIP.pdf",
        mime="application/pdf"
    )

    st.divider()

    st.subheader("📈 Análisis Gráfico")
    col_graf1, col_graf2, col_graf3 = st.columns(3)

    with col_graf1:
        st.pyplot(fig1)

    with col_graf2:
        st.pyplot(fig2)

    with col_graf3:
        st.pyplot(fig3)

else:
    st.info("Por favor, sube un archivo CSV en el menú superior para comenzar el análisis.")