import streamlit as st
import random
from ortools.sat.python import cp_model

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Torneo | Generador", layout="wide")

ESTILOS_NORMALES = {
    "Gris":     ["#9E9E9E", "black"], "Morado":   ["#7E57C2", "white"],
    "Rosa":     ["#F06292", "black"], "Rojo":     ["#E53935", "white"],
    "Negro":    ["#303030", "white"], "Verde":    ["#66BB6A", "black"],
    "Amarillo": ["#FFEE58", "black"], "Naranja":  ["#FFA726", "black"],
    "Granate":  ["#900C3F", "white"], "Blanco":   ["#FFFFFF", "black"],
    "Marrón":   ["#8D6E63", "white"], "Azul":     ["#4BA3E3", "black"]
}

def generar_multitorneo_equilibrado(equipos, lista_rivalidades, semilla=None):
    if semilla is None: semilla = random.randint(1, 100000)
    num_equipos, num_rondas, num_juegos = 12, 5, 5
    equipo_a_id = {t: i for i, t in enumerate(equipos)}
    id_a_equipo = {i: t for i, t in enumerate(equipos)}
    
    historial_global = {} 
    resultados = []

    for idx, rivalidad in enumerate(lista_rivalidades):
        A_nombre, B_nombre = rivalidad
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
            resultados.append((rivalidad, cuadrante))
        else:
            resultados.append((rivalidad, None))
            
    return resultados

def generar_html_exacto(cuadrante, rivalidad_fija, titulo_torneo):
    A_nombre, B_nombre = rivalidad_fija
    
    html = f'''
    <div style="font-family: 'Aptos', 'Calibri', 'Arial', sans-serif; margin-bottom: 30px;">
        <h2 style="color: #333; margin: 0; padding-left: 10px;">{titulo_torneo}</h2>
        <h4 style="color: #666; margin: 5px 0 15px 10px; font-weight: normal;">Rivalidad: <b>{A_nombre} vs {B_nombre}</b></h4>
        <div style="background-color: #A6A6A6; padding: 10px; display: inline-block; font-size: 14px; border-radius: 8px;">
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
                    rivalry_match, other_match = m1, m2
                else:
                    rivalry_match, other_match = m2, m1
                if rivalry_match[0] != A_nombre:
                    rivalry_match = (A_nombre, B_nombre)

                bg_o0, txt_o0 = ESTILOS_NORMALES.get(other_match[0], ["#FFFFFF", "black"])
                bg_o1, txt_o1 = ESTILOS_NORMALES.get(other_match[1], ["#FFFFFF", "black"])
                bg_r0, txt_r0 = ESTILOS_NORMALES.get(rivalry_match[0], ["#FFFFFF", "black"])
                bg_r1, txt_r1 = ESTILOS_NORMALES.get(rivalry_match[1], ["#FFFFFF", "black"])

                html += f'''
                <div style="display: flex; flex-direction: column; height: 100%;">
                    <div style="flex: 1; display: flex; border-bottom: 1px solid black;">
                        <div style="flex: 1; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; background-color: {bg_o0}; color: {txt_o0};">{other_match[0]}</div>
                        <div style="flex: 1; display: flex; align-items: center; justify-content: center; background-color: {bg_o1}; color: {txt_o1};">{other_match[1]}</div>
                    </div>
                    <div style="flex: 1; display: flex;">
                        <div style="flex: 1; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; background-color: {bg_r0}; color: {txt_r0};">{rivalry_match[0]}</div>
                        <div style="flex: 1; display: flex; align-items: center; justify-content: center; background-color: {bg_r1}; color: {txt_r1};">{rivalry_match[1]}</div>
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

# --- INTERFAZ DE USUARIO (WEB) ---
st.title("🏆 Generador de Cuadrantes")
st.write("Haz clic en el botón para calcular y generar los 6 torneos con cruces equilibrados.")

lista_equipos = ["Gris", "Morado", "Rosa", "Rojo", "Negro", "Verde", "Amarillo", "Naranja", "Granate", "Blanco", "Marrón", "Azul"]
lista_rivalidades = [
    ("Rosa", "Rojo"), ("Granate", "Marrón"), ("Azul", "Morado"), 
    ("Blanco", "Negro"), ("Verde", "Gris"), ("Amarillo", "Naranja")
]

# El botón mágico
if st.button("🔄 Generar Cuadrantes", type="primary"):
    
    # Muestra un mensaje de carga mientras piensa
    with st.spinner('Calculando emparejamientos mediante Inteligencia Artificial... (puede tardar unos 15-20 segundos)'):
        resultados = generar_multitorneo_equilibrado(lista_equipos, lista_rivalidades)
        
        # Muestra los resultados en la web
        for i, (rivalidad, cuadrante) in enumerate(resultados):
            if cuadrante is not None:
                titulo = f"TORNEO {i+1}"
                html_final = generar_html_exacto(cuadrante, rivalidad, titulo)
                st.markdown(html_final, unsafe_allow_html=True)
            else:
                st.error(f"❌ No se pudo resolver el Torneo {i+1}")