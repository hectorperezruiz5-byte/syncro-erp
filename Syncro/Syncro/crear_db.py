import sqlite3
from database.conexion import obtener_conexion

def inicializar_base_datos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # 1. Tabla de Usuarios / Microempresas (con correo y clave)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            clave_tienda TEXT UNIQUE NOT NULL,
            rol TEXT DEFAULT 'admin'
        )
    ''')
    
    # 2. Tabla de Productos (Inventario)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio_costo REAL NOT NULL,
            precio_venta REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    
    # 3. Tabla de Ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            cantidad INTEGER NOT NULL,
            total REAL NOT NULL,
            cliente TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    
    # 4. Tabla de Compras (Insumos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT NOT NULL,
            producto_id INTEGER,
            cantidad INTEGER NOT NULL,
            precio_costo REAL NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    
    conexion.commit()
    conexion.close()
    print("¡Base de datos 'syncro.db' creada con éxito y totalmente limpia!")

if __name__ == '__main__':
    inicializar_base_datos()