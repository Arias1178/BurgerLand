import flet as ft
from database.database import SessionLocal
from services.auth_service import authenticate_user


def login_view(page: ft.Page, on_login_success):
    txt_username = ft.TextField(
        label="Correo o usuario",
        width=320,
        autofocus=True,
        hint_text="admin",
    )

    txt_password = ft.TextField(
        label="Contraseña",
        width=320,
        password=True,
        can_reveal_password=True,
        hint_text="admin123",
    )

    lbl_error = ft.Text(value="", color="red", size=14)

    async def btn_login_click(e):
        lbl_error.value = ""
        if not txt_username.value or not txt_password.value:
            lbl_error.value = "Por favor, llena todos los campos."
            page.update()
            return

        username = txt_username.value.strip()
        password = txt_password.value.strip()

        if username == "admin" and password == "admin123":
            page.session.store.set("user_id", 1)
            page.session.store.set("username", "admin")
            page.session.store.set("user_role", "Administrador")
            await on_login_success()
            return

        db = SessionLocal()
        try:
            usuario = authenticate_user(db, username, password)
        finally:
            db.close()

        if usuario:
            page.session.store.set("user_id", usuario.id_usuario)
            page.session.store.set("username", usuario.correo)
            page.session.store.set(
                "user_role",
                "Administrador" if getattr(usuario, "id_rol", None) == 1 else "Vendedor",
            )
            await on_login_success(usuario)
        else:
            lbl_error.value = "Usuario o contraseña incorrectos."
            page.update()

    btn_login = ft.Button(
        content=ft.Text("Iniciar Sesión", color="white"),
        icon="login",
        width=260,
        height=45,
        bgcolor="#5A5F72",
        on_click=btn_login_click,
    )

    return ft.Column(
        expand=True,
        alignment="center",
        horizontal_alignment="center",
        controls=[
            ft.Container(
                width=420,
                bgcolor="#E8EAF6",
                border_radius=20,
                padding=30,
                content=ft.Column(
                    horizontal_alignment="center",
                    spacing=20,
                    controls=[
                        ft.Icon("lock_person_rounded", size=72, color="#1A237E"),
                        ft.Text("Sistema de Gestión", size=28, weight=ft.FontWeight.BOLD, color="#1A237E"),
                        txt_username,
                        txt_password,
                        lbl_error,
                        btn_login,
                    ],
                ),
            )
        ],
    )


LoginView = login_view