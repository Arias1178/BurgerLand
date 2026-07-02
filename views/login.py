import flet as ft

def login_view(page: ft.Page, on_login_success):

    txt_username = ft.TextField(
        label="Correo o usuario",
        width=280,
        bgcolor="#E8E8E8",
        border_radius=10,
        label_style=ft.TextStyle(color="black", weight="bold", size=18),
        text_style=ft.TextStyle(color="black", size=18),
        border_color="transparent",
    )

    txt_password = ft.TextField(
        label="Contraseña",
        password=True,
        width=280,
        bgcolor="#E8E8E8",
        border_radius=10,
        label_style=ft.TextStyle(color="black", weight="bold", size=18),
        text_style=ft.TextStyle(color="black", size=18),
        border_color="transparent",
    )

    lbl_error = ft.Text(value="", color="red", weight="bold")

    async def btn_login_click(e):
        from database.database import SessionLocal
        from services.auth_service import authenticate_user

        lbl_error.value = ""
        if not txt_username.value or not txt_password.value:
            lbl_error.value = "Por favor, llena todos los campos."
            page.update()
            return

        db = SessionLocal()
        usuario = authenticate_user(db, txt_username.value, txt_password.value)
        db.close()

        if usuario:
            on_login_success(usuario)
        else:
            lbl_error.value = "Usuario o contraseña incorrectos."
            page.update()

    btn_login = ft.Button(
        content=ft.Text("Ingresar", color="white", size=16, weight="bold"),
        width=200,
        height=50,
        bgcolor="#5A5F72",
        on_click=btn_login_click
    )

    return ft.Container(
        width=370,
        height=420,
        bgcolor="#8A8F9E",
        border_radius=30,
        padding=30,
        content=ft.Column(
            horizontal_alignment="center",
            alignment="center",
            spacing=20,
            controls=[
                ft.Text("Iniciar Sesion", size=28, weight="bold", color="black"),
                ft.Container(
                    bgcolor="#D0D0D0",
                    border_radius=20,
                    padding=20,
                    content=ft.Column(
                        spacing=15,
                        controls=[txt_username, txt_password]
                    )
                ),
                lbl_error,
                btn_login,
            ]
        )
    )