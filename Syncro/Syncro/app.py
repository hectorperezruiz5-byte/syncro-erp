from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'syncro_secret_key_super_segura'

def obtener_conexion():
    conexion = sqlite3.connect('database.db')
    conexion.row_factory = sqlite3.Row
    return conexion

# --- INICIALIZACIÓN Y CARGA AUTOMÁTICA DE TU MICROEMPRESA ---
def inicializar_bd():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Tabla Usuarios / Empresas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            clave TEXT NOT NULL,
            clave_tienda TEXT UNIQUE NOT NULL,
            whatsapp TEXT,
            tema_activo TEXT DEFAULT 'purpura'
        )
    ''')
    
    # Tabla Productos
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
    
    # Tabla Ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            cantidad INTEGER NOT NULL,
            total REAL NOT NULL,
            cliente TEXT,
            fecha TEXT NOT NULL,
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    
    # Tabla Gastos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            categoria TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL
        )
    ''')
    
    # Tabla Créditos / Fiados
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
    
    # Tabla Pedidos Tienda Virtual
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
    
    # GARANTIZAR QUE FARMACIA KIELSA SIEMPRE EXISTA
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (id, nombre_empresa, usuario, clave, clave_tienda, whatsapp, tema_activo)
        VALUES (1, 'Farmacia Kielsa', 'kielsa17@gmail.com', 'Kielsa17', 'kielsa', '99887766', 'purpura')
    ''')
    
    conexion.commit()
    conexion.close()

# Se ejecuta al iniciar el servidor
inicializar_bd()


# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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
            session['tema_activo'] = user['tema_activo'] or 'purpura'
            flash('¡Bienvenido de nuevo a Syncro!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))


# --- DASHBOARD PRINCIPAL ---
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    total_ventas = 0.0
    total_costos = 0.0
    total_gastos = 0.0
    utilidad_neta = 0.0
    stock_bajo = []
    pedidos_pendientes = []

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                COALESCE(SUM(v.total), 0) as total_ventas,
                COALESCE(SUM(v.cantidad * p.precio_costo), 0) as total_costos
            FROM ventas v
            JOIN productos p ON v.producto_id = p.id
        ''')
        res_ventas = cursor.fetchone()
        if res_ventas:
            total_ventas = res_ventas['total_ventas']
            total_costos = res_ventas['total_costos']
        
        cursor.execute('SELECT COALESCE(SUM(monto), 0) as total_gastos FROM gastos')
        res_gastos = cursor.fetchone()
        if res_gastos:
            total_gastos = res_gastos['total_gastos']
        
        utilidad_neta = total_ventas - total_costos - total_gastos
        
        cursor.execute('SELECT id, nombre, stock FROM productos WHERE stock <= 3 ORDER BY stock ASC')
        stock_bajo = cursor.fetchall()
        
        cursor.execute('''
            SELECT p.id, p.cliente, p.telefono, p.cantidad, p.estado, p.fecha, prod.nombre as producto_nombre
            FROM pedidos p
            LEFT JOIN productos prod ON p.producto_id = prod.id
            WHERE p.estado = "Pendiente"
            ORDER BY p.fecha DESC
        ''')
        pedidos_pendientes = cursor.fetchall()

    except Exception as e:
        print(f"Error en dashboard: {e}")
    finally:
        conexion.close()
    
    return render_template('dashboard.html', 
                           total_ventas=total_ventas,
                           total_costos=total_costos,
                           total_gastos=total_gastos,
                           utilidad_neta=utilidad_neta,
                           stock_bajo=stock_bajo,
                           pedidos_pendientes=pedidos_pendientes,
                           nombre_empresa=session.get('nombre_empresa', 'Syncro'))


# --- MÓDULO DE INVENTARIO ---
@app.route('/inventario')
def inventario():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM productos ORDER BY id DESC')
    productos = cursor.fetchall()
    conexion.close()
    return render_template('inventario.html', productos=productos)

@app.route('/agregar-producto', methods=['POST'])
def agregar_producto():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    nombre = request.form['nombre']
    descripcion = request.form.get('descripcion', '')
    precio_costo = round(float(request.form.get('precio_costo', 0)), 2)
    precio_venta = round(float(request.form.get('precio_venta', 0)), 2)
    stock = int(request.form.get('stock', 0))
    imagen_url = request.form.get('imagen_url', '')
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO productos (nombre, descripcion, precio_costo, precio_venta, stock, imagen)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nombre, descripcion, precio_costo, precio_venta, stock, imagen_url))
    conexion.commit()
    conexion.close()
    
    flash('¡Producto agregado exitosamente!', 'success')
    return redirect(url_for('inventario'))

@app.route('/editar-producto/<int:id>', methods=['POST'])
def editar_producto(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    precio_costo = round(float(request.form.get('precio_costo', 0)), 2)
    precio_venta = round(float(request.form.get('precio_venta', 0)), 2)
    stock = int(request.form.get('stock', 0))
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        UPDATE productos 
        SET nombre = ?, descripcion = ?, precio_costo = ?, precio_venta = ?, stock = ?
        WHERE id = ?
    ''', (nombre, descripcion, precio_costo, precio_venta, stock, id))
    conexion.commit()
    conexion.close()
    
    flash('¡Producto actualizado correctamente!', 'success')
    return redirect(url_for('inventario'))

@app.route('/eliminar-producto/<int:id>', methods=['POST'])
def eliminar_producto(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('DELETE FROM productos WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    
    flash('Producto eliminado del inventario.', 'info')
    return redirect(url_for('inventario'))


# --- MÓDULO DE VENTAS Y RECIBOS ---
@app.route('/ventas')
def ventas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM productos WHERE stock > 0 ORDER BY nombre ASC')
    productos = cursor.fetchall()
    
    cursor.execute('''
        SELECT v.id, v.fecha, v.cliente, v.cantidad, v.total, p.nombre as producto_nombre
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        ORDER BY v.fecha DESC
    ''')
    ventas_list = cursor.fetchall()
    conexion.close()
    
    return render_template('ventas.html', productos=productos, ventas=ventas_list)

@app.route('/registrar-venta', methods=['POST'])
def registrar_venta():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    producto_id = request.form['producto_id']
    cantidad = int(request.form['cantidad'])
    cliente = request.form.get('cliente', 'Cliente General')
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT precio_venta, stock FROM productos WHERE id = ?', (producto_id,))
    prod = cursor.fetchone()
    
    if prod and prod['stock'] >= cantidad:
        total = round(prod['precio_venta'] * cantidad, 2)
        cursor.execute('''
            INSERT INTO ventas (producto_id, cantidad, total, cliente, fecha)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (producto_id, cantidad, total, cliente))
        
        cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, producto_id))
        conexion.commit()
        flash('¡Venta realizada con éxito!', 'success')
    else:
        flash('Stock insuficiente para completar la venta.', 'error')
        
    conexion.close()
    return redirect(url_for('ventas'))

@app.route('/generar-recibo/<int:venta_id>')
def generar_recibo(venta_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT v.id, v.fecha, v.cliente, v.cantidad, v.total, p.nombre as producto_nombre, p.precio_venta
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        WHERE v.id = ?
    ''', (venta_id,))
    venta = cursor.fetchone()
    conexion.close()
    
    if not venta:
        flash('Venta no encontrada.', 'error')
        return redirect(url_for('ventas'))
        
    return render_template('recibo.html', venta=venta, nombre_empresa=session.get('nombre_empresa', 'Syncro'))


# --- MÓDULO DE GASTOS ---
@app.route('/gastos')
def gastos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM gastos ORDER BY fecha DESC')
    lista_gastos = cursor.fetchall()
    
    cursor.execute('SELECT COALESCE(SUM(monto), 0) as total FROM gastos')
    total_gastos = cursor.fetchone()['total']
    conexion.close()
    
    return render_template('gastos.html', gastos=lista_gastos, total_gastos=total_gastos)

@app.route('/agregar-gasto', methods=['POST'])
def agregar_gasto():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    descripcion = request.form['descripcion']
    categoria = request.form['categoria']
    monto = round(float(request.form['monto']), 2)
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO gastos (descripcion, categoria, monto, fecha)
        VALUES (?, ?, ?, datetime('now', 'localtime'))
    ''', (descripcion, categoria, monto))
    conexion.commit()
    conexion.close()
    
    flash('Gasto registrado correctamente.', 'success')
    return redirect(url_for('gastos'))


# --- MÓDULO DE FIADOS / CRÉDITOS ---
@app.route('/creditos')
def creditos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM creditos ORDER BY fecha DESC')
    lista_creditos = cursor.fetchall()
    
    cursor.execute('SELECT COALESCE(SUM(monto), 0) as total FROM creditos WHERE estado = "Pendiente"')
    total_pendiente = cursor.fetchone()['total']
    conexion.close()
    
    return render_template('creditos.html', creditos=lista_creditos, total_pendiente=total_pendiente)

