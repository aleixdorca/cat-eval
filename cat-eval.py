import os
import json
import regex
import sqlite3

from ollama import Client
from dotenv import load_dotenv

load_dotenv()

ollama_host = os.getenv("LLM_BASE_URL")
db_name = os.getenv("DB_NAME")

# IMPORTANT: Creació de la base de dades i les taules de dades
# > sqlite3 cat-eval.db
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

    questions = ["Escriu un text en català de 150 paraules sobre la importància de la IA",
                "Escriu un text en català de 150 paraules sobre els beneficis de la lectura habitual",
                "Escriu un text en català de 150 paraules sobre la importància de l'esport en la vida quotidiana",
                "Escriu un text en català de 150 paraules sobre les xarxes socials: avantatges i inconvenients",
                "Escriu un text en català de 150 paraules sobre el problema del canvi climàtic i les seves conseqüències",
                "Escriu un text en català de 150 paraules sobre l'educació en valors a les escoles",
                "Escriu un text en català de 150 paraules sobre la influència de la publicitat en el consumisme",
                "Escriu un text en català de 150 paraules sobre les noves tecnologies: oportunitats i reptes",
                "Escriu un text en català de 150 paraules sobre l'importància de la diversitat cultural",
                "Escriu un text en català de 150 paraules sobre el paper dels voluntaris en la societat",
                "Escriu un text en català de 150 paraules sobre la necessitat de promoure l'ecoturisme"]

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

                evaluator = f'''Ets un avaluador d'expressió escrita en català,
                            La teva tasca és posar una nota entre el 0 i el 10 al text entre els delimitadors >>>RESPOSTA<<< seguint la rúbrica a continuació:
                            - Ortografia, gramàtica i puntuació:
                                * Sense errors: 3
                                * Amb errors menors: 2
                                * Amb algunes errades significatives: 1
                                * Amb moltes errades greus: 0
                            - Estructura de les frases:
                                * Fragments molt variats i ben construïts: 3
                                * Fragments amb alguna dificultat però en general bé: 2
                                * Fragments amb algunes construccions errònies o difícils: 1
                                * Fragments amb moltes errades o sense sentit: 0
                            - Coherència:
                                * Text molt coherent i clar: 3
                                * Text en general coherent però amb alguns dubtes: 2
                                * Text amb algunes dificultats de coherència: 1
                                * Text incoherent o difícil de seguir: 0
                            Retorna NOMÉS un valor numèric entre 0 i 10 en format JSON segons l'avaluació de la rúbrica.
                            Exemples de valors vàlids: {{"nota": "9" }}, {{"nota": "6" }}, {{"nota": "4" }}.
                            No afegeixis comentaris, explicacions ni res més, només el JSON amb la nota.
                            Tampoc afegeixis formatació de sortida amb ```.
                            Això és el que es va demanar als estudiants: "{question}".
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
