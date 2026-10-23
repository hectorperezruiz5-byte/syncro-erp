from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import random
import string
import urllib.parse
import json

app = Flask(__name__)
app.secret_key = 'syncro_secret_key_super_segura'

CARPETA_SUBIDAS = os.path.join('static', 'uploads')
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)
app.config['UPLOAD_FOLDER'] = CARPETA_SUBIDAS

def obtener_conexion():
    conexion = sqlite3.connect('database.db')
    conexion.row_factory = sqlite3.Row
    return conexion

def inicializar_bd():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            clave TEXT NOT NULL,
            clave_tienda TEXT UNIQUE NOT NULL,
            whatsapp TEXT,
            logo_empresa TEXT,
            tema_activo TEXT DEFAULT 'esmeralda'
        )
    ''')
    
    # Asegurar campos si la tabla ya existia
    try:
        cursor.execute('ALTER TABLE usuarios ADD COLUMN logo_empresa TEXT')
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio_costo REAL NOT NULL,
            precio_venta REAL NOT NULL,
            stock INTEGER NOT NULL,
            imagen TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_ticket TEXT,
            producto_id INTEGER,
            cantidad INTEGER NOT NULL,
            descuento REAL DEFAULT 0.0,
            total REAL NOT NULL,
            cliente TEXT,
            fecha TEXT NOT NULL,
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            categoria TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS creditos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefono TEXT,
            descripcion TEXT NOT NULL,
            monto REAL NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            fecha TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefono TEXT,
            producto_id INTEGER,
            cantidad INTEGER NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            fecha TEXT NOT NULL,
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (id, nombre_empresa, usuario, clave, clave_tienda, whatsapp, logo_empresa, tema_activo)
        VALUES (1, 'Design Print Store', 'hector@syncro.com', 'Syncro2026', 'designprint', '50490000000', '', 'esmeralda')
    ''')
    conexion.commit()
    conexion.close()

inicializar_bd()

@app.context_processor
def inject_theme():
    tema = session.get('tema_activo', 'esmeralda')
    if tema == 'esmeralda':
        estilos_tema = """
            body { background: linear-gradient(135deg, #062b1e 0%, #0a3d2b 50%, #031710 100%) !important; color: #ffffff !important; }
            .navbar-custom, footer, .header-tienda { background-color: #041f15 !important; border-bottom: 2px solid #00e676 !important; }
            .card-dashboard, .card-modulo, .card-producto { background: linear-gradient(145deg, #083827, #05271b) !important; border: 1px solid #00e676 !important; color: #ffffff !important; }
            .btn-primary { background-color: #00e676 !important; border-color: #00e676 !important; color: #000000 !important; font-weight: bold; }
        """
    elif tema == 'purpura':
        estilos_tema = """
            body { background: linear-gradient(135deg, #1d0933 0%, #2a0845 50%, #120321 100%) !important; color: #ffffff !important; }
            .navbar-custom, footer, .header-tienda { background-color: #140524 !important; border-bottom: 2px solid #a855f7 !important; }
            .card-dashboard, .card-modulo, .card-producto { background: linear-gradient(145deg, #280a48, #1a0530) !important; border: 1px solid #a855f7 !important; color: #ffffff !important; }
            .btn-primary { background-color: #a855f7 !important; border-color: #a855f7 !important; color: #ffffff !important; font-weight: bold; }
        """
    elif tema == 'red':
        estilos_tema = """
            body { background: linear-gradient(135deg, #2b0606 0%, #450808 50%, #170303 100%) !important; color: #ffffff !important; }
            .navbar-custom, footer, .header-tienda { background-color: #1f0404 !important; border-bottom: 2px solid #ff1744 !important; }
            .card-dashboard, .card-modulo, .card-producto { background: linear-gradient(145deg, #3d0a0a, #260505) !important; border: 1px solid #ff1744 !important; color: #ffffff !important; }
            .btn-primary { background-color: #ff1744 !important; border-color: #ff1744 !important; color: #ffffff !important; font-weight: bold; }
        """
    else:
        estilos_tema = """
            body { background: linear-gradient(135deg, #091e3a 0%, #203a43 50%, #071326 100%) !important; color: #ffffff !important; }
            .navbar-custom, footer, .header-tienda { background-color: #061529 !important; border-bottom: 2px solid #00b0ff !important; }
            .card-dashboard, .card-modulo, .card-producto { background: linear-gradient(145deg, #0d2a4d, #081a33) !important; border: 1px solid #00b0ff !important; color: #ffffff !important; }
            .btn-primary { background-color: #00b0ff !important; border-color: #00b0ff !important; color: #000000 !important; font-weight: bold; }
        """
    return dict(estilos_tema=estilos_tema)

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'usuario_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        clave = request.form['clave'].strip()
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE usuario = ? AND clave = ?', (usuario, clave))
        user = cursor.fetchone()
        conexion.close()
        if user:
            session['usuario_id'] = user['id']
            session['nombre_empresa'] = user['nombre_empresa']
            session['clave_tienda'] = user['clave_tienda']
            session['logo_empresa'] = user['logo_empresa'] or ''
            session['tema_activo'] = user['tema_activo'] or 'esmeralda'
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos.', 'error')
    return render_template('login.html')

