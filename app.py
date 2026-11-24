
# Tienda Virtual - Heladería Karina EIRL (Satipo)
# Tecnologías: Python + Flask (servidor), HTML + CSS (pantallas), SQLite (datos)

import os, re, sqlite3, datetime, uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "karina-eirl-2026"          # necesaria para sesiones (carrito, login)

# ---------- CONFIGURACIÓN EDITABLE (cambia estos datos a los reales) ----------
NEGOCIO = {
    "nombre": "Heladería Karina",
    "direccion": "Jr. Francisco Irazola 591, Satipo, Junín, Perú",
    "telefono": "921 581 683",
    "horario": "De lunes a Domingo 7:00 am -10:30 pm",
    "yape": "921 581 683",          # número al que pagan con Yape/Plin
    "qr_yape": "qr_yape.svg",                 # imagen del QR dentro de static/img/
}
CLAVE_ADMIN = "karina2026"                    # contraseña del panel /admin
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.db")   # ruta completa
CARPETA_IMG = os.path.join(app.root_path, "static", "img")   # ruta completa: aquí se guardan las fotos
os.makedirs(CARPETA_IMG, exist_ok=True)                      # crea la carpeta si no existe
EXT_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}

# Productos iniciales (solo se cargan la primera vez; luego se editan desde /admin/productos)
PRODUCTOS_INICIALES = [
    # (categoría, nombre, descripción, precio, emoji, imagen)  -> precios REFERENCIALES, edítalos en /admin/productos
    ("Helados", "Helado minihamburguesa", "Crema batida de fresa con mini barquillo, chocolate y chispas de colores", 8.00, "🍔", "minihamburguesa.png"),
    ("Combos", "Banana split", "Combo de helados con plátano, barquillos y toppings", 12.00, "🍌", "banana_split.png"),
    ("Jugos", "Jugo de plátano con leche", "Jugo de fruta cremoso y fresco", 5.00, "🥤", "jugo_platano.jpg"),
    ("Helados", "Copa de helado Karina", "Copa de helado con barquillo", 10.00, "🍨", "logo.jpg"),
    ("Helados", "Helado de vainilla", "Helado artesanal cremoso", 3.00, "🍦"),
    ("Helados", "Helado de chocolate", "Intenso sabor a cacao", 3.00, "🍫"),
    ("Helados", "Helado de fresa", "Con trocitos de fruta", 3.00, "🍓"),
    ("Helados Donofrio", "Helado Donofrio", "Variedad de la marca Donofrio", 2.50, "🍨"),
    ("Cremoladas", "Cremolada de maracuyá", "Refrescante y frutal", 4.00, "🧊"),
    ("Jugos", "Jugo de naranja", "Natural, recién exprimido", 3.50, "🍊"),
    ("Pasteles", "Porción de pastel", "Variedad del día", 5.00, "🍰"),
    ("Snacks", "Snack surtido", "Bocaditos para acompañar", 2.00, "🍿"),
    ("Chupetes", "Chupete helado", "Sabores variados", 1.50, "🍭"),
    ("Yogurts", "Yogurt de fresa", "Yogurt de 3 sabores", 3.00, "🥛"),
    ("Yogurts", "Yogurt de vainilla", "Yogurt de 3 sabores", 3.00, "🥛"),
    ("Yogurts", "Yogurt de durazno", "Yogurt de 3 sabores", 3.00, "🥛"),
]

# ---------- TEXTOS E IMÁGENES EDITABLES DE LA PÁGINA (se cambian en /admin/personalizar) ----------
CONFIG_INICIAL = {
    "titulo": "HELADERÍA KARINA",
    "lema": "DONDE ENCUENTRAS VARIEDADES DE HELADOS",
    "slogan":"Ven a Heladería Karina ",
    "slogan2": "Más que helado, es una experiencia",
    "promo_titulo": "Helados minihamburguesa a S/ 8",
    "promo_texto": "Hechos a base de crema batida de fresa, con un mini barquillo, chocolate y chispas de colores.",
    "galeria_titulo": "Los mejores momentos",
    "facebook": "https://www.facebook.com",
    "whatsapp": "https://wa.me/51921581683",
    "logo": "logo.jpg", "promo_imagen": "minihamburguesa.png",
    "galeria1": "momentos.jpg", "galeria2": "clientes.jpg", "galeria3": "karina.jpg",
}
CAMPOS_TEXTO = [("titulo", "Nombre en el encabezado"), ("lema", "Frase bajo el nombre"), ("slogan", "Eslogan"),
                ("slogan2", "Eslogan: frase grande"),
                ("promo_titulo", "Título de la promoción"), ("promo_texto", "Texto de la promoción"),
                ("galeria_titulo", "Título de la galería"), ("facebook", "Enlace de Facebook"),
                ("whatsapp", "Enlace de whatsapp ")]
CAMPOS_IMG = [("logo", "Logo / foto de perfil"), ("promo_imagen", "Imagen de la promoción"),
              ("galeria1", "Galería: foto 1"), ("galeria2", "Galería: foto 2"), ("galeria3", "Galería: foto 3")]

def guardar_imagen(archivo):
    """Guarda una foto subida desde la laptop en static/img/ y devuelve su nombre (o None si no es válida)."""
    if not archivo or not archivo.filename:
        return None
    ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in EXT_PERMITIDAS:
        flash("Formato no permitido (usa png, jpg, jpeg o webp).")
        return None
    nombre = f"{uuid.uuid4().hex[:10]}.{ext}"          # nombre único: evita problemas con tildes y espacios
    archivo.save(os.path.join(CARPETA_IMG, nombre))
    return nombre

def config():
    c = dict(CONFIG_INICIAL)
    with bd() as con:
        c.update({r["clave"]: r["valor"] for r in con.execute("SELECT clave, valor FROM config")})
    return c

# ---------- BASE DE DATOS ----------
def bd():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def iniciar_bd():
    with bd() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS productos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, nombre TEXT, descr TEXT,
            precio REAL, icono TEXT DEFAULT '🍦', imagen TEXT DEFAULT '')""")
        con.execute("CREATE TABLE IF NOT EXISTS config(clave TEXT PRIMARY KEY, valor TEXT)")
        con.execute("""CREATE TABLE IF NOT EXISTS pedidos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, telefono TEXT, hora_recojo TEXT,
            detalle TEXT, total REAL, estado TEXT DEFAULT 'Pendiente', metodo TEXT,
            pago TEXT DEFAULT 'Pendiente', referencia TEXT DEFAULT '', creado TEXT)""")
        if con.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
            con.executemany("INSERT INTO productos(cat,nombre,descr,precio,icono,imagen) VALUES(?,?,?,?,?,?)",
                            [t if len(t) == 6 else t + ("",) for t in PRODUCTOS_INICIALES])

def producto(pid):
    with bd() as con:
        return con.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()

# ---------- CARRITO (guardado en la sesión del navegador) ----------
def items_carrito():
    items, total = [], 0
    for pid, cant in session.get("carrito", {}).items():
        p = producto(int(pid))
        if p:
            sub = p["precio"] * cant
            total += sub
            items.append({"id": p["id"], "nombre": p["nombre"], "icono": p["icono"], "cant": cant, "sub": sub})
    return items, total

@app.context_processor
def globales():   # variables disponibles en TODAS las plantillas HTML
    return {"n_carrito": sum(session.get("carrito", {}).values()), "N": NEGOCIO, "C": config()}

@app.template_global()
def src_img(nombre):
    """Si es un enlace (http...) lo usa tal cual; si no, busca el archivo en static/img/."""
    if not nombre:
        return ""
    return nombre if nombre.startswith("http") else url_for("static", filename="img/" + nombre)

# ---------- PÁGINAS DEL CLIENTE ----------
@app.route("/")
def inicio():
    cat = request.args.get("cat")
    with bd() as con:
        cats = [r[0] for r in con.execute("SELECT DISTINCT cat FROM productos ORDER BY cat")]
        if cat:
            lista = con.execute("SELECT * FROM productos WHERE cat=?", (cat,)).fetchall()
        else:
            lista = con.execute("SELECT * FROM productos").fetchall()
    return render_template("index.html", productos=lista, categorias=cats, cat=cat)

@app.route("/agregar/<int:pid>")
def agregar(pid):
    p = producto(pid)
    if p:
        c = session.get("carrito", {})
        c[str(pid)] = c.get(str(pid), 0) + 1
        session["carrito"] = c
        flash(f"Agregaste «{p['nombre']}» al carrito")
    return redirect(request.referrer or url_for("inicio"))

@app.route("/carrito")
def carrito():
    items, total = items_carrito()
    return render_template("carrito.html", items=items, total=total)

@app.route("/cambiar/<int:pid>/<accion>")
def cambiar(pid, accion):
    c, k = session.get("carrito", {}), str(pid)
    if k in c:
        c[k] += 1 if accion == "mas" else -1
        if accion == "quitar" or c[k] <= 0:
            del c[k]
    session["carrito"] = c
    return redirect(url_for("carrito"))

@app.route("/pedido", methods=["GET", "POST"])
def pedido():
    items, total = items_carrito()
    if not items:
        return redirect(url_for("carrito"))
    if request.method == "POST":
        f = request.form
        nombre, tel, hora = f["nombre"].strip(), f["telefono"].strip(), f["hora"]
        metodo, operacion = f["metodo"], f.get("operacion", "").strip()
        error = None
        if not nombre or not (tel.isdigit() and len(tel) == 9):
            error = "Ingresa tu nombre y un celular de 9 dígitos."
        else:
            ahora = datetime.datetime.now()
            h, m = map(int, hora.split(":"))
            recojo = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
            if recojo < ahora + datetime.timedelta(minutes=5):      # RF05: mínimo 5 minutos
                error = "La hora de recojo debe ser al menos 5 minutos después de la hora actual."
            elif metodo == "yape" and not (operacion.isdigit() and 6 <= len(operacion) <= 12):
                error = "Ingresa el número de operación de tu Yape/Plin (solo números)."
        if error:
            flash(error)
            return render_template("pedido.html", items=items, total=total, f=f)
        detalle = "; ".join(f"{i['cant']} x {i['nombre']}" for i in items)
        pago = "Por verificar" if metodo == "yape" else "Pendiente"
        with bd() as con:
            num = con.execute(
                "INSERT INTO pedidos(cliente,telefono,hora_recojo,detalle,total,metodo,pago,referencia,creado) VALUES(?,?,?,?,?,?,?,?,?)",
                (nombre, tel, hora, detalle, total, metodo, pago, operacion, ahora.strftime("%d/%m/%Y %H:%M"))).lastrowid
        session["carrito"] = {}
        return redirect(url_for("pago", num=num) if metodo == "tarjeta" else url_for("gracias", num=num))
    return render_template("pedido.html", items=items, total=total, f={})

# ---------- PASARELA DE PAGO CON TARJETA (SIMULADA) ----------
# Una pasarela real (Culqi, Niubiz, Mercado Pago) se conecta aquí con sus llaves API.
# En esta versión se valida la tarjeta y se simula la aprobación. NUNCA se guarda el número completo.
def luhn_ok(numero):
    """Algoritmo de Luhn: verifica que el número de tarjeta sea válido."""
    digitos = [int(x) for x in numero][::-1]
    suma = sum(digitos[0::2])
    for x in digitos[1::2]:
        suma += sum(divmod(2 * x, 10))
    return suma % 10 == 0

@app.route("/pago/<int:num>", methods=["GET", "POST"])
def pago(num):
    with bd() as con:
        p = con.execute("SELECT * FROM pedidos WHERE id=?", (num,)).fetchone()
    if not p or p["pago"] == "Pagado":
        return redirect(url_for("gracias", num=num))
    if request.method == "POST":
        tarjeta = re.sub(r"\s", "", request.form["tarjeta"])
        venc, cvv = request.form["venc"].strip(), request.form["cvv"].strip()
        ok_venc = False
        if re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", venc):
            mes, anio = int(venc[:2]), 2000 + int(venc[3:])
            hoy = datetime.date.today()
            ok_venc = (anio, mes) >= (hoy.year, hoy.month)
        if not (tarjeta.isdigit() and 13 <= len(tarjeta) <= 19 and luhn_ok(tarjeta)):
            flash("Número de tarjeta inválido. (Para pruebas usa 4111 1111 1111 1111)")
        elif not ok_venc:
            flash("Fecha de vencimiento inválida o vencida (formato MM/AA).")
        elif not (cvv.isdigit() and len(cvv) in (3, 4)):
            flash("CVV inválido.")
        else:
            with bd() as con:
                con.execute("UPDATE pedidos SET pago='Pagado', referencia=? WHERE id=?", ("Tarjeta ****" + tarjeta[-4:], num))
            return redirect(url_for("gracias", num=num))
    return render_template("pago.html", p=p)

@app.route("/gracias/<int:num>")
def gracias(num):
    with bd() as con:
        p = con.execute("SELECT * FROM pedidos WHERE id=?", (num,)).fetchone()
    return render_template("gracias.html", p=p)

@app.route("/contacto")
def contacto():
    return render_template("contacto.html")

# ---------- PANEL DE ADMINISTRACIÓN ----------
def es_admin():
    return session.get("admin") is True

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("clave") == CLAVE_ADMIN:
            session["admin"] = True
        else:
            flash("Contraseña incorrecta.")
    if not es_admin():
        return render_template("admin_login.html")
    with bd() as con:
        pedidos = con.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    return render_template("admin.html", pedidos=pedidos)

@app.route("/admin/estado/<int:pid>/<campo>/<valor>")
def estado(pid, campo, valor):
    validos = {"estado": ("Pendiente", "Listo", "Entregado"), "pago": ("Pagado", "Por verificar", "Pendiente")}
    if es_admin() and campo in validos and valor in validos[campo]:
        with bd() as con:
            con.execute(f"UPDATE pedidos SET {campo}=? WHERE id=?", (valor, pid))   # campo validado arriba
    return redirect(url_for("admin"))

@app.route("/admin/productos")
def admin_productos():
    if not es_admin():
        return redirect(url_for("admin"))
    with bd() as con:
        lista = con.execute("SELECT * FROM productos ORDER BY cat, nombre").fetchall()
    editar = producto(request.args.get("editar", type=int)) if request.args.get("editar") else None
    return render_template("admin_productos.html", productos=lista, e=editar)

@app.route("/admin/productos/guardar", methods=["POST"])
def guardar_producto():
    if not es_admin():
        return redirect(url_for("admin"))
    f = request.form
    imagen = f.get("imagen_actual", "")
    ruta = f.get("imagen_ruta", "").strip()          # nombre de archivo o enlace escrito a mano
    if ruta:
        imagen = ruta
    nueva = guardar_imagen(request.files.get("imagen"))   # foto subida desde la laptop (tiene prioridad)
    if nueva:
        imagen = nueva
    datos = (f["cat"].strip(), f["nombre"].strip(), f["descr"].strip(), float(f["precio"]), f["icono"].strip() or "🍦", imagen)
    with bd() as con:
        if f.get("id"):
            con.execute("UPDATE productos SET cat=?,nombre=?,descr=?,precio=?,icono=?,imagen=? WHERE id=?", datos + (f["id"],))
        else:
            con.execute("INSERT INTO productos(cat,nombre,descr,precio,icono,imagen) VALUES(?,?,?,?,?,?)", datos)
    flash("Producto guardado.")
    return redirect(url_for("admin_productos"))

@app.route("/admin/personalizar", methods=["GET", "POST"])
def personalizar():
    if not es_admin():
        return redirect(url_for("admin"))
    if request.method == "POST":
        with bd() as con:
            for clave, _ in CAMPOS_TEXTO:
                con.execute("INSERT OR REPLACE INTO config VALUES(?,?)", (clave, request.form.get(clave, "").strip()))
            for clave, _ in CAMPOS_IMG:
                nueva = guardar_imagen(request.files.get(clave))
                ruta = request.form.get(clave + "_ruta", "").strip()
                if nueva or ruta or request.form.get(clave + "_quitar"):
                    con.execute("INSERT OR REPLACE INTO config VALUES(?,?)", (clave, nueva or ("" if request.form.get(clave + "_quitar") else ruta)))
        flash("Página actualizada.")
        return redirect(url_for("personalizar"))
    return render_template("admin_personalizar.html", textos=CAMPOS_TEXTO, imagenes=CAMPOS_IMG)

@app.route("/admin/productos/borrar/<int:pid>")
def borrar_producto(pid):
    if es_admin():
        with bd() as con:
            con.execute("DELETE FROM productos WHERE id=?", (pid,))
    return redirect(url_for("admin_productos"))

@app.route("/salir")
def salir():
    session.pop("admin", None)
    return redirect(url_for("inicio"))

iniciar_bd()
if __name__ == "__main__":
    app.run(debug=True)
