from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "clave_secreta"

def init_database():
    conn = sqlite3.connect("eventos.db")
    conn.execute("DROP TABLE eventos")
    conn.execute("DROP TABLE inscripciones")
    conn.execute("DROP TABLE users")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eventos(
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            anfitrion TEXT NOT NULL,
            fecha DATE NOT NULL,
            hora TEXT NOT NULL,
            maximo INTEGER NOT NULL,
            vestimenta TEXT NOT NULL
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS inscripciones(
        id INTEGER PRIMARY KEY,
        evento_id INTEGER,
        username TEXT NOT NULL,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL,
        UNIQUE(evento_id, username),
        FOREIGN KEY(evento_id) REFERENCES eventos(id)
    )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_database()

@app.route("/")
def index():
    if not session.get("user"):
        return redirect("/login")
    
    conn = sqlite3.connect("eventos.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Obtener todos los eventos
    cursor.execute("SELECT * from eventos")
    even = cursor.fetchall()
    
    # 2. Obtener el TOTAL de inscritos por cada evento (para el contador 0/maximo)
    cursor.execute("SELECT evento_id, count(*) AS total FROM inscripciones GROUP BY evento_id")
    asistencias = cursor.fetchall()
    inscritos_dict = {row["evento_id"]: row["total"] for row in asistencias}
    
    # 3. Obtener los IDs de los eventos donde está inscrito el usuario ACTUAL
    cursor.execute("SELECT evento_id FROM inscripciones WHERE username=?", (session["user"],))
    mias = cursor.fetchall()
    inscritos_usuario = [row["evento_id"] for row in mias] # Lista de IDs
    
    conn.close()
    
    return render_template(
        "index.html",
        even=even,
        inscritos=inscritos_dict, # Conteo total
        mios=inscritos_usuario    # Lista para el botón desinscribir
    )

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            conn = sqlite3.connect("eventos.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users(username,password) VALUES (?,?)", (username,password))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            return "El usuario ya existe"
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("eventos.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/")
        return "Credenciales incorrectas"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/crear")
def crear():
    if not session.get("user"):
        return redirect("/login")
    return render_template("crear.html")

@app.route("/guardar", methods=['POST'])
def guardar():
    if not session.get("user"):
        return redirect("/login")
    
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    anfitrion = session.get("user")
    fecha = request.form['fecha']
    hora = request.form['hora']
    maximo = int(request.form['maximo'])
    vestimenta = request.form['vestimenta']

    conn = sqlite3.connect("eventos.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO eventos(nombre,descripcion,anfitrion,fecha,hora,maximo,vestimenta)
        VALUES (?,?,?,?,?,?,?)
    """, (nombre,descripcion,anfitrion,fecha,hora,maximo,vestimenta))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/editar/<int:id>")
def editar(id):
    if not session.get("user"):
        return redirect("/login")
    
    conn = sqlite3.connect("eventos.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * from eventos WHERE id=?", (id,))
    evento = cursor.fetchone()
    conn.close()

    if evento and evento["anfitrion"] == session.get("user"):
        return render_template("editar.html", even=evento)
    return redirect("/")

@app.route("/actualizar/<int:id>", methods=['POST'])
def actualizar(id):
    if not session.get("user"):
        return redirect("/login")
    
    conn = sqlite3.connect("eventos.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT anfitrion FROM eventos WHERE id=?", (id,))
    evento = cursor.fetchone()
    
    if evento and evento[0] == session.get("user"):
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        fecha = request.form['fecha']
        hora = request.form['hora']
        maximo = int(request.form['maximo'])
        vestimenta = request.form['vestimenta']
        
        cursor.execute("""
            UPDATE eventos SET nombre=?,descripcion=?,fecha=?,hora=?,maximo=?,vestimenta=? WHERE id=?
        """, (nombre,descripcion,fecha,hora,maximo,vestimenta,id))
        conn.commit()
    
    conn.close()
    return redirect("/")

@app.route("/inscribir/<int:id>")
def inscribir(id):
    if not session.get("user"):
        return redirect("/login")
    conn = sqlite3.connect("eventos.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM eventos WHERE id=?", (id,))
    evento = cursor.fetchone()
    conn.close()
    return render_template("inscribir.html", evento=evento)

@app.route("/guardar_inscripcion/<int:id>", methods=["POST"])
def guardar_inscripcion(id):
    if not session.get("user"):
        return redirect("/login")
        
    nombre = request.form["nombre"]
    email = request.form["email"]
    
    conn = sqlite3.connect("eventos.db")
    cursor = conn.cursor()
    try:
        # Faltaba la palabra VALUES y los (?)
        cursor.execute("""
            INSERT INTO inscripciones(evento_id, username, nombre, email)
            VALUES (?, ?, ?, ?)
        """, (id, session["user"], nombre, email))
        conn.commit()
    except Exception as e:
        print(f"Error al inscribir: {e}")
    finally:
        conn.close()
    return redirect("/")

@app.route("/eliminar/<int:id>")
def eliminar_evento(id):
    if not session.get("user"):
        return redirect("/login")
    
    conn = sqlite3.connect("eventos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT anfitrion FROM eventos WHERE id=?", (id,))
    evento = cursor.fetchone()
    
    if evento and evento[0] == session.get("user"):
        cursor.execute("DELETE FROM eventos WHERE id=?", (id,))
        cursor.execute("DELETE FROM inscripciones WHERE evento_id=?", (id,))
        conn.commit()
    conn.close()
    return redirect("/")

@app.route("/desinscribir/<int:id>")
def desinscribir(id):
    if not session.get("user"):
        return redirect("/login")

    conn = sqlite3.connect("eventos.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM inscripciones
        WHERE evento_id=? AND username=?
    """, (id, session["user"]))

    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)