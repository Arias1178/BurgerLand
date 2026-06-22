from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from database.database import Base
import datetime
import enum 

class UserRole(enum.Enum):
    ADMIN = "Administrador"
    VENDEDOR = "Vendedor"


class rol(Base):
    __tablename__= "rol"

    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)

class estado_usuarios(Base):
    __tablename__= "estado_usuarios"

    id_estado = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)

class estados_productos(Base):
    __tablename__= "estados_productos"

    id_estado_producto = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)

class estados_caja(Base):
    __tablename__= "estados_caja"

    id_estado_caja = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)

class metodos_pago(Base):
    __tablename__= "metodos_pago"

    id_metodos_pago = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)

class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, index=True, nullable=False)
    contraseña = Column(String, nullable=False)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), index=True)
    id_estado = Column(Integer, ForeignKey("estados_usuarios.id_estado"), index=True)

class categorias(Base):
    __tablename__= "categorias"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)
    descripcion = Column (String, nullable=True)

class proveedores(Base):
    __tablename__ = "proveedores"

    id_proveedor = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    correo = Column(String, unique=True, index=True, nullable=False)

class productos(Base):
    __tablename__ = "productos"

    id_producto = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    descripcion = Column(String, nullable=True)
    id_categoria = Column(Integer, ForeignKey("categorias.id_categoria"), index=True)
    id_estado = Column(Integer, ForeignKey("estados_productos.id_estado_producto"), index=True)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), index=True)


class caja(Base):
    __tablename__="caja"

    id_caja = Column(Integer, primary_key=True, index=True)   
    fecha_apertura = Column(DateTime, nullable=False)
    fecha_cierre  = Column(DateTime, nullable=True)
    saldo_inicial  = Column(Float, nullable=False)
    saldo_final   =  Column(Float, nullable=True)
    id_estado_caja  =  Column(Integer, ForeignKey("estados_caja.id_estado_caja"), index=True)
    id_usuario =  Column(Integer, ForeignKey("usuarios.id_usuario"), index=True)

class movimiento_caja(Base):
    __tablename__="movimiento_caja"

    id_movimiento = Column(Integer, primary_key=True, index=True)   
    fecha = Column(DateTime, nullable=False)
    tipo  = Column(String, nullable=True)
    valor  = Column(Float, nullable=False)
    descripcion   =  Column(String, nullable=True)
    id_caja  =  Column(Integer, ForeignKey("caja.id_caja"), index=True)

class ventas(Base):
    __tablename__="ventas"

    id_venta = Column(Integer, primary_key=True, index=True)  
    fecha_hora  = Column(DateTime, nullable=False)
    total     = Column(Float, nullable=False)
    id_estado_ventas  = Column(Integer, ForeignKey("estado_ventas.id_estado_venta"), index=True)
    id_caja  = Column(Integer, ForeignKey("caja.id_caja"), index=True) 
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), index=True)
    id_metodos_pagos = Column(Integer, ForeignKey("metodos_pago.id_metodos_pago"), index=True) 

class estado_ventas(Base):
    __tablename__="estado_ventas"

    id_estado_venta = Column(Integer, primary_key=True, index=True)  
    nombre = Column(String, nullable=False)

class detalle_ventas(Base):
    __tablename__="detalle_ventas"

    id_detalle = Column(Integer, primary_key=True, index=True)  
    cantidad  = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal  = Column(Float, nullable=False)
    id_venta  = Column(Integer, ForeignKey("ventas.id_venta"), index=True) 
    id_producto  = Column(Integer, ForeignKey("productos.id_producto"), index=True)

class compras(Base):
    __tablename__="compras"

    id_compra = Column(Integer, primary_key=True, index=True)  
    fecha = Column(DateTime, nullable=False)
    total = Column(Float, nullable=False)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), index=True)

class detalles_compras (Base):
    __tablename__="detalles_compras"

    id_detalle_compras = Column(Integer, primary_key=True, index=True)  
    cantidad = Column(Integer, nullable=False)  
    precio = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    id_compra = Column(Integer, ForeignKey("compras.id_compra"), index=True)
    id_producto = Column(Integer, ForeignKey("productos.id_producto"), index=True)

class informes(Base):
    __tablename__ = "informes"

    id_informe = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    ventas_totales = Column(Float, nullable=False)
    productos_vendidos = Column(Integer, nullable=False)
    clientes_atendidos = Column(Integer, nullable=False)
    total_efectivo = Column(Float, nullable=False)
    total_tarjeta = Column(Float, nullable=False)
    total_nequi = Column(Float, nullable=False)
    saldo_inicial = Column(Float, nullable=False)
    saldo_final = Column(Float, nullable=False)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True)     