@app.route('/agregar-credito', methods=['POST'])
def agregar_credito():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    cliente = request.form['cliente']
    telefono = request.form.get('telefono', '')
    descripcion = request.form['descripcion']
    monto = round(float(request.form['monto']), 2)
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO creditos (cliente, telefono, descripcion, monto, estado, fecha)
        VALUES (?, ?, ?, ?, 'Pendiente', datetime('now', 'localtime'))
    ''', (cliente, telefono, descripcion, monto))
    conexion.commit()
    conexion.close()
    
    flash('¡Cuenta por cobrar registrada!', 'success')
    return redirect(url_for('creditos'))

@app.route('/pagar-credito/<int:id>', methods=['POST'])
def pagar_credito(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('UPDATE creditos SET estado = "Pagado" WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    
    flash('¡Crédito marcado como cobrado!', 'success')
    return redirect(url_for('creditos'))


# --- TIENDA VIRTUAL Y PEDIDOS DE WHATSAPP ---
@app.route('/tienda/<clave>')
def tienda_publica(clave):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE clave_tienda = ?', (clave,))
    empresa = cursor.fetchone()
    
    if not empresa:
        conexion.close()
        return "Tienda no encontrada", 404
        
    cursor.execute('SELECT * FROM productos WHERE stock > 0 ORDER BY nombre ASC')
    productos = cursor.fetchall()
    conexion.close()
    
    return render_template('tienda_publica.html', empresa=empresa, productos=productos)

@app.route('/realizar-pedido', methods=['POST'])
def realizar_pedido():
    clave_tienda = request.form.get('clave_tienda')
    cliente = request.form.get('cliente', '').strip()
    telefono = request.form.get('telefono', '').strip()
    producto_id = request.form.get('producto_id')
    cantidad = int(request.form.get('cantidad', 1))
    tipo_entrega = request.form.get('tipo_entrega', 'Pasar a Recoger')
    forma_pago = request.form.get('forma_pago', 'Efectivo')
    
    whatsapp_empresa = request.form.get('whatsapp_empresa', '').strip()
    nombre_producto = request.form.get('nombre_producto', 'Producto')
    precio_producto = float(request.form.get('precio_producto', 0))
    total_pedido = precio_producto * cantidad
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO pedidos (cliente, telefono, producto_id, cantidad, estado, fecha)
        VALUES (?, ?, ?, ?, 'Pendiente', datetime('now', 'localtime'))
    ''', (f"{cliente} ({tipo_entrega} - {forma_pago})", telefono, producto_id, cantidad))
    conexion.commit()
    conexion.close()
    
    mensaje_wa = f"Hola, soy {cliente}. Acabo de realizar un pedido en su tienda virtual Syncro:%0A%0A" \
                 f"- *Producto:* {nombre_producto}%0A" \
                 f"- *Cantidad:* {cantidad}%0A" \
                 f"- *Total:* L. {total_pedido:.2f}%0A" \
                 f"- *Modalidad:* {tipo_entrega}%0A" \
                 f"- *Pago:* {forma_pago}%0A" \
                 f"- *Teléfono de contacto:* {telefono}%0A%0A" \
                 f"Quedo a la espera de su confirmación."
    
    if whatsapp_empresa:
        num_wa = "".join(filter(str.isdigit, whatsapp_empresa))
        url_whatsapp = f"https://api.whatsapp.com/send?phone={num_wa}&text={mensaje_wa}"
        return redirect(url_whatsapp)
        
    flash('¡Pedido registrado con éxito!', 'success')
    return redirect(url_for('tienda_publica', clave=clave_tienda))

@app.route('/completar-pedido/<int:id>', methods=['POST'])
def completar_pedido(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM pedidos WHERE id = ?', (id,))
    pedido = cursor.fetchone()
    
    if pedido:
        cursor.execute('SELECT precio_venta, stock FROM productos WHERE id = ?', (pedido['producto_id'],))
        prod = cursor.fetchone()
        
        if prod:
            total = round(prod['precio_venta'] * pedido['cantidad'], 2)
            cursor.execute('''
                INSERT INTO ventas (producto_id, cantidad, total, cliente, fecha)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            ''', (pedido['producto_id'], pedido['cantidad'], total, pedido['cliente']))
            
            cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (pedido['cantidad'], pedido['producto_id']))
            cursor.execute('UPDATE pedidos SET estado = "Completado" WHERE id = ?', (id,))
            conexion.commit()
            flash('¡Pedido completado y registrado en Ventas!', 'success')
            
    conexion.close()
    return redirect(url_for('dashboard'))


# --- PERSONALIZACIÓN DE TEMAS DE COLOR ---
@app.route('/personalizar')
def personalizar():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('personalizar.html')

@app.route('/cambiar-tema', methods=['POST'])
def cambiar_tema():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    nuevo_tema = request.form.get('tema', 'purpura')
    session['tema_activo'] = nuevo_tema
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('UPDATE usuarios SET tema_activo = ? WHERE id = ?', (nuevo_tema, session['usuario_id']))
    conexion.commit()
    conexion.close()
    
    flash('¡Tema de color actualizado en todo el sistema!', 'success')
    return redirect(url_for('personalizar'))


if __name__ == '__main__':
    app.run(debug=True)