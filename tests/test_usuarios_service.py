import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import Usuario, estado_usuarios, rol, ventas
from services.auth_service import verify_password
from services.usuarios_service import (
    cambiar_estado_usuario,
    cambiar_rol_usuario,
    crear_usuario,
    editar_usuario,
    eliminar_usuario,
    listar_usuarios_para_administracion,
)


class UsuariosServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.admin_role = rol(nombre="ADMIN")
        self.worker_role = rol(nombre="VENDEDOR")
        self.cashier_role = rol(nombre="CAJERO")
        self.active_state = estado_usuarios(nombre="ACTIVO")
        self.inactive_state = estado_usuarios(nombre="INACTIVO")
        self.db.add_all(
            [
                self.admin_role,
                self.worker_role,
                self.cashier_role,
                self.active_state,
                self.inactive_state,
            ]
        )
        self.db.flush()
        self.admin = self._crear_usuario("Admin", self.admin_role)
        self.worker = self._crear_usuario("Vendedor", self.worker_role)
        self.cashier = self._crear_usuario("Cajero", self.cashier_role)
        self.db.commit()

    def _crear_usuario(self, nombre, perfil):
        usuario = Usuario(
            nombre=nombre,
            correo=f"{nombre.lower()}@burgerland.test",
            contraseña="hash",
            id_rol=perfil.id_rol,
            id_estado=self.active_state.id_estado,
        )
        self.db.add(usuario)
        self.db.flush()
        return usuario

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_admin_can_promote_and_demote_other_users(self):
        cambiar_rol_usuario(
            self.db,
            self.admin.id_usuario,
            self.worker.id_usuario,
            "ADMIN",
        )
        self.assertEqual(self.db.get(Usuario, self.worker.id_usuario).id_rol, self.admin_role.id_rol)

        cambiar_rol_usuario(
            self.db,
            self.admin.id_usuario,
            self.worker.id_usuario,
            "VENDEDOR",
        )
        self.assertEqual(self.db.get(Usuario, self.worker.id_usuario).id_rol, self.worker_role.id_rol)

    def test_admin_cannot_change_own_role_or_unknown_user(self):
        with self.assertRaisesRegex(ValueError, "propio rol"):
            cambiar_rol_usuario(
                self.db,
                self.admin.id_usuario,
                self.admin.id_usuario,
                "VENDEDOR",
            )
        with self.assertRaisesRegex(ValueError, "No se encontró el usuario"):
            cambiar_rol_usuario(
                self.db,
                self.admin.id_usuario,
                self.admin.id_usuario + 100,
                "VENDEDOR",
            )

        self.assertEqual(
            self.db.get(Usuario, self.admin.id_usuario).id_rol,
            self.admin_role.id_rol,
        )

    def test_last_admin_can_demote_another_admin_when_one_remains(self):
        segundo_admin = self._crear_usuario("Admin2", self.admin_role)
        self.db.commit()

        cambiar_rol_usuario(
            self.db,
            self.admin.id_usuario,
            segundo_admin.id_usuario,
            "VENDEDOR",
        )

        self.assertEqual(
            self.db.get(Usuario, segundo_admin.id_usuario).id_rol,
            self.worker_role.id_rol,
        )

    def test_only_admins_can_list_or_change_roles_and_roles_are_limited(self):
        with self.assertRaisesRegex(ValueError, "Solo un administrador"):
            listar_usuarios_para_administracion(
                self.db,
                self.worker.id_usuario,
            )
        with self.assertRaisesRegex(ValueError, "Solo un administrador"):
            cambiar_rol_usuario(
                self.db,
                self.worker.id_usuario,
                self.cashier.id_usuario,
                "VENDEDOR",
            )
        with self.assertRaisesRegex(ValueError, "ADMIN o VENDEDOR"):
            cambiar_rol_usuario(
                self.db,
                self.admin.id_usuario,
                self.cashier.id_usuario,
                "CAJERO",
            )

    def test_admin_user_listing_returns_roles(self):
        usuarios = listar_usuarios_para_administracion(
            self.db,
            self.admin.id_usuario,
        )
        roles_por_correo = {
            usuario["correo"]: usuario["rol"] for usuario in usuarios
        }

        self.assertEqual(
            roles_por_correo["admin@burgerland.test"],
            "ADMIN",
        )
        self.assertEqual(
            roles_por_correo["vendedor@burgerland.test"],
            "VENDEDOR",
        )
        self.assertEqual(
            roles_por_correo["cajero@burgerland.test"],
            "CAJERO",
        )

    def test_admin_can_create_and_edit_user_credentials(self):
        usuario = crear_usuario(
            self.db,
            self.admin.id_usuario,
            " Nuevo Usuario ",
            "NUEVO@BURGERLAND.TEST",
            "clave-nueva",
            "VENDEDOR",
        )
        self.assertEqual(usuario.nombre, "Nuevo Usuario")
        self.assertEqual(usuario.correo, "nuevo@burgerland.test")
        self.assertEqual(usuario.id_estado, self.active_state.id_estado)
        self.assertTrue(verify_password("clave-nueva", usuario.contraseña))

        editar_usuario(
            self.db,
            self.admin.id_usuario,
            usuario.id_usuario,
            "Usuario Editado",
            "editado@burgerland.test",
            "clave-editada",
        )
        actualizado = self.db.get(Usuario, usuario.id_usuario)
        self.assertEqual(actualizado.nombre, "Usuario Editado")
        self.assertEqual(actualizado.correo, "editado@burgerland.test")
        self.assertTrue(verify_password("clave-editada", actualizado.contraseña))

    def test_admin_can_disable_enable_and_delete_other_users(self):
        cambiar_estado_usuario(
            self.db,
            self.admin.id_usuario,
            self.worker.id_usuario,
            False,
        )
        inhabilitado = self.db.get(Usuario, self.worker.id_usuario)
        self.assertEqual(inhabilitado.id_estado, self.inactive_state.id_estado)

        cambiar_estado_usuario(
            self.db,
            self.admin.id_usuario,
            self.worker.id_usuario,
            True,
        )
        self.assertEqual(
            self.db.get(Usuario, self.worker.id_usuario).id_estado,
            self.active_state.id_estado,
        )

        eliminar_usuario(self.db, self.admin.id_usuario, self.worker.id_usuario)
        self.assertIsNone(self.db.get(Usuario, self.worker.id_usuario))

    def test_admin_cannot_delete_user_with_sales_history(self):
        self.db.add(
            ventas(
                fecha_hora=datetime.datetime.now(),
                total=10000,
                id_usuario=self.worker.id_usuario,
            )
        )
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "actividad registrada"):
            eliminar_usuario(
                self.db,
                self.admin.id_usuario,
                self.worker.id_usuario,
            )
        self.assertIsNotNone(self.db.get(Usuario, self.worker.id_usuario))

    def test_admin_cannot_disable_or_delete_self(self):
        with self.assertRaisesRegex(ValueError, "propia cuenta"):
            cambiar_estado_usuario(
                self.db,
                self.admin.id_usuario,
                self.admin.id_usuario,
                False,
            )
        with self.assertRaisesRegex(ValueError, "propia cuenta"):
            eliminar_usuario(
                self.db,
                self.admin.id_usuario,
                self.admin.id_usuario,
            )
if __name__ == "__main__":
    unittest.main()
