from flask_sqlalchemy import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Empresa(db.Model):
    __tablename__ = 'empresas'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    rtn = db.Column(db.String(30), unique=True, nullable=False)
    
    # Relaciones
    productos = db.relationship('Producto', backref='empresa', lazy=True)

class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio_costo = db.Column(db.Float, nullable=False)    # Clave para utilidad neta
    precio_venta = db.Column(db.Float, nullable=False)    # Precio al público
    stock = db.Column(db.Integer, default=0, nullable=False)
    
    # Llave foránea para Multi-Empresa
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)

class Venta(db.Model):
    __tablename__ = 'ventas'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    total_venta = db.Column(db.Float, nullable=False)
    ganancia_neta = db.Column(db.Float, nullable=False)     # (Precio Venta - Precio Costo) * Cantidad
    fecha = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)