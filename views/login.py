import flet as ft


def login_view(page: ft.Page, on_login_success):

    campo_ancho = 300

    txt_username = ft.TextField(
        label="Usuario o correo",
        width=campo_ancho,
        height=54,
        bgcolor="#252A3A",
        border_radius=12,
        border_color="#3A3F52",
        focused_border_color="#F2C744",
        cursor_color="#F2C744",
        label_style=ft.TextStyle(color="#A7AEC2", size=14),
        text_style=ft.TextStyle(color="white", size=15),
        content_padding=ft.Padding(left=16, right=16, top=8, bottom=8),
        prefix_icon=ft.Icons.PERSON_OUTLINE,
    )

    txt_password = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        width=campo_ancho,
        height=54,
        bgcolor="#252A3A",
        border_radius=12,
        border_color="#3A3F52",
        focused_border_color="#F2C744",
        cursor_color="#F2C744",
        label_style=ft.TextStyle(color="#A7AEC2", size=14),
        text_style=ft.TextStyle(color="white", size=15),
        content_padding=ft.Padding(left=16, right=16, top=8, bottom=8),
        prefix_icon=ft.Icons.LOCK_OUTLINE,
    )

    lbl_error = ft.Text(value="", color="#FF7B7B", size=13, weight="bold")
    indicador_carga = ft.ProgressRing(width=18, height=18, stroke_width=2, color="#101420", visible=False)
    texto_boton = ft.Text("Ingresar", color="#101420", size=16, weight="bold")

    async def btn_login_click(e):
        from database.database import SessionLocal
        from services.auth_service import authenticate_user

        lbl_error.value = ""
        if not txt_username.value or not txt_password.value:
            lbl_error.value = "Por favor, llena todos los campos."
            page.update()
            return

        texto_boton.value = "Verificando..."
        indicador_carga.visible = True
        btn_login.disabled = True
        page.update()

        db = SessionLocal()
        try:
            usuario = authenticate_user(db, txt_username.value, txt_password.value)
        finally:
            db.close()

        if usuario:
            on_login_success(usuario)
        else:
            lbl_error.value = "Usuario o contraseña incorrectos."
            texto_boton.value = "Ingresar"
            indicador_carga.visible = False
            btn_login.disabled = False
            page.update()

    txt_username.on_submit = lambda e: page.run_task(btn_login_click, e)
    txt_password.on_submit = lambda e: page.run_task(btn_login_click, e)

    btn_login = ft.ElevatedButton(
        content=ft.Row(
            alignment="center",
            spacing=10,
            controls=[indicador_carga, texto_boton],
        ),
        width=campo_ancho,
        height=50,
        bgcolor="#F2C744",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            overlay_color="#00000022",
        ),
        on_click=btn_login_click,
    )

    panel_marca = ft.Container(
        expand=1,
        padding=40,
        gradient=ft.LinearGradient(
            begin=ft.alignment.Alignment(-1, -1),
            end=ft.alignment.Alignment(1, 1),
            colors=["#2E3344", "#1B1E29"],
        ),
        content=ft.Column(
            alignment="center",
            horizontal_alignment="center",
            spacing=18,
            controls=[
                ft.Container(
                    width=88,
                    height=88,
                    border_radius=44,
                    bgcolor="#F2C744",
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.LUNCH_DINING, size=46, color="#101420"),
                ),
                ft.Text("BurgerLand", size=32, weight="bold", color="white"),
                ft.Text(
                    "Sistema de gestión administrativa",
                    size=14,
                    color="#A7AEC2",
                    text_align="center",
                ),
                ft.Container(height=10),
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.POINT_OF_SALE_OUTLINED, size=16, color="#7AE582"),
                        ft.Text("Ventas y control de caja", size=12, color="#C9CEDB"),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_OUTLINED, size=16, color="#7ABAFB"),
                        ft.Text("Informes y contabilidad", size=12, color="#C9CEDB"),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=16, color="#FFB86C"),
                        ft.Text("Inventario y proveedores", size=12, color="#C9CEDB"),
                    ],
                ),
            ],
        ),
    )

    panel_formulario = ft.Container(
        expand=1,
        padding=40,
        bgcolor="#232838",
        content=ft.Column(
            alignment="center",
            horizontal_alignment="center",
            spacing=22,
            controls=[
                ft.Text("Bienvenido de nuevo", size=24, weight="bold", color="white"),
                ft.Text(
                    "Ingresa tus credenciales para continuar",
                    size=13,
                    color="#A7AEC2",
                ),
                ft.Container(height=6),
                ft.Column(spacing=16, controls=[txt_username, txt_password]),
                lbl_error,
                btn_login,
            ],
        ),
    )

    tarjeta = ft.Container(
        width=760,
        height=460,
        border_radius=24,
        bgcolor="#232838",
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        shadow=ft.BoxShadow(
            spread_radius=2,
            blur_radius=30,
            color="#00000066",
            offset=ft.Offset(0, 12),
        ),
        content=ft.Row(
            expand=True,
            spacing=0,
            controls=[panel_marca, panel_formulario],
        ),
    )

    return ft.Container(
        expand=True,
        alignment=ft.Alignment(0, 0),
        gradient=ft.LinearGradient(
            begin=ft.alignment.Alignment(-1, -1),
            end=ft.alignment.Alignment(1, 1),
            colors=["#1B1E29", "#2C2F3E"],
        ),
        content=tarjeta,
    )