# --- REGISTRO NUEVO DE MICROEMPRESA ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_empresa = request.form['nombre_empresa'].strip()
        usuario = request.form['usuario'].strip()
        clave = request.form['clave'].strip()
        whatsapp = request.form['whatsapp'].strip()
        
        logo_path = ''
        if 'logo_archivo' in request.files:
            file = request.files['logo_archivo']
            if file and file.filename != '':
                nombre_archivo = f"logo_{random.randint(1000,9999)}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))
                logo_path = f"/static/uploads/{nombre_archivo}"

        clave_tienda = nombre_empresa.lower().replace(" ", "")
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute('''
                INSERT INTO usuarios (nombre_empresa, usuario, clave, clave_tienda, whatsapp, logo_empresa)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nombre_empresa, usuario, clave, clave_tienda, whatsapp, logo_path))
            conexion.commit()
            flash('¡Microempresa registrada con éxito! Ya puedes iniciar sesión.', 'success')
            conexion.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conexion.close()
            flash('El correo o nombre de empresa ya está registrado.', 'error')
            
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(v.total), 0) as total_ventas,
               COALESCE(SUM(v.cantidad * p.precio_costo), 0) as total_costos
        FROM ventas v JOIN productos p ON v.producto_id = p.id
    ''')
    res = cursor.fetchone()
    total_ventas = res['total_ventas'] if res else 0.0
    total_costos = res['total_costos'] if res else 0.0
    cursor.execute('SELECT COALESCE(SUM(monto), 0) as total_gastos FROM gastos')
    res_g = cursor.fetchone()
    total_gastos = res_g['total_gastos'] if res_g else 0.0
    utilidad_neta = total_ventas - total_costos - total_gastos
    cursor.execute('SELECT id, nombre, stock FROM productos WHERE stock <= 3 ORDER BY stock ASC')
    stock_bajo = cursor.fetchall()
    cursor.execute('''
        SELECT p.id, p.cliente, p.telefono, p.cantidad, p.fecha, prod.nombre as producto_nombre
        FROM pedidos p LEFT JOIN productos prod ON p.producto_id = prod.id
        WHERE p.estado = "Pendiente" ORDER BY p.fecha DESC
    ''')
    pedidos = cursor.fetchall()
    conexion.close()
    return render_template('dashboard.html', total_ventas=total_ventas, total_costos=total_costos, total_gastos=total_gastos, utilidad_neta=utilidad_neta, stock_bajo=stock_bajo, pedidos_pendientes=pedidos)

@app.route('/inventario')
def inventario():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM productos ORDER BY nombre ASC')
    productos = cursor.fetchall()
    conexion.close()
    return render_template('inventario.html', productos=productos)

@app.route('/agregar-producto', methods=['POST'])
def agregar_producto():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    nombre = request.form['nombre']
    descripcion = request.form.get('descripcion', '')
    precio_costo = float(request.form.get('precio_costo', 0))
    precio_venta = float(request.form.get('precio_venta', 0))
    stock = int(request.form.get('stock', 0))
    imagen_path = ''
    if 'foto_archivo' in request.files:
        file = request.files['foto_archivo']
        if file and file.filename != '':
            nombre_archivo = f"{random.randint(1000,9999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))
            imagen_path = f"/static/uploads/{nombre_archivo}"
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('INSERT INTO productos (nombre, descripcion, precio_costo, precio_venta, stock, imagen) VALUES (?, ?, ?, ?, ?, ?)',
                   (nombre, descripcion, precio_costo, precio_venta, stock, imagen_path))
    conexion.commit()
    conexion.close()
    flash('¡Producto agregado correctamente!', 'success')
    return redirect(url_for('inventario'))

@app.route('/editar-producto/<int:id>', methods=['POST'])
def editar_producto(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    nombre = request.form['nombre']
    descripcion = request.form.get('descripcion', '')
    precio_costo = float(request.form.get('precio_costo', 0))
    precio_venta = float(request.form.get('precio_venta', 0))
    stock = int(request.form.get('stock', 0))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT imagen FROM productos WHERE id = ?', (id,))
    prod_act = cursor.fetchone()
    imagen_path = prod_act['imagen'] if prod_act else ''
    if 'foto_archivo' in request.files:
        file = request.files['foto_archivo']
        if file and file.filename != '':
            nombre_archivo = f"{random.randint(1000,9999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))
            imagen_path = f"/static/uploads/{nombre_archivo}"
    cursor.execute('UPDATE productos SET nombre=?, descripcion=?, precio_costo=?, precio_venta=?, stock=?, imagen=? WHERE id=?',
                   (nombre, descripcion, precio_costo, precio_venta, stock, imagen_path, id))
    conexion.commit()
    conexion.close()
    flash('¡Producto actualizado!', 'success')
    return redirect(url_for('inventario'))

@app.route('/eliminar-producto/<int:id>', methods=['POST'])
def eliminar_producto(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('DELETE FROM productos WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    flash('Producto eliminado.', 'info')
    return redirect(url_for('inventario'))

@app.route('/ventas')
def ventas():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM productos WHERE stock > 0 ORDER BY nombre ASC')
    productos = cursor.fetchall()
    cursor.execute('''
        SELECT v.id, v.codigo_ticket, v.fecha, v.cliente, v.cantidad, v.descuento, v.total, p.nombre as producto_nombre
        FROM ventas v JOIN productos p ON v.producto_id = p.id ORDER BY v.fecha DESC
    ''')
    ventas_list = cursor.fetchall()
    conexion.close()
    return render_template('ventas.html', productos=productos, ventas=ventas_list)

@app.route('/registrar-venta-multiple', methods=['POST'])
def registrar_venta_multiple():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    cliente = request.form.get('cliente', '').strip() or "Cliente General"
    detalle_json = request.form.get('detalle_venta_json', '[]')
    
    try:
        items = json.loads(detalle_json)
    except:
        items = []

    if not items:
        flash('No hay productos agregados en el carrito de venta.', 'error')
        return redirect(url_for('ventas'))

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    caracteres = string.ascii_uppercase + string.digits
    codigo_ticket = f"TCK-{''.join(random.choices(caracteres, k=4))}"
    
    prime_id = None
    for item in items:
        prod_id = item['id']
        cant = item['cantidad']
        
        cursor.execute('SELECT precio_venta, stock FROM productos WHERE id = ?', (prod_id,))
        prod = cursor.fetchone()
        
        if prod and prod['stock'] >= cant:
            subtotal = prod['precio_venta'] * cant
            cursor.execute('''
                INSERT INTO ventas (codigo_ticket, producto_id, cantidad, descuento, total, cliente, fecha)
                VALUES (?, ?, ?, 0.0, ?, ?, datetime('now', 'localtime'))
            ''', (codigo_ticket, prod_id, cant, subtotal, cliente))
            
            cursor.execute('SELECT last_insert_rowid() as id')
            prime_id = cursor.fetchone()['id']
            cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cant, prod_id))

    conexion.commit()
    conexion.close()

    if prime_id:
        session['ultima_venta_id'] = prime_id
        flash(f'¡Venta múltiple registrada con éxito! Ticket: {codigo_ticket}', 'success')
    else:
        flash('Error al procesar la venta.', 'error')

    return redirect(url_for('ventas'))

@app.route('/anular-venta', methods=['POST'])
def anular_venta():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    venta_id = request.form.get('venta_id', '').strip()
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute('SELECT * FROM ventas WHERE codigo_ticket = ? OR id = ?', (venta_id, venta_id))
    ventas_encontradas = cursor.fetchall()
    
    if ventas_encontradas:
        for v in ventas_encontradas:
            cursor.execute('UPDATE productos SET stock = stock + ? WHERE id = ?', (v['cantidad'], v['producto_id']))
            cursor.execute('DELETE FROM ventas WHERE id = ?', (v['id'],))
        conexion.commit()
        flash(f'¡Ticket #{venta_id} anulado exitosamente!', 'success')
    else:
        flash('Ticket no encontrado.', 'error')
    conexion.close()
    return redirect(url_for('ventas'))

@app.route('/generar-recibo/<int:venta_id>')
def generar_recibo(venta_id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute('SELECT codigo_ticket FROM ventas WHERE id = ?', (venta_id,))
    res = cursor.fetchone()
    if not res:
        conexion.close()
        flash('Venta no encontrada.', 'error')
        return redirect(url_for('ventas'))
        
    codigo_t = res['codigo_ticket']
    cursor.execute('''
        SELECT v.*, p.nombre as producto_nombre, p.precio_venta 
        FROM ventas v JOIN productos p ON v.producto_id = p.id 
        WHERE v.codigo_ticket = ?
    ''', (codigo_t,))
    items_venta = cursor.fetchall()
    
    # Obtener el logo de la empresa activa
    cursor.execute('SELECT logo_empresa FROM usuarios WHERE id = ?', (session['usuario_id'],))
    u = cursor.fetchone()
    logo_empresa = u['logo_empresa'] if u else ''
    
    conexion.close()
    return render_template('recibo.html', items=items_venta, codigo_ticket=codigo_t, nombre_empresa=session.get('nombre_empresa', 'Syncro'), logo_empresa=logo_empresa)

@app.route('/gastos')
def gastos():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM gastos ORDER BY fecha DESC')
    lista = cursor.fetchall()
    cursor.execute('SELECT COALESCE(SUM(monto), 0) as total FROM gastos')
    total = cursor.fetchone()['total']
    conexion.close()
    return render_template('gastos.html', gastos=lista, total_gastos=total)

@app.route('/agregar-gasto', methods=['POST'])
def agregar_gasto():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('INSERT INTO gastos (descripcion, categoria, monto, fecha) VALUES (?, ?, ?, datetime("now", "localtime"))',
                   (request.form['descripcion'], request.form['categoria'], float(request.form['monto'])))
    conexion.commit()
    conexion.close()
    flash('Gasto guardado.', 'success')
    return redirect(url_for('gastos'))

@app.route('/creditos')
def creditos():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM creditos ORDER BY fecha DESC')
    lista = cursor.fetchall()
    cursor.execute('SELECT COALESCE(SUM(monto), 0) as total FROM creditos WHERE estado = "Pendiente"')
    total = cursor.fetchone()['total']
    conexion.close()
    return render_template('creditos.html', creditos=lista, total_pendiente=total)

@app.route('/agregar-credito', methods=['POST'])
def agregar_credito():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('INSERT INTO creditos (cliente, telefono, descripcion, monto, estado, fecha) VALUES (?, ?, ?, ?, "Pendiente", datetime("now", "localtime"))',
                   (request.form['cliente'], request.form.get('telefono',''), request.form['descripcion'], float(request.form['monto'])))
    conexion.commit()
    conexion.close()
    flash('Crédito registrado.', 'success')
    return redirect(url_for('creditos'))

@app.route('/pagar-credito/<int:id>', methods=['POST'])
def pagar_credito(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('UPDATE creditos SET estado = "Pagado" WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('creditos'))

@app.route('/tienda/<clave>')
def tienda_publica(clave):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE clave_tienda = ?', (clave,))
    empresa = cursor.fetchone()
    cursor.execute('SELECT * FROM productos WHERE stock > 0 ORDER BY nombre ASC')
    productos = cursor.fetchall()
    conexion.close()
    return render_template('tienda_publica.html', empresa=empresa, productos=productos)

@app.route('/realizar-pedido', methods=['POST'])
def realizar_pedido():
    clave_tienda = request.form.get('clave_tienda')
    cliente = request.form.get('cliente', '').strip()
    telefono = request.form.get('telefono', '').strip()
    tipo_entrega = request.form.get('tipo_entrega', 'Pasar a Recoger')
    forma_pago = request.form.get('forma_pago', 'Efectivo')
    detalle_json = request.form.get('detalle_pedido_json', '[]')
    
    try:
        items = json.loads(detalle_json)
    except:
        items = []

    if not items:
        flash('El carrito estaba vacío.', 'error')
        return redirect(url_for('tienda_publica', clave=clave_tienda))

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT whatsapp, nombre_empresa FROM usuarios WHERE clave_tienda = ?', (clave_tienda,))
    empresa = cursor.fetchone()

    resumen_texto = f"¡Hola {empresa['nombre_empresa']}! Mi nombre es *{cliente}*.\nDeseo confirmar mi pedido:\n\n"
    monto_total = 0.0

    for item in items:
        subtotal = item['precio'] * item['cantidad']
        monto_total += subtotal
        resumen_texto += f"• {item['cantidad']}x {item['nombre']} - L. {subtotal:.2f}\n"

        cursor.execute('''
            INSERT INTO pedidos (cliente, telefono, producto_id, cantidad, estado, fecha)
            VALUES (?, ?, ?, ?, 'Pendiente', datetime('now', 'localtime'))
        ''', (cliente, telefono, item['id'], item['cantidad']))

    conexion.commit()
    conexion.close()

    resumen_texto += f"\n*Total a pagar: L. {monto_total:.2f}*"
    resumen_texto += f"\n*Entrega:* {tipo_entrega}"
    resumen_texto += f"\n*Forma de Pago:* {forma_pago}"

    num_wa = empresa['whatsapp'] or '50490000000'
    if not num_wa.startswith('504') and len(num_wa) == 8:
        num_wa = f"504{num_wa}"

    mensaje_url = urllib.parse.quote(resumen_texto)
    url_whatsapp = f"https://wa.me/{num_wa}?text={mensaje_url}"

    return redirect(url_whatsapp)

@app.route('/completar-pedido/<int:id>', methods=['POST'])
def completar_pedido(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM pedidos WHERE id = ?', (id,))
    ped = cursor.fetchone()
    
    if ped and ped['estado'] == 'Pendiente':
        producto_id = ped['producto_id']
        cantidad = ped['cantidad']
        cliente = ped['cliente']
        
        cursor.execute('SELECT precio_venta, stock FROM productos WHERE id = ?', (producto_id,))
        prod = cursor.fetchone()
        
        if prod and prod['stock'] >= cantidad:
            total_venta = prod['precio_venta'] * cantidad
            caracteres = string.ascii_uppercase + string.digits
            codigo_ticket = f"TCK-ONLINE-{''.join(random.choices(caracteres, k=3))}"
            
            cursor.execute('UPDATE pedidos SET estado = "Completado" WHERE id = ?', (id,))
            cursor.execute('''
                INSERT INTO ventas (codigo_ticket, producto_id, cantidad, descuento, total, cliente, fecha)
                VALUES (?, ?, ?, 0.0, ?, ?, datetime('now', 'localtime'))
            ''', (codigo_ticket, producto_id, cantidad, total_venta, f"{cliente} (Online)"))
            cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, producto_id))
            conexion.commit()
            flash(f'¡Pedido de {cliente} procesado con éxito! Ticket generado: {codigo_ticket}', 'success')
        else:
            flash('No hay stock suficiente en inventario para procesar este pedido.', 'error')
    
    conexion.close()
    return redirect(url_for('dashboard'))

@app.route('/reporte-financiero')
def reporte_financiero():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT p.nombre, SUM(v.cantidad) as total_vendidos, SUM(v.total) as ingresos_totales,
               SUM(v.cantidad * p.precio_costo) as costos_totales,
               SUM(v.total - (v.cantidad * p.precio_costo)) as ganancia_bruta
        FROM ventas v JOIN productos p ON v.producto_id = p.id GROUP BY p.id
    ''')
    reporte = cursor.fetchall()
    conexion.close()
    return render_template('reporte_financiero.html', reporte_productos=reporte)

@app.route('/personalizar')
def personalizar():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    return render_template('personalizar.html')

@app.route('/cambiar-tema', methods=['POST'])
def cambiar_tema():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    nuevo_tema = request.form.get('tema', 'esmeralda')
    session['tema_activo'] = nuevo_tema
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('UPDATE usuarios SET tema_activo = ? WHERE id = ?', (nuevo_tema, session['usuario_id']))
    conexion.commit()
    conexion.close()
    flash('¡Tema actualizado!', 'success')
    return redirect(url_for('personalizar'))

if __name__ == '__main__':
    app.run(debug=True)