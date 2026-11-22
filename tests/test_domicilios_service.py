import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    Transaction,
    caja,
    detalle_ventas,
    estado_ventas,
    estados_caja,
    inventario,
    historial_domicilios,
    metodos_pago,
    movimiento_caja,
    productos,
    ventas,
)
from services.domicilios_service import (
    cambiar_estado_domicilio,
    listar_domicilios_activos,
)
from services.venta_service import registrar_venta


class DomiciliosServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

        caja_abierta = estados_caja(nombre="ABIERTA")
        self.db.add(caja_abierta)
        self.db.flush()
        self.caja = caja(
            fecha_apertura=datetime.datetime.now(),
            saldo_inicial=2_000_000,
            id_estado_caja=caja_abierta.id_estado_caja,
        )
        efectivo = metodos_pago(nombre="EFECTIVO")
        completada = estado_ventas(nombre="COMPLETADA")
        anulada = estado_ventas(nombre="ANULADA")
        self.db.add_all([self.caja, efectivo, completada, anulada])
        self.db.commit()
        self.metodo = efectivo
        self.estado_anulado = anulada

        self.insumo = inventario(
            nombre="Pan",
            categoria="Insumos",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=1,
            costo_unitario=500,
            estado="ACTIVO",
        )
        self.db.add(self.insumo)
        self.db.flush()
        self.producto = productos(
            nombre="Hamburguesa prueba",
            precio=12_000,
            stock=5,
            descripcion="test",
            id_categoria=1,
            id_estado=1,
            id_inventario=self.insumo.id_inventario,
        )
        self.db.add(self.producto)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def crear_domicilio(self):
        return registrar_venta(
            self.db,
            [
                {
                    "id_producto": self.producto.id_producto,
                    "nombre": self.producto.nombre,
                    "precio": self.producto.precio,
                    "cantidad": 1,
                }
            ],
            self.metodo.id_metodos_pago,
            caja_actual=self.caja,
            domicilio={
                "cliente": "Ana Pérez",
                "telefono": "3001234567",
                "direccion": "Calle 10 # 5-20",
                "barrio_referencia": "Centro",
                "valor_domicilio": 1_500,
                "domiciliario": "Carlos",
            },
        )

    def test_delivery_is_charged_and_tracks_all_status_changes(self):
        venta = self.crear_domicilio()

        self.assertEqual(venta.total, 13_500)
        self.assertEqual(venta.tipo_pedido, "DOMICILIO")
        self.assertEqual(venta.estado_domicilio, "RECIBIDO")
        self.assertEqual(len(listar_domicilios_activos(self.db)), 1)
        self.assertEqual(
            self.db.query(movimiento_caja)
            .filter_by(id_caja=self.caja.id_caja)
            .one()
            .valor,
            13_500,
        )

        for estado in ("EN_PREPARACION", "EN_CAMINO", "ENTREGADO"):
            cambiar_estado_domicilio(self.db, venta.id_venta, estado, usuario_id=7)

        self.assertEqual(venta.estado_domicilio, "ENTREGADO")
        self.assertEqual(listar_domicilios_activos(self.db), [])
        self.assertEqual(
            self.db.query(historial_domicilios)
            .filter_by(id_venta=venta.id_venta)
            .count(),
            4,
        )

    def test_cancel_delivery_refunds_and_restores_inventory_at_cancel_time(self):
        venta = self.crear_domicilio()
        fecha_venta = venta.fecha_hora
        self.assertEqual(self.insumo.cantidad, 4)

        cancelado = cambiar_estado_domicilio(
            self.db,
            venta.id_venta,
            "CANCELADO",
            usuario_id=7,
            motivo="Cliente no disponible",
        )

        self.assertEqual(cancelado.estado_domicilio, "CANCELADO")
        self.assertEqual(cancelado.id_estado_ventas, self.estado_anulado.id_estado_venta)
        self.assertEqual(self.insumo.cantidad, 5)
        reembolso = self.db.query(Transaction).filter_by(tipo="reembolso_venta").one()
        movimiento = (
            self.db.query(movimiento_caja)
            .filter(movimiento_caja.tipo == "EGRESO")
            .one()
        )
        self.assertEqual(reembolso.monto, 13_500)
        self.assertGreaterEqual(reembolso.fecha, fecha_venta)
        self.assertEqual(reembolso.fecha, movimiento.fecha)
        self.assertEqual(
            self.db.query(detalle_ventas)
            .filter_by(id_venta=venta.id_venta)
            .count(),
            1,
        )

    def test_cancellation_requires_reason_and_valid_state_transition(self):
        venta = self.crear_domicilio()

        with self.assertRaisesRegex(ValueError, "motivo"):
            cambiar_estado_domicilio(
                self.db,
                venta.id_venta,
                "CANCELADO",
            )
        with self.assertRaisesRegex(ValueError, "No se puede cambiar"):
            cambiar_estado_domicilio(
                self.db,
                venta.id_venta,
                "ENTREGADO",
            )

        self.assertEqual(venta.estado_domicilio, "RECIBIDO")
        self.assertEqual(self.db.query(Transaction).count(), 0)


if __name__ == "__main__":
    unittest.main()
