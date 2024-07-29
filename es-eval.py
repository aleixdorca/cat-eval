import os
import json
import regex
import sqlite3

from ollama import Client
from dotenv import load_dotenv

load_dotenv()

ollama_host = os.getenv("LLM_BASE_URL")
db_name = os.getenv("DB_NAME_ES")

# IMPORTANT: Creació de la base de dades i les taules de dades
# > sqlite3 es-eval.db
# > CREATE TABLE content (id INTEGER PRIMARY KEY, model TEXT(1024) NOT NULL, question TEXT(1024) NOT NULL, answer TEXT(4096) NOT NULL, final_grade INTEGER DEFAULT '-1');
# > CREATE TABLE grades (id INTEGER PRIMARY KEY, evaluator TEXT(1024) NOT NULL, content_id INTEGER NOT NULL, grade INTEGER DEFAULT '-1');

models = ['llama3.1:8b-instruct-fp16', 'llama3.1:8b-instruct-q8_0', 'qwen:7b-chat-v1.5-fp16', 'qwen:7b-chat-v1.5-q8_0', 'gemma2:9b-instruct-fp16', 'gemma2:9b-instruct-q8_0', 'mistral-nemo:12b-instruct-2407-fp16', 'mistral-nemo:12b-instruct-2407-q8_0',  'aya:8b-23-f16', 'aya:8b-23-q8_0', 'mixtral:8x7b']

def extract_json(content):
    # From: https://stackoverflow.com/questions/2583472/regex-to-validate-json
    pattern = r'(?(DEFINE)(?<json>(?>\s*(?&object)\s*|\s*(?&array)\s*))(?<object>(?>\{\s*(?>(?&pair)(?>\s*,\s*(?&pair))*)?\s*\}))(?<pair>(?>(?&STRING)\s*:\s*(?&value)))(?<array>(?>\[\s*(?>(?&value)(?>\s*,\s*(?&value))*)?\s*\]))(?<value>(?>true|false|null|(?&STRING)|(?&NUMBER)|(?&object)|(?&array)))(?<STRING>(?>"(?>\\(?>["\\\/bfnrt]|u[a-fA-F0-9]{4})|[^"\\\0-\x1F\x7F]+)*"))(?<NUMBER>(?>-?(?>0|[1-9][0-9]*)(?>\.[0-9]+)?(?>[eE][+-]?[0-9]+)?))) (?&json)'

    content = regex.sub("\n", " ", content)
    content = " " + content
    match = regex.search(pattern, content) 
    try:
        json.loads(match.group(0).strip())
        return match.group(0).strip()
    except:
        return content

def create_connection():
    conn = None;
    try:
        conn = sqlite3.connect(db_name) 
    except sqlite3.Error as e:  
        print(f"Error en connectar a la base de dades: {e}")
    finally:
        return conn

def fetch_rows(conn, query):
    cur = conn.cursor()
    cur.execute(query)
    return cur.fetchall()

