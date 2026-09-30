import datetime
import unittest
from uuid import uuid4

from database.database import SessionLocal
from database.models import (
    Usuario,
    caja,
    detalle_ventas,
    estado_usuarios,
    estados_caja,
    inventario,
    metodos_pago,
    movimiento_caja,
    productos,
    rol,
    ventas,
)
from services.venta_service import registrar_venta


class VentaServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.db.query(movimiento_caja).delete()
        self.db.query(detalle_ventas).delete()
        self.db.query(ventas).delete()
        self.db.query(caja).delete()
        self.db.query(productos).delete()
        self.db.query(inventario).delete()
        self.db.query(Usuario).delete()
        self.db.commit()

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


if __name__ == "__main__":
    unittest.main()
