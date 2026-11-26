import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import Usuario, estado_usuarios, rol
from services.auth_service import authenticate_user, hash_password


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.admin_role = rol(nombre="ADMIN")
        self.worker_role = rol(nombre="VENDEDOR")
        self.active_state = estado_usuarios(nombre="ACTIVO")
        self.inactive_state = estado_usuarios(nombre="INACTIVO")
        self.db.add_all(
            [
                self.admin_role,
                self.worker_role,
                self.active_state,
                self.inactive_state,
            ]
        )
        self.db.commit()
        self.db.add_all([
            Usuario(
                nombre="Administrador",
                correo="admin@burguerland.com",
                contraseña=hash_password("clave-admin"),
                id_rol=self.admin_role.id_rol,
                id_estado=self.active_state.id_estado,
            ),
            Usuario(
                nombre="Vendedor",
                correo="vendedor@burgerland.com",
                contraseña=hash_password("clave-vendedor"),
                id_rol=self.worker_role.id_rol,
                id_estado=self.active_state.id_estado,
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_admin_alias_authenticates_the_seeded_admin(self):
        usuario = authenticate_user(self.db, " Admin ", "clave-admin")

        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.correo, "admin@burguerland.com")

    def test_admin_alias_requires_the_admin_password_and_role(self):
        self.assertIsNone(authenticate_user(self.db, "Admin", "incorrecta"))
        self.assertIsNone(
            authenticate_user(self.db, "Admin", "clave-vendedor")
        )

    def test_email_login_continues_to_work(self):
        usuario = authenticate_user(
            self.db,
            " ADMIN@BURGUERLAND.COM ",
            "clave-admin",
        )

        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.correo, "admin@burguerland.com")

    def test_inactive_user_cannot_authenticate(self):
        vendedor = (
            self.db.query(Usuario)
            .filter(Usuario.correo == "vendedor@burgerland.com")
            .one()
        )
        vendedor.id_estado = self.inactive_state.id_estado
        self.db.commit()

        self.assertIsNone(
            authenticate_user(
                self.db,
                "vendedor@burgerland.com",
                "clave-vendedor",
            )
        )


if __name__ == "__main__":
    unittest.main()
