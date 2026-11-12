import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import ventas
from services.historial_service import buscar_ventas_historial


class HistorialServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all(
            [
                ventas(
                    fecha_hora=datetime.datetime(2026, 11, 3, 17, 30),
                    total=100,
                    id_metodos_pagos=1,
                    id_usuario=1,
                    id_mesa=1,
                    tipo_pedido="MESA",
                ),
                ventas(
                    fecha_hora=datetime.datetime(2025, 11, 3, 19, 30),
                    total=200,
                    id_metodos_pagos=2,
                    id_usuario=2,
                ),
                ventas(
                    fecha_hora=datetime.datetime(2026, 10, 3, 21, 30),
                    total=300,
                    id_metodos_pagos=1,
                    id_usuario=1,
                    id_mesa=2,
                    tipo_pedido="MESA",
                ),
                ventas(
                    fecha_hora=datetime.datetime(2026, 11, 4, 0, 15),
                    total=400,
                    id_metodos_pagos=2,
                    id_usuario=2,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_combine_calendar_time_order_type_payment_and_user_filters(self):
        resultado = buscar_ventas_historial(
            self.db,
            dia="3",
            mes="11",
            anio="2026",
            hora_desde="17:00",
            hora_hasta="20:00",
            tipo_pedido="MESA",
            metodo_pago_id=1,
            usuario_id=1,
        )

        self.assertEqual(resultado["cantidad"], 1)
        self.assertEqual(resultado["total"], 100)
        self.assertEqual(resultado["ventas"][0].fecha_hora, datetime.datetime(2026, 11, 3, 17, 30))

    def test_filters_recalculate_total_and_paginate_in_database(self):
        resultado = buscar_ventas_historial(
            self.db,
            mes="11",
            anio="2026",
            pagina=1,
            tamano_pagina=1,
        )

        self.assertEqual(resultado["cantidad"], 2)
        self.assertEqual(resultado["total"], 500)
        self.assertEqual(resultado["paginas"], 2)
        self.assertEqual(len(resultado["ventas"]), 1)
        siguiente = buscar_ventas_historial(
            self.db,
            mes="11",
            anio="2026",
            pagina=2,
            tamano_pagina=1,
        )
        self.assertEqual(len(siguiente["ventas"]), 1)
        self.assertNotEqual(
            resultado["ventas"][0].id_venta,
            siguiente["ventas"][0].id_venta,
        )

    def test_time_filter_can_cross_midnight_and_invalid_values_are_reported(self):
        resultado = buscar_ventas_historial(
            self.db,
            hora_desde="23:00",
            hora_hasta="01:00",
        )
        self.assertEqual(resultado["cantidad"], 1)
        self.assertEqual(resultado["total"], 400)

        with self.assertRaisesRegex(ValueError, "día"):
            buscar_ventas_historial(self.db, dia="32")
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            buscar_ventas_historial(self.db, hora_desde="25:00")
        with self.assertRaisesRegex(ValueError, "mayor que cero"):
            buscar_ventas_historial(self.db, pagina=0)


if __name__ == "__main__":
    unittest.main()