def main(write = False, n = 10, eval = False):    
    conn = create_connection()

    client = Client(host=ollama_host)

    questions = ["Escribe un texto en castellano de 150 palabras sobre la importancia de la IA",
                "Escribe un texto en castellano de 150 palabras sobre los beneficios de la lectura habitual",
                "Escribe un texto en castellano de 150 palabras sobre la importancia del deporte en la vida cotidiana",
                "Escribe un texto en castellano de 150 palabras sobre las redes sociales: ventajas e inconvenientes",
                "Escribe un texto en castellano de 150 palabras sobre el problema del cambio climático y sus consecuencias",
                "Escribe un texto en castellano de 150 palabras sobre la educación en valores en las escuelas",
                "Escribe un texto en castellano de 150 palabras sobre la influencia de la publicidad en el consumismo",
                "Escribe un texto en castellano de 150 palabras sobre las nuevas tecnologías: oportunidades y retos",
                "Escribe un texto en castellano de 150 palabras sobre la importancia de la diversidad cultural",
                "Escribe un texto en castellano de 150 palabras sobre el papel de los voluntarios en la sociedad",
                "Escribe un texto en castellano de 150 palabras sobre la necesidad de promover el ecoturismo"]

    if write:
        for model in models:
            for question in questions:
                for i in range(1, n + 1):
                    stream = client.chat(
                        model = model,
                        messages=[{'role': 'user', 'content': question}],
                        options={"temperature":1}
                    )

                    answer = stream['message']['content']
                    new_question = (model, question, answer)

                    sql = ''' INSERT INTO content (model, question, answer) VALUES (?,?,?) '''
                    cur = conn.cursor()
                    cur.execute(sql, new_question)
                    conn.commit()
                    print(f"S'ha afegit una resposta: {model}, {question}, {i}")

    if eval:
        rows = fetch_rows(conn, "SELECT * FROM content")

        grades = {}

        for model in models:
            print("Avaluador:", model)

            for row in rows:
                try:
                    if grades[row[0]]:
                        pass
                except KeyError as e:
                    grades[row[0]] = []

                question = row[2]
                answer = row[3]

                evaluator = f'''Eres un evaluador de la expresión escrita en castellano,
                                Tu tarea es poner una nota entre el 0 y el 10 en el texto entre los delimitadores >>>RESPUESTA<<< siguiendo la rúbrica a continuación:
                                - Ortografía, gramática y puntuación:
                                    * Sin errores: 3
                                    * Con errores menores: 2
                                    * Con algunos errores significativos: 1
                                    * Con muchos errores graves: 0
                                - Estructura de las frases:
                                    * Fragmentos muy variados y bien construidos: 3
                                    * Fragmentos con alguna dificultad pero en general bien: 2
                                    * Fragmentos con algunas construcciones erróneas o difíciles: 1
                                    * Fragmentos con muchos errores o sin sentido: 0
                                - Coherencia:
                                    * Texto muy coherente y claro: 3
                                    * Texto en general coherente pero con algunas dudas: 2
                                    * Texto con algunas dificultades de coherencia: 1
                                    * Texto incoherente o difícil de seguir: 0
                                Devuelve SÓLO un valor numérico entre 0 y 10 en formato JSON según la evaluación de la rúbrica.
                                Ejemplos de valores válidos: {{"nota": "9" }}, {{"nota": "6" }}, {{"nota": "4" }}.
                                No añadas comentarios, explicaciones ni nada más, sólo JSON con la nota.
                                Tampoco añadas formato de salida con ```.
                                Esto es lo que se pidió a los estudiantes: "{question}".
                                >>>{answer}<<<'''

                stream = client.chat(
                    model = model,
                    messages=[{'role': 'user', 'content': evaluator}],
                    options={"temperature":0}

                )

                grade = stream['message']['content']
                print(grade)

                try:
                    data = json.loads(grade)
                    grade = float(data['nota'])
                    grades[row[0]].append((model, grade))
                except (TypeError, ValueError) as e:
                    print(f"JSON no vàlid: {e}, es prova a extreure...")
                    try:
                        grade = extract_json(grade)
                        data = json.loads(grade)
                        grade = float(data['nota'])
                        grades[row[0]].append((model, grade))
                    except:
                        print("JSON no vàlid, s'abandona l'intent...")

        for key in grades:
            sum = 0
            for grade in grades[key]:
                cur = conn.cursor()
                sql = 'INSERT INTO grades (content_id, evaluator, grade) VALUES (?, ?, ?)'
                cur.execute(sql,(key, grade[0], grade[1]))
                conn.commit()

                sum += float(grade[1])

            mean = sum / len(grades[key])

            cur = conn.cursor()
            sql = 'UPDATE content SET final_grade = ? WHERE id = ?'
            cur.execute(sql,(mean, key))
            conn.commit()

    rows = fetch_rows(conn, 'SELECT model, avg(final_grade) grade FROM content GROUP BY model ORDER BY avg(final_grade) DESC')

    for row in rows:
        print(row[0], round(float(row[1]),2))

    conn.close()

if __name__ == '__main__':
    print("Comença l'execució...")

    # Call the function with arguments
    # main(Generar contingut, nombre de repeticions, avaluar el contingut)
    main(True, 5, True)
    
    print("L'execució ha finalitzat correctament.")
