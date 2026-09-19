<<<<<<< HEAD
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Enum
=======
from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Date
>>>>>>> Burguerland_V_1.0
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
<<<<<<< HEAD
    id_estado = Column(Integer, ForeignKey("estados_usuarios.id_estado"), index=True)
=======
    id_estado = Column(Integer, ForeignKey("estado_usuarios.id_estado"), index=True)
>>>>>>> Burguerland_V_1.0

class categorias(Base):
    __tablename__= "categorias"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column (String, nullable=False)
    descripcion = Column (String, nullable=True)
<<<<<<< HEAD
=======
    estado = Column(String, nullable=False, default="ACTIVO")
>>>>>>> Burguerland_V_1.0

class proveedores(Base):
    __tablename__ = "proveedores"

    id_proveedor = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
<<<<<<< HEAD
    telefono = Column(String, nullable=True)
    correo = Column(String, unique=True, index=True, nullable=False)
=======
    que_provee = Column(String, nullable=False, default="")
    telefono = Column(String, nullable=True)
    correo = Column(String, unique=True, index=True, nullable=False)
    cuanto_cobra = Column(Float, nullable=False, default=0)
    estado = Column(String, nullable=False, default="ACTIVO")
>>>>>>> Burguerland_V_1.0

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
<<<<<<< HEAD
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), index=True)
    id_metodos_pagos = Column(Integer, ForeignKey("metodos_pago.id_metodos_pago"), index=True) 
=======
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    id_metodos_pagos = Column(Integer, ForeignKey("metodos_pago.id_metodos_pago"), index=True) 
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), index=True, nullable=True)
    proveedores_texto = Column(String, nullable=True)
    costo_proveedor = Column(Float, nullable=False, default=0)
>>>>>>> Burguerland_V_1.0

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
<<<<<<< HEAD
    saldo_inicial = Column(Float, nullable=False)
    saldo_final = Column(Float, nullable=False)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True)     

=======
    total_proveedores = Column(Float, nullable=False, default=0)
    saldo_inicial = Column(Float, nullable=False)
    saldo_final = Column(Float, nullable=False)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True)


class categorias_gasto(Base):
    __tablename__ = "categorias_gasto"

    id_categoria_gasto = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)


class gastos(Base):
    __tablename__ = "gastos"

    id_gasto = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    id_categoria_gasto = Column(Integer, ForeignKey("categorias_gasto.id_categoria_gasto"), index=True)
    descripcion = Column(String, nullable=True)
    valor = Column(Float, nullable=False)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True, nullable=True)
    comprobante_path = Column(String, nullable=True)


class empleados(Base):
    __tablename__ = "empleados"

    id_empleado = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    cargo = Column(String, nullable=False)
    tipo_contrato = Column(String, nullable=False)
    salario_base = Column(Float, nullable=False)
    fecha_ingreso = Column(Date, nullable=False)
    fecha_retiro = Column(Date, nullable=True)
    activo = Column(Integer, nullable=False, default=1)


class parametros_legales(Base):
    """Valores legales anuales del negocio, para actualizar cada año sin tocar código."""

    __tablename__ = "parametros_legales"

    id_parametro = Column(Integer, primary_key=True, index=True)
    anio = Column(Integer, nullable=False)
    smlv = Column(Float, nullable=False)
    auxilio_transporte = Column(Float, nullable=False)
    uvt = Column(Float, nullable=False)
    pct_salud_empleador = Column(Float, nullable=False, default=0.085)
    pct_pension_empleador = Column(Float, nullable=False, default=0.12)
    pct_arl = Column(Float, nullable=False, default=0.00522)
    pct_caja_compensacion = Column(Float, nullable=False, default=0.04)
    pct_cesantias = Column(Float, nullable=False, default=1 / 12)
    pct_intereses_cesantias = Column(Float, nullable=False, default=0.12)
    pct_prima = Column(Float, nullable=False, default=1 / 12)
    pct_vacaciones = Column(Float, nullable=False, default=1 / 24)
    tarifa_impoconsumo = Column(Float, nullable=False, default=0.08)
    tarifa_rst = Column(Float, nullable=False, default=0.019)


class nomina_mensual(Base):
    __tablename__ = "nomina_mensual"

    id_nomina = Column(Integer, primary_key=True, index=True)
    id_empleado = Column(Integer, ForeignKey("empleados.id_empleado"), index=True)
    periodo = Column(String, nullable=False)
    salario_base = Column(Float, nullable=False)
    auxilio_transporte = Column(Float, nullable=False)
    salud_empleador = Column(Float, nullable=False)
    pension_empleador = Column(Float, nullable=False)
    arl = Column(Float, nullable=False)
    caja_compensacion = Column(Float, nullable=False)
    provision_cesantias = Column(Float, nullable=False)
    provision_intereses_cesantias = Column(Float, nullable=False)
    provision_prima = Column(Float, nullable=False)
    provision_vacaciones = Column(Float, nullable=False)
    costo_total_empleador = Column(Float, nullable=False)


class costo_producto(Base):
    """Costo real de producción por producto, usado como base para COGS."""

    __tablename__ = "costo_producto"

    id_costo = Column(Integer, primary_key=True, index=True)
    id_producto = Column(Integer, ForeignKey("productos.id_producto"), index=True)
    costo_unitario = Column(Float, nullable=False)
    fecha_actualizacion = Column(Date, nullable=False)


class cierre_contable(Base):
    """Registro contable consolidado de cada cierre de caja."""

    __tablename__ = "cierre_contable"

    id_cierre = Column(Integer, primary_key=True, index=True)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), index=True)
    id_informe = Column(Integer, ForeignKey("informes.id_informe"), nullable=True)
    fecha = Column(Date, nullable=False)
    ingresos_totales = Column(Float, nullable=False)
    costo_ventas = Column(Float, nullable=False)
    utilidad_bruta = Column(Float, nullable=False)
    gastos_del_dia = Column(Float, nullable=False)
    utilidad_operacional = Column(Float, nullable=False)
    margen_bruto_pct = Column(Float, nullable=False)
    observaciones = Column(String, nullable=True)


class consolidaciones_contables(Base):
    """
    Consolidación contable diaria de una caja ya cerrada.

    Guarda el desglose de ventas brutas/netas, la separación de
    Impoconsumo/IVA, las propinas registradas y el costo de ventas,
    para el módulo de Operatividad Contable. Solo puede existir (o
    procesarse) para una caja cuyo estado sea CERRADA/COMPLETADA.
    """

    __tablename__ = "consolidaciones_contables"

    id_consolidacion = Column(Integer, primary_key=True, index=True)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), unique=True, index=True, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True, nullable=True)
    fecha_procesamiento = Column(DateTime, nullable=False, default=datetime.datetime.now)

    venta_bruta = Column(Float, nullable=False, default=0)
    impoconsumo = Column(Float, nullable=False, default=0)
    iva = Column(Float, nullable=False, default=0)
    venta_neta = Column(Float, nullable=False, default=0)
    propinas = Column(Float, nullable=False, default=0)
    costo_ventas = Column(Float, nullable=False, default=0)
    utilidad_bruta = Column(Float, nullable=False, default=0)
    observaciones = Column(String, nullable=True)


class Orden(Base):
    """
    Orden/venta consolidada de un turno de caja, usada por el cierre de
    caja para calcular ventas totales, impuestos y desglose por medio de
    pago. Es un modelo complementario a `ventas`, pensado para el flujo
    de `procesar_cierre_caja` (ver services/cierre_caja_service.py).
    """

    __tablename__ = "ordenes"

    id_orden = Column(Integer, primary_key=True, index=True)
    fecha_hora = Column(DateTime, nullable=False, default=datetime.datetime.now)
    estado = Column(String, nullable=False, default="PAGADA")  # PAGADA, ANULADA, PENDIENTE
    subtotal = Column(Float, nullable=False, default=0)
    iva = Column(Float, nullable=False, default=0)
    impuesto_consumo = Column(Float, nullable=False, default=0)
    total = Column(Float, nullable=False, default=0)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), index=True, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), index=True, nullable=True)

    pagos = relationship("Pago", back_populates="orden")


class Pago(Base):
    """
    Pago asociado a una `Orden`. El campo `medio_pago` identifica el
    canal (EFECTIVO, TARJETA, TRANSFERENCIA, APP_DELIVERY) usado para
    desglosar las ventas totales del turno en `procesar_cierre_caja`.
    """

    __tablename__ = "pagos"

    id_pago = Column(Integer, primary_key=True, index=True)
    medio_pago = Column(String, nullable=False)
    monto = Column(Float, nullable=False, default=0)
    fecha_hora = Column(DateTime, nullable=False, default=datetime.datetime.now)
    id_orden = Column(Integer, ForeignKey("ordenes.id_orden"), index=True, nullable=False)

    orden = relationship("Orden", back_populates="pagos")


class AsientoContableDiario(Base):
    """
    Asiento contable generado al cerrar una caja: desglosa ventas
    totales, impuestos (IVA / impuesto al consumo) y egresos/gastos de
    caja chica del turno, junto con el resultado del arqueo (sobrante o
    faltante) frente al saldo teórico del sistema.
    """

    __tablename__ = "asientos_contables_diarios"

    id_asiento = Column(Integer, primary_key=True, index=True)
    id_caja = Column(Integer, ForeignKey("caja.id_caja"), unique=True, index=True, nullable=False)
    fecha = Column(DateTime, nullable=False, default=datetime.datetime.now)

    ventas_totales = Column(Float, nullable=False, default=0)
    iva_total = Column(Float, nullable=False, default=0)
    impuesto_consumo_total = Column(Float, nullable=False, default=0)
    egresos_caja_chica = Column(Float, nullable=False, default=0)

    saldo_teorico = Column(Float, nullable=False, default=0)
    saldo_fisico_contado = Column(Float, nullable=False, default=0)
    diferencia = Column(Float, nullable=False, default=0)  # positivo = sobrante, negativo = faltante

    base_caja_siguiente_turno = Column(Float, nullable=False, default=0)
    efectivo_a_consignar = Column(Float, nullable=False, default=0)

    detalle_json = Column(String, nullable=True)  # desglose por medio de pago serializado


class inventario(Base):
    __tablename__ = "inventario"

    id_inventario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    categoria = Column(String, nullable=False)
    unidad_medida = Column(String, nullable=False)
    cantidad = Column(Float, nullable=False, default=0)
    stock_minimo = Column(Float, nullable=False, default=0)
    costo_unitario = Column(Float, nullable=False, default=0)
    estado = Column(String, nullable=False, default="ACTIVO")
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.datetime.now)
    fecha_actualizacion = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)


class Transaction(Base):
    """Movimiento financiero usado por el motor de P&L y flujo de caja."""

    __tablename__ = "transacciones_financieras"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)  # ingreso, gasto_fijo, gasto_variable, gasto_financiero
    monto = Column(Float, nullable=False)
    fecha = Column(DateTime, nullable=False, default=datetime.datetime.now)
    categoria = Column(String, nullable=False)
    centro_de_costo_id = Column(Integer, nullable=True, index=True)
    pagado = Column(Boolean, nullable=False, default=False)


class Payroll(Base):
    """Registro de nómina y costo laboral total de un empleado."""

    __tablename__ = "nomina"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, default="Empleado")
    salario_base = Column(Float, nullable=False, default=0)
    comisiones = Column(Float, nullable=False, default=0)
    tipo_contrato = Column(String, nullable=False)
    cargas_sociales_porcentaje = Column(Float, nullable=False, default=0)
    fecha = Column(DateTime, nullable=False, default=datetime.datetime.now)
    incluido_en_calculo = Column(Boolean, nullable=False, default=True)

    def costo_total_empleado(self) -> float:
        """Salario, comisiones y cargas sociales calculadas sobre ambos."""
        remuneracion = float(self.salario_base or 0) + float(self.comisiones or 0)
        return remuneracion * (1 + float(self.cargas_sociales_porcentaje or 0) / 100)


class Debt(Base):
    """Cuota de deuda: el interés afecta P&L y el capital solo caja."""

    __tablename__ = "deudas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, default="Deuda")
    monto_total = Column(Float, nullable=False, default=0)
    tasa_interes = Column(Float, nullable=False, default=0)
    cuota_mensual = Column(Float, nullable=False, default=0)
    abono_capital = Column(Float, nullable=False, default=0)
    pago_interes = Column(Float, nullable=False, default=0)
    fecha = Column(DateTime, nullable=False, default=datetime.datetime.now)
    pagado = Column(Boolean, nullable=False, default=False)
    incluido_en_calculo = Column(Boolean, nullable=False, default=True)


class Service(Base):
    """Servicio fijo o variable asociado a la operación."""

    __tablename__ = "servicios_financieros"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    monto = Column(Float, nullable=False, default=0)
    tipo = Column(String, nullable=False, default="fijo")  # fijo o variable
    fecha = Column(DateTime, nullable=False, default=datetime.datetime.now)
    pagado = Column(Boolean, nullable=False, default=False)
    incluido_en_calculo = Column(Boolean, nullable=False, default=True)
>>>>>>> Burguerland_V_1.0
