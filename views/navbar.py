import flet as ft

def construir_navbar(
    page,
    activo,
    mostrar_inicio,
    mostrar_venta,
    mostrar_historial,
    mostrar_menu,
    mostrar_inventario,
    mostrar_proveedores,
    mostrar_informes,
    mostrar_contabilidad=None,
    contabilidad_habilitada=True,
):

    def boton_nav(texto, clave, accion, deshabilitado=False, tooltip=None):
        es_activo = activo == clave
        return ft.Button(
            content=ft.Text(texto, color="white" if not deshabilitado else "#6B7080", weight="bold" if es_activo else "normal"),
            bgcolor="transparent",
            style=ft.ButtonStyle(
                side=ft.BorderSide(2, "white") if es_activo else ft.BorderSide(0, "transparent"),
                shape=ft.RoundedRectangleBorder(radius=20)
            ),
            disabled=deshabilitado,
            tooltip=tooltip,
            on_click=(lambda e: accion()) if accion else None,
        )

    return ft.Container(
        width=float("inf"),
        height=60,
        bgcolor="#3A3F52",
        border_radius=15,
        padding=ft.Padding(left=20, right=20, top=0, bottom=0),
        content=ft.Row(
            vertical_alignment="center",
            controls=[
                boton_nav("Inicio", "inicio", mostrar_inicio),
                boton_nav("Venta", "venta", mostrar_venta),
                boton_nav("Historial", "historial", mostrar_historial),
                boton_nav("Menu", "menu", mostrar_menu),
                boton_nav("Inventario", "inventario", mostrar_inventario),
                boton_nav("Proveedores", "proveedores", mostrar_proveedores),
                boton_nav("Informes", "informes", mostrar_informes),
                boton_nav(
                    "Contabilidad",
                    "contabilidad",
                    mostrar_contabilidad,
                    deshabilitado=not contabilidad_habilitada or mostrar_contabilidad is None,
                    tooltip=None if contabilidad_habilitada else "Cierra la caja del día para habilitar Operatividad Contable",
                ),
            ]
        )
    )