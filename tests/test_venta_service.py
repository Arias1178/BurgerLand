import datetime
import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    Usuario,
    caja,
    detalle_ventas,
    estado_usuarios,
    estados_caja,
    inventario,
    metodos_pago,
    mesas,
    movimiento_caja,
    productos,
    rol,
    ventas,
)
from services.venta_service import registrar_venta


class VentaServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

        rol_obj = self.db.query(rol).filter(rol.nombre == "ADMIN").first()
        if not rol_obj:
            rol_obj = rol(nombre="ADMIN")
            self.db.add(rol_obj)
            self.db.commit()

        estado_obj = self.db.query(estado_usuarios).filter(estado_usuarios.nombre == "ACTIVO").first()
        if not estado_obj:
            estado_obj = estado_usuarios(nombre="ACTIVO")
            self.db.add(estado_obj)
            self.db.commit()

        self.usuario = Usuario(
            nombre="Tester",
            correo=f"tester-{uuid4().hex[:8]}@burgerland.com",
            contraseña="hash",
            id_rol=rol_obj.id_rol,
            id_estado=estado_obj.id_estado,
        )
        self.db.add(self.usuario)
        self.db.commit()

        estado_caja = self.db.query(estados_caja).filter(estados_caja.nombre == "ABIERTA").first()
        if not estado_caja:
            estado_caja = estados_caja(nombre="ABIERTA")
            self.db.add(estado_caja)
            self.db.commit()

        self.caja = caja(
            fecha_apertura=datetime.datetime.now(),
            saldo_inicial=0,
            id_estado_caja=estado_caja.id_estado_caja,
            id_usuario=self.usuario.id_usuario,
        )
        self.db.add(self.caja)
        self.db.commit()

        metodo = self.db.query(metodos_pago).filter(metodos_pago.nombre == "EFECTIVO").first()
        if not metodo:
            metodo = metodos_pago(nombre="EFECTIVO")
            self.db.add(metodo)
            self.db.commit()
        self.metodo = metodo

        insumo = inventario(
            nombre="Pan",
            categoria="Insumos",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=1,
            costo_unitario=500,
            estado="ACTIVO",
        )
        self.db.add(insumo)
        self.db.commit()
        self.insumo = insumo

        self.producto = productos(
            nombre="Hamburguesa prueba",
            precio=12000,
            stock=5,
            descripcion="test",
            id_categoria=1,
            id_estado=1,
            id_inventario=insumo.id_inventario,
        )
        self.db.add(self.producto)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_registrar_venta_descuenta_inventario_y_agrega_movimiento(self):
        carrito = [{
            "id_producto": self.producto.id_producto,
            "nombre": self.producto.nombre,
            "precio": self.producto.precio,
            "cantidad": 2,
        }]

        venta = registrar_venta(
            self.db,
            carrito,
            self.metodo.id_metodos_pago,
            usuario_actual=self.usuario,
            caja_actual=self.caja,
        )

        self.assertEqual(venta.total, 24000)
        self.assertEqual(
            self.db.query(inventario).filter(inventario.id_inventario == self.insumo.id_inventario).first().cantidad,
            3,
        )
        self.assertEqual(
            self.db.query(movimiento_caja).filter(movimiento_caja.id_caja == self.caja.id_caja).count(),
            1,
        )

    def test_registrar_venta_rechaza_stock_insuficiente_sin_modificar_inventario(self):
        carrito = [{
            "id_producto": self.producto.id_producto,
            "nombre": self.producto.nombre,
            "precio": self.producto.precio,
            "cantidad": 10,
        }]

        with self.assertRaises(ValueError):
            registrar_venta(
                self.db,
                carrito,
                self.metodo.id_metodos_pago,
                usuario_actual=self.usuario,
                caja_actual=self.caja,
            )

        inventario_actual = self.db.query(inventario).filter(inventario.id_inventario == self.insumo.id_inventario).first()
        self.assertEqual(inventario_actual.cantidad, 5)

    def test_registrar_venta_rechaza_cantidad_negativa(self):
        carrito = [{
            "id_producto": self.producto.id_producto,
            "nombre": self.producto.nombre,
            "precio": self.producto.precio,
            "cantidad": -1,
        }]

        with self.assertRaises(ValueError):
            registrar_venta(
                self.db,
                carrito,
                self.metodo.id_metodos_pago,
                usuario_actual=self.usuario,
                caja_actual=self.caja,
            )

    def test_registrar_venta_guarda_lineas_y_personalizaciones_por_precio(self):
        carrito = [
            {
                "id_producto": self.producto.id_producto,
                "nombre": self.producto.nombre,
                "precio": 13000,
                "cantidad": 1,
                "personalizacion": "carne: Koller; combo (+$7.500)",
            },
            {
                "id_producto": self.producto.id_producto,
                "nombre": self.producto.nombre,
                "precio": 14000,
                "cantidad": 1,
                "personalizacion": "carne: Pollo apanado",
            },
        ]

        venta = registrar_venta(
            self.db,
            carrito,
            self.metodo.id_metodos_pago,
            usuario_actual=self.usuario,
            caja_actual=self.caja,
        )

        detalles = (
            self.db.query(detalle_ventas)
            .filter(detalle_ventas.id_venta == venta.id_venta)
            .order_by(detalle_ventas.precio_unitario)
            .all()
        )
        self.assertEqual(venta.total, 27000)
        self.assertEqual(len(detalles), 2)
        self.assertEqual([detalle.precio_unitario for detalle in detalles], [13000, 14000])
        self.assertEqual(
            [detalle.nombre_producto for detalle in detalles],
            [self.producto.nombre, self.producto.nombre],
        )
        self.assertEqual(
            [detalle.personalizacion for detalle in detalles],
            ["carne: Koller; combo (+$7.500)", "carne: Pollo apanado"],
        )

    def test_registrar_venta_asocia_mesa_seleccionada(self):
        mesa = mesas(numero=1, estado="LIBRE")
        self.db.add(mesa)
        self.db.commit()

        venta = registrar_venta(
            self.db,
            [{
                "id_producto": self.producto.id_producto,
                "nombre": self.producto.nombre,
                "precio": self.producto.precio,
                "cantidad": 1,
            }],
            self.metodo.id_metodos_pago,
            usuario_actual=self.usuario,
            caja_actual=self.caja,
            mesa_id=mesa.id_mesa,
        )

        self.assertEqual(venta.id_mesa, mesa.id_mesa)


if __name__ == "__main__":
    unittest.main()
