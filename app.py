import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from datetime import datetime


st.set_page_config(layout='wide')


# Título de la aplicación
st.title("Bot de Consultas Ranking de Atletismo Galego 🏃‍♂️")

# --- Configuración de la API de Gemini ---
API_KEY = st.secrets["API_KEY"] # Reemplaza con tu clave
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')



sinonimos_pruebas = {
    '200': '200 M.L. MASCULINO',
    '200m': '200 M.L. MASCULINO',
    '200 metros': '200 M.L. MASCULINO',
    '200 metros lisos': '200 M.L. MASCULINO',
    '400': '400 M.L. MASCULINO',
    '400m': '400 M.L. MASCULINO',
    '400 metros': '400 M.L. MASCULINO',
    '400 metros lisos': '400 M.L. MASCULINO',
    '100': '100 M.L. MASCULINO',
    '100m': '100 M.L. MASCULINO',
    '100 metros': '100 M.L. MASCULINO',
    '100 metros lisos': '100 M.L. MASCULINO',
    '800': '800 M.L. MASCULINO',
    '800m':'800 M.L. MASCULINO',
    '800 metros': '800 M.L. MASCULINO',
    '1500 metros lisos': '800 M.L. MASCULINO',
    '1500': '1500 M.L. MASCULINO',
    '1500m':'1500 M.L. MASCULINO',
    '1500 metros': '1500 M.L. MASCULINO',
    '1500 metros lisos': '1500 M.L. MASCULINO'
}


# --- Función para eliminar tildes y mantener la ñ ---
def eliminar_tildes(texto):
    """
    Elimina las tildes de una cadena de texto, pero conserva la letra 'ñ'.
    """
    if not isinstance(texto, str):
        return texto
    
    replacements = (
        ('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'),
        ('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'),
    )
    
    for a, b in replacements:
        texto = texto.replace(a, b)
    
    return texto.lower()


def marca_a_segundos(marca):
    """
    Convierte la marca de tiempo (ej. '10.50' o '00:10.50') a segundos.
    """
    if not isinstance(marca, str):
        return None
    
    try:
        # Intenta convertir directamente a flotante si no contiene ':'
        if ':' not in marca:
            return float(marca)
        else:
            # Si contiene ':', asume que es formato MM:SS.ms y lo convierte
            minutos, segundos_str = marca.split(':')
            segundos = float(minutos) * 60 + float(segundos_str)
            return segundos
    except ValueError:
        return None

# --- Cargar los datos ---
@st.cache_data
def cargar_datos(ruta_archivo):
    try:
        df = pd.read_csv(ruta_archivo, sep=';', encoding='utf-8')
        df = df.dropna(how='all')
        
        # Normalizar las columnas del DataFrame de una vez
        df['Atleta_normalizado'] = df['Atleta'].apply(eliminar_tildes)
        df['Equipo_normalizado'] = df['Equipo'].apply(eliminar_tildes)
        df['prueba_normalizada'] = df['Prueba'].apply(eliminar_tildes)
        df['Marca_segundos'] = df['Marca'].apply(marca_a_segundos) 

        
        # Convertir la columna 'Data' a formato de fecha
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y')


        return df
    except FileNotFoundError:
        st.error(f"Error: El archivo '{ruta_archivo}' no se encontró. Asegúrate de que está en la misma carpeta.")
        return None

df = cargar_datos('ranking_consolidado.csv')

# --- Lógica de la conversación con el bot ---
if df is not None:
    st.write("¡Haz una pregunta sobre atletas, equipos o marcas y te daré la respuesta!")
    
    pregunta_usuario = st.text_input("Ingresa tu pregunta:", "Muéstrame los resultados de Jose Perez en el 100 metros lisos de los últimos 5 años ordenados por fecha")

    if pregunta_usuario:
        with st.spinner('Procesando...'):
            try:
                # Normalizar la pregunta del usuario para la IA
                pregunta_normalizada = eliminar_tildes(pregunta_usuario)

                # 1. Instrucción para el LLM: Extraer la intención y los parámetros
                prompt = f"""
                Eres un asistente experto en atletismo. Tu tarea es extraer la intención del usuario y los parámetros relevantes de su consulta.
                Solo responde con un objeto JSON.

                Parámetros a extraer (si se encuentran):
                - "atleta": Nombre del atleta.
                - "prueba": Nombre de la prueba.
                - "viento": Viento de la prueba.
                - "puesto_competicion": Puesto del atleta en la competicion.
                - "ano": Año específico.
                - "rango_anos": Un número que representa los últimos X años.
                - "equipo": Nombre del equipo.
                - "ordenar_por": El campo por el cual ordenar ("fecha", "marca", etc.).
                - "marca_limite": Una marca de tiempo en segundos para hacer comparaciones.
                - "accion": La acción que el usuario quiere realizar. (ej. "buscar", "comparar", "mejor_marca", "contar_atletas_por_prueba_y_ano", "contar_atletas_por_marca")
                
                Ejemplo de salida para "cuantos atletas han corrido el 100m en 2024?":
                {{"prueba": "100m", "ano": 2024, "accion": "contar_atletas_por_prueba_y_ano"}}

                Ejemplo de salida para "cuantos atletas han corrido por debajo de 11.50 segundos en 100 metros lisos en 2024?":
                {{"prueba": "100 metros lisos", "marca_limite": 11.50, "ano": 2024 , "accion": "contar_atletas_por_marca"}}

                Ejemplo de salida para "dime la mejor marca de Kevin Viñuela en los 200 metros lisos":
                {{"atleta": "Kevin Viñuela", "prueba": "200 M.L. MASCULINO", "accion": "mejor_marca"}}
                
                Ejemplo de salida para "resultados de Jose Perez en el 100 metros de los ultimos 5 años ordenados por fecha":
                {{"atleta": "Jose Perez", "prueba": "100 metros lisos", "rango_anos": 5, "ordenar_por": "fecha"}}

                Consulta del usuario: "{pregunta_normalizada}"
                """
                
                response = model.generate_content(prompt)
                
                parametros = json.loads(response.text.strip().replace("`", "").replace("json", ""))

                # 2. Usa los parámetros para filtrar el DataFrame
                accion = parametros.get('accion', 'buscar')
                df_filtrado = df.copy()
                final_response_content = None

                # --- Lógica para contar atletas por prueba y año ---
                if accion == 'contar_atletas_por_prueba_y_ano':
                    prueba = parametros.get('prueba')
                    ano = parametros.get('ano')
                    if prueba and ano:
                        prueba_normalizada = eliminar_tildes(prueba)
                        prueba_estandarizada = sinonimos_pruebas.get(prueba_normalizada).replace('.', '').lower()
                        if prueba_estandarizada:
                            df_filtrado = df_filtrado[(df_filtrado['prueba_normalizada'] == prueba_estandarizada) & (df_filtrado['Ano'] == ano)]
                            # Contar atletas únicos
                            conteo = df_filtrado['Atleta'].nunique()

                            resultados_str = df_filtrado.to_string()
                            conteo_str = conteo

                            prompt_respuesta = f"""
                            Basado en los siguientes datos de un ranking de atletismo, genera una respuesta amigable en lenguaje natural para el usuario.

                            Datos:
                            {resultados_str, conteo}

                            Pregunta original del usuario: "{pregunta_usuario}"
                            """

                            respuesta_final = model.generate_content(prompt_respuesta)
                            st.write("---")
                            st.write(respuesta_final.text)
                        else:
                            st.info(f"Lo siento, no pude encontrar resultados para esa consulta. Por favor, reformula tu pregunta.")
                    else:
                        st.info(f"Lo siento, no pude encontrar resultados para esa consulta. Por favor, reformula tu pregunta.")

                # --- Lógica para contar atletas por marca ---
                elif accion == 'contar_atletas_por_marca':
                    prueba = parametros.get('prueba')
                    marca_limite = parametros.get('marca_limite')
                    if prueba and marca_limite:
                        prueba_normalizada = eliminar_tildes(prueba)
                        prueba_estandarizada = sinonimos_pruebas.get(prueba_normalizada).replace('.', '').lower()
                        if prueba_estandarizada:
                            df_filtrado = df_filtrado[(df_filtrado['prueba_normalizada'] == prueba_estandarizada) & (df_filtrado['Marca_segundos'] <= marca_limite)]
                            conteo = df_filtrado['Atleta'].nunique()

                            resultados_str = df_filtrado.to_string()
                            conteo_str = conteo

                            prompt_respuesta = f"""
                            Basado en los siguientes datos de un ranking de atletismo, genera una respuesta amigable en lenguaje natural para el usuario.

                            Datos:
                            {resultados_str, conteo}

                            Pregunta original del usuario: "{pregunta_usuario}"
                            """

                            respuesta_final = model.generate_content(prompt_respuesta)
                            st.write("---")
                            st.write(respuesta_final.text)

                        else:
                            st.info(f"Lo siento, no pude encontrar resultados para esa consulta. Por favor, reformula tu pregunta.")
                    else:
                        st.info(f"Lo siento, no pude encontrar resultados para esa consulta. Por favor, reformula tu pregunta..")

                # --- Lógica de búsqueda normal ---
                else:
                
                    if 'atleta' in parametros:
                        nombres_busqueda = eliminar_tildes(parametros['atleta']).split()
                        mask = df_filtrado['Atleta_normalizado'].apply(lambda x: all(nombre in x for nombre in nombres_busqueda))
                        df_filtrado = df_filtrado[mask]


                    if 'prueba' in parametros:
                        test_df = df_filtrado.copy()
                        prueba_normalizada = eliminar_tildes(parametros['prueba'])
                        # Usa el diccionario para obtener el nombre estandarizado
                        prueba_estandarizada = sinonimos_pruebas.get(prueba_normalizada).replace('.', '').lower()

                        if prueba_estandarizada:
                            df_filtrado = df_filtrado[df_filtrado['prueba_normalizada'] == prueba_estandarizada]
                        else:
                            df_filtrado = df_filtrado[df_filtrado['prueba_normalizada'].str.contains(prueba_normalizada, na=False)]


                    if 'ano' in parametros:
                        ano = parametros['ano']
                        if isinstance(ano, int):
                            df_filtrado = df_filtrado[df_filtrado['Ano'] == ano]
                        elif isinstance(ano, str) and ano.isdigit():
                            df_filtrado = df_filtrado[df_filtrado['Ano'] == int(ano)]
                        else:
                            st.warning(f"No se pudo procesar el año: '{ano}'. Se ignorará este filtro.")

                    # --- Lógica para el rango de años ---
                    if 'rango_anos' in parametros:
                        try:
                            rango_anos = int(parametros['rango_anos'])
                            ano_actual = datetime.now().year
                            ano_inicio = ano_actual - rango_anos
                            df_filtrado = df_filtrado[(df_filtrado['Ano'] >= ano_inicio) & (df_filtrado['Ano'] <= ano_actual)]
                        except (ValueError, TypeError):
                            st.warning("No se pudo procesar el rango de años. Se ignorará este filtro.")

                    # 3. Generación de la respuesta final con el LLM
                    if not df_filtrado.empty:
                        # --- Lógica para ordenar los resultados ---
                        if 'ordenar_por' in parametros:
                            if parametros['ordenar_por'].lower() == 'fecha':
                                # Se asume que 'Data' es la columna de fecha
                                df_filtrado = df_filtrado.sort_values(by='Fecha', ascending=False)
                            # Puedes añadir más criterios de ordenamiento aquí (ej. 'marca', 'posicion')

                        resultados_str = df_filtrado.to_string()

                        prompt_respuesta = f"""
                        Basado en los siguientes datos de un ranking de atletismo, genera una respuesta amigable en lenguaje natural para el usuario.

                        Datos:
                        {resultados_str}

                        Pregunta original del usuario: "{pregunta_usuario}"
                        """

                        respuesta_final = model.generate_content(prompt_respuesta)
                        st.write("---")
                        st.write(respuesta_final.text)
                    else:
                        st.info(f"Lo siento, no pude encontrar resultados para esa consulta. Por favor, reformula tu pregunta.")
            
            except Exception as e:
                st.error(f"Ocurrió un error al procesar tu solicitud: {e}. Intenta de nuevo.")
# --- Pie de página con créditos ---
st.markdown("---")
st.markdown("Creado por **Tella** | Feito con ❤️ e fe en dios")
st.markdown("Versión 1.0.0")
# ------------------------------------
