import streamlit as st
import random
from ortools.sat.python import cp_model

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Generador de Días | Torneo", layout="wide")

# --- INYECCIÓN DE FUENTE PERSONALIZADA (Opcional, usando Montserrat como ejemplo) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');
        html, body, [class*="css"], [class*="st-"] {
            font-family: 'Montserrat', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

ESTILOS_NORMALES = {
    "Gris":     ["#9E9E9E", "black"], "Morado":   ["#7E57C2", "white"],
    "Rosa":     ["#F06292", "black"], "Rojo":     ["#E53935", "white"],
    "Negro":    ["#303030", "white"], "Verde":    ["#66BB6A", "black"],
    "Amarillo": ["#FFEE58", "black"], "Naranja":  ["#FFA726", "black"],
    "Granate":  ["#900C3F", "white"], "Blanco":   ["#FFFFFF", "black"],
    "Marrón":   ["#8D6E63", "white"], "Azul":     ["#4BA3E3", "black"]
}

MAPA_OPCIONES = {
    "Derbi: Rosa vs Rojo": ("Rosa", "Rojo"),
    "Derbi: Granate vs Marrón": ("Granate", "Marrón"),
    "Derbi: Azul vs Morado": ("Azul", "Morado"),
    "Derbi: Blanco vs Negro": ("Blanco", "Negro"),
    "Derbi: Verde vs Gris": ("Verde", "Gris"),
    "Derbi: Amarillo vs Naranja": ("Amarillo", "Naranja"),
    "Cooperativas (Equipos Amigos)": "COOPERATIVAS"
}

def generar_dias_equilibrados(equipos, lista_derbis_ordenada, semilla=None):
    if semilla is None: semilla = random.randint(1, 100000)
    num_equipos, num_rondas, num_juegos = 12, 5, 5
    equipo_a_id = {t: i for i, t in enumerate(equipos)}
    id_a_equipo = {i: t for i, t in enumerate(equipos)}
    
    historial_global = {} 
    resultados = []

    for idx, derbi in enumerate(lista_derbis_ordenada):
        A_nombre, B_nombre = derbi
        A, B = equipo_a_id[A_nombre], equipo_a_id[B_nombre]
        A, B = min(A, B), max(A, B)

        model = cp_model.CpModel()
        juega = {}
        partido = {}
        
        for r in range(num_rondas):
            for g in range(num_juegos):
                for t in range(num_equipos):
                    juega[(r, g, t)] = model.NewBoolVar(f'j_{r}_{g}_{t}')
                for t1 in range(num_equipos):
                    for t2 in range(t1 + 1, num_equipos):
                        partido[(r, g, t1, t2)] = model.NewBoolVar(f'p_{r}_{g}_{t1}_{t2}')

        for r in range(num_rondas): 
            for t in range(num_equipos):
                model.AddExactlyOne(juega[(r, g, t)] for g in range(num_juegos))

        for r in range(num_rondas): 
            for g in range(num_juegos):
                if r == g: 
                    model.Add(sum(juega[(r, g, t)] for t in range(num_equipos)) == 4)
                    model.Add(sum(partido[(r, g, t1, t2)] for t1 in range(num_equipos) for t2 in range(t1+1, num_equipos)) == 2)
                else:
                    model.Add(sum(juega[(r, g, t)] for t in range(num_equipos)) == 2)
                    model.Add(sum(partido[(r, g, t1, t2)] for t1 in range(num_equipos) for t2 in range(t1+1, num_equipos)) == 1)

        for g in range(num_juegos):
            for t in range(num_equipos):
                model.AddExactlyOne(juega[(r, g, t)] for r in range(num_rondas))

        for r in range(num_rondas):
            for g in range(num_juegos):
                for t in range(num_equipos):
                    model.Add(juega[(r, g, t)] == sum(partido[(r, g, t, t2)] for t2 in range(t + 1, num_equipos)) + sum(partido[(r, g, t1, t)] for t1 in range(t)))

        for r in range(num_rondas):
            model.Add(partido[(r, r, A, B)] == 1)
        
        for t in range(num_equipos):
            if t not in [A, B]:
                model.Add(sum(juega[(r, r, t)] for r in range(num_rondas)) == 1)

        for t1 in range(num_equipos):
            for t2 in range(t1 + 1, num_equipos):
                if (t1, t2) != (A, B):
                    model.Add(sum(partido[(r, g, t1, t2)] for r in range(num_rondas) for g in range(num_juegos)) <= 1)

        penalizaciones = []
        for t1 in range(num_equipos):
            for t2 in range(t1 + 1, num_equipos):
                if (t1, t2) != (A, B):
                    veces_previas = historial_global.get((t1, t2), 0)
                    if veces_previas > 0:
                        peso = veces_previas * 10
                        for r in range(num_rondas):
                            for g in range(num_juegos):
                                penalizaciones.append(partido[(r, g, t1, t2)] * peso)
        
        if penalizaciones:
            model.Minimize(sum(penalizaciones))

        solver = cp_model.CpSolver()
        solver.parameters.random_seed = semilla + idx
        solver.parameters.max_time_in_seconds = 15.0 
        status = solver.Solve(model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            cuadrante = []
            for r in range(num_rondas):
                fila = []
                for g in range(num_juegos):
                    juegos_en_celda = []
                    for t1 in range(num_equipos):
                        for t2 in range(t1 + 1, num_equipos):
                            if solver.Value(partido[(r, g, t1, t2)]) == 1:
                                juegos_en_celda.append((id_a_equipo[t1], id_a_equipo[t2]))
                                if (t1, t2) != (A, B):
                                    historial_global[(t1, t2)] = historial_global.get((t1, t2), 0) + 1
                    fila.append(juegos_en_celda)
                cuadrante.append(fila)
            resultados.append((derbi, cuadrante))
        else:
            resultados.append((derbi, None))
            
    return resultados

def generar_dia_especial_amigos():
    pares_amigos = [
        ("Gris", "Negro"), ("Blanco", "Rosa"), ("Granate", "Azul"),
        ("Amarillo", "Verde"), ("Naranja", "Marrón"), ("Morado", "Rojo")
    ]
    cuadrante_especial = []
    for r in range(6): 
        fila = []
        for g in range(6): 
            par = pares_amigos[(g - r) % 6]
            fila.append([par]) 
        cuadrante_especial.append(fila)
    return cuadrante_especial

def generar_html_exacto(cuadrante, derbi_fijo, titulo_dia, texto_olimpiadas):
    A_nombre, B_nombre = derbi_fijo
    titulo_olim = f"OLIMPIADAS {texto_olimpiadas}" if texto_olimpiadas else "OLIMPIADAS"

    html = f'''
    <div style="font-family: 'Montserrat', 'Aptos', 'Calibri', 'Arial', sans-serif; margin-bottom: 20px;">
        <h2 style="color: #333; margin: 0; padding-left: 10px;">{titulo_dia}</h2>
        <h4 style="color: #666; margin: 5px 0 15px 10px; font-weight: normal;">Derbi: <b>{A_nombre} vs {B_nombre}</b></h4>
        <div style="background-color: #A6A6A6; padding: 10px; display: inline-block; font-size: 14px; border-radius: 8px;">
            <div style="text-align: center; font-size: 18px; font-weight: bold; color: black; margin-bottom: 10px; text-transform: uppercase;">
                {titulo_olim}
            </div>
            <table style="border-collapse: separate; border-spacing: 8px; text-align: center; border: none; margin: 0;">
                <tr>
                    <td style="background-color: transparent; border: none;"></td>
    '''
    for g in range(5):
        html += f'<td style="background-color: white; color: black; border: 1px solid black; padding: 6px 0; width: 140px; font-weight: normal;">JUEGO {g+1}</td>'
    html += '</tr>'
    for r, fila in enumerate(cuadrante):
        html += '<tr>'
        html += f'<td style="background-color: white; color: black; border: 1px solid black; padding: 0 15px; font-weight: normal; vertical-align: middle;">RONDA {r+1}</td>'
        for juegos in fila:
            html += '<td style="background-color: white; border: 1px solid black; padding: 0; height: 50px;">'
            if len(juegos) == 1:
                p = juegos[0]
                bg0, txt0 = ESTILOS_NORMALES.get(p[0], ["#FFFFFF", "black"])
                bg1, txt1 = ESTILOS_NORMALES.get(p[1], ["#FFFFFF", "black"])
                html += f'''
                <div style="display: flex; height: 100%;">
                    <div style="flex: 1; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; background-color: {bg0}; color: {txt0};">{p[0]}</div>
                    <div style="flex: 1; display: flex; align-items: center; justify-content: center; background-color: {bg1}; color: {txt1};">{p[1]}</div>
                </div>
                '''
            else:
                m1, m2 = juegos[0], juegos[1]
                if set(m1) == {A_nombre, B_nombre}:
                    derbi_match, other_match = m1, m2
                else:
                    derbi_match, other_match = m2, m1
                if derbi_match[0] != A_nombre:
                    derbi_match = (A_nombre, B_nombre)

                bg_o0, txt_o0 = ESTILOS_NORMALES.get(other_match[0], ["#FFFFFF", "black"])
                bg_o1, txt_o1 = ESTILOS_NORMALES.get(other_match[1], ["#FFFFFF", "black"])
                bg_r0, txt_r0 = ESTILOS_NORMALES.get(derbi_match[0], ["#FFFFFF", "black"])
                bg_r1, txt_r1 = ESTILOS_NORMALES.get(derbi_match[1], ["#FFFFFF", "black"])

                html += f'''
                <div style="display: flex; flex-direction: column; height: 100%;">
                    <div style="flex: 1; display: flex; border-bottom: 1px solid black;">
                        <div style="flex: 1; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; background-color: {bg_o0}; color: {txt_o0};">{other_match[0]}</div>
                        <div style="flex: 1; display: flex; align-items: center; justify-content: center; background-color: {bg_o1}; color: {txt_o1};">{other_match[1]}</div>
                    </div>
                    <div style="flex: 1; display: flex;">
                        <div style="flex: 1; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; background-color: {bg_r0}; color: {txt_r0};">{derbi_match[0]}</div>
                        <div style="flex: 1; display: flex; align-items: center; justify-content: center; background-color: {bg_r1}; color: {txt_r1};">{derbi_match[1]}</div>
                    </div>
                </div>
                '''
            html += '</td>'
        html += '</tr>'
    html += '''
            </table>
        </div>
    </div>
    '''
    return html

def generar_html_amigos(cuadrante, titulo_dia, texto_olimpiadas):
    titulo_olim = f"OLIMPIADAS {texto_olimpiadas}" if texto_olimpiadas else "OLIMPIADAS"

    html = f'''
    <div style="font-family: 'Montserrat', 'Aptos', 'Calibri', 'Arial', sans-serif; margin-bottom: 20px;">
        <h2 style="color: #333; margin: 0; padding-left: 10px;">{titulo_dia}</h2>
        <h4 style="color: #666; margin: 5px 0 15px 10px; font-weight: normal;">Día Especial: <b>Cooperativas (Equipos Amigos)</b></h4>
        <div style="background-color: #A6A6A6; padding: 10px; display: inline-block; font-size: 14px; border-radius: 8px;">
            <div style="text-align: center; font-size: 18px; font-weight: bold; color: black; margin-bottom: 10px; text-transform: uppercase;">
                {titulo_olim}
            </div>
            <table style="border-collapse: separate; border-spacing: 8px; text-align: center; border: none; margin: 0;">
                <tr>
                    <td style="background-color: transparent; border: none;"></td>
    '''
    for g in range(6):
        html += f'<td style="background-color: white; color: black; border: 1px solid black; padding: 6px 0; width: 140px; font-weight: normal;">JUEGO {g+1}</td>'
    html += '</tr>'
    
    for r, fila in enumerate(cuadrante):
        html += '<tr>'
        html += f'<td style="background-color: white; color: black; border: 1px solid black; padding: 0 15px; font-weight: normal; vertical-align: middle;">RONDA {r+1}</td>'
        for juegos in fila:
            html += '<td style="background-color: white; border: 1px solid black; padding: 0; height: 50px;">'
            p = juegos[0]
            bg0, txt0 = ESTILOS_NORMALES.get(p[0], ["#FFFFFF", "black"])
            bg1, txt1 = ESTILOS_NORMALES.get(p[1], ["#FFFFFF", "black"])
            html += f'''
            <div style="display: flex; height: 100%;">
                <div style="flex: 1; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; background-color: {bg0}; color: {txt0};">{p[0]}</div>
                <div style="flex: 1; display: flex; align-items: center; justify-content: center; background-color: {bg1}; color: {txt1};">{p[1]}</div>
            </div>
            '''
            html += '</td>'
        html += '</tr>'
    html += '''
            </table>
        </div>
    </div>
    '''
    return html

# ==========================================
# INTERFAZ DE USUARIO (MENÚ PRINCIPAL)
# ==========================================
st.title("🏆 Generador de Días")
st.write("Configura el orden de los eventos y personaliza el título de las Olimpiadas para cada día.")

opciones_lista = list(MAPA_OPCIONES.keys())
lista_equipos = ["Gris", "Morado", "Rosa", "Rojo", "Negro", "Verde", "Amarillo", "Naranja", "Granate", "Blanco", "Marrón", "Azul"]

st.markdown("### 📅 Configuración del Menú")
configuracion_dias = []

for i in range(1, 8):
    col1, col2 = st.columns([1, 1])
    with col1:
        opcion = st.selectbox(f"DÍA {i}:", opciones_lista, index=(i-1), key=f"sel_{i}")
    with col2:
        texto = st.text_input(f"Olimpiadas (Día {i}):", key=f"txt_{i}", placeholder="Ej: Nocturnas")
    configuracion_dias.append((opcion, texto))

eventos_seleccionados = [c[0] for c in configuracion_dias]
hay_repetidos = len(set(eventos_seleccionados)) != 7

st.markdown("---")

if hay_repetidos:
    st.error("⚠️ ¡Atención! Tienes eventos repetidos. Asegúrate de asignar una opción distinta a cada día para poder generar el calendario.")
else:
    if st.button("🔄 Generar Calendario Completo", type="primary"):
        
        derbis_ordenados = []
        for config in configuracion_dias:
            tipo_evento = MAPA_OPCIONES[config[0]]
            if tipo_evento != "COOPERATIVAS":
                derbis_ordenados.append(tipo_evento)
        
        with st.spinner('Calculando emparejamientos mixtos mediante IA... (puede tardar unos 15 segundos)'):
            resultados_derbis = generar_dias_equilibrados(lista_equipos, derbis_ordenados)
        
        st.success("✅ ¡Calendario generado con éxito!")
        iterador_derbis = iter(resultados_derbis)
        
        for i, config in enumerate(configuracion_dias):
            dia_num = i + 1
            tipo_evento = MAPA_OPCIONES[config[0]]
            texto_olimpiadas = config[1]
            titulo_dia = f"DÍA {dia_num}"
            
            if tipo_evento == "COOPERATIVAS":
                cuadrante = generar_dia_especial_amigos()
                html_final = generar_html_amigos(cuadrante, titulo_dia, texto_olimpiadas)
                st.markdown(html_final, unsafe_allow_html=True)
                
                # Botón de Descarga
                html_descarga = f"<html><head><meta charset='utf-8'></head><body style='padding: 20px;'>{html_final}</body></html>"
                st.download_button(
                    label=f"💾 Descargar {titulo_dia} (HTML)",
                    data=html_descarga,
                    file_name=f"Cuadrante_Dia_{dia_num}_Cooperativas.html",
                    mime="text/html",
                    key=f"dl_amigos_{dia_num}"
                )
                st.markdown("---")
                
            else:
                derbi, cuadrante = next(iterador_derbis)
                if cuadrante is not None:
                    html_final = generar_html_exacto(cuadrante, derbi, titulo_dia, texto_olimpiadas)
                    st.markdown(html_final, unsafe_allow_html=True)
                    
                    # Botón de Descarga
                    html_descarga = f"<html><head><meta charset='utf-8'></head><body style='padding: 20px;'>{html_final}</body></html>"
                    st.download_button(
                        label=f"💾 Descargar {titulo_dia} (HTML)",
                        data=html_descarga,
                        file_name=f"Cuadrante_Dia_{dia_num}_{derbi[0]}_vs_{derbi[1]}.html",
                        mime="text/html",
                        key=f"dl_derbi_{dia_num}"
                    )
                    st.markdown("---")
                else:
                    st.error(f"❌ No se pudo resolver el {config[0]}")