import flet as ft

def LoginView(page: ft.Page, on_login_success):
    txt_username = ft.TextField(label="Usuario", icon="person", width=300, autofocus=True)
    txt_password = ft.TextField(label="Contraseña", icon="lock", password=True, can_reveal_password=True, width=300)
    lbl_error = ft.Text(value="", color="red", weight=ft.FontWeight.BOLD)

    async def btn_login_click(e):
        lbl_error.value = ""
        if not txt_username.value or not txt_password.value:
            lbl_error.value = "Por favor, llena todos los campos."
            page.update()
            return

        # probar la interfaz
        if txt_username.value == "admin" and txt_password.value == "admin123":
            page.session.set("user_id", 1)
            page.session.set("username", "admin")
            page.session.set("user_role", "Administrador")
            await on_login_success()
        else:
            lbl_error.value = "Usuario o contraseña incorrectos."

        page.update()

    return ft.Container(
        content=ft.Column(
            horizontal_alignment="center",
            alignment="center",
            spacing=20,
            controls=[
                ft.Icon("lock_person_rounded", size=80, color="blue"),
                ft.Text("Sistema de Gestión", style=ft.TextThemeStyle.HEADLINE_SMALL, weight="bold"),
                txt_username,
                txt_password,
                lbl_error,
                ft.Button("Iniciar Sesión", icon="login", bgcolor="blue", color="white", width=300, on_click=btn_login_click)
            ]
        ),
        alignment="center",
        expand=True
    )