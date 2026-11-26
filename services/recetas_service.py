import re
import unicodedata
from dataclasses import dataclass

from database.models import (
    categorias,
    categorias_inventario,
    categorias_proveedores,
    catalogo_proveedores,
    inventario,
    productos,
    proveedores,
    receta_producto,
)


@dataclass(frozen=True)
class IngredienteMenu:
    nombre: str
    aliases: tuple[str, ...]
    categoria: str
    unidad: str
    cantidad: int
    proveedor: str
    grupo_opcion: str | None = None
    opcion: str | None = None


PROVEEDORES_INGREDIENTES = (
    ("Proveedor de carnes y embutidos", "Carnes y embutidos"),
    ("Proveedor de frutas y verduras", "Frutas y verduras"),
    ("Proveedor de panadería", "Panadería"),
    ("Proveedor de lácteos y huevos", "Lácteos y huevos"),
    ("Proveedor de congelados", "Congelados"),
    ("Proveedor de abarrotes y salsas", "Abarrotes y salsas"),
    ("Proveedor de bebidas y snacks", "Bebidas y snacks"),
)

INGREDIENTES_MENU = (
    IngredienteMenu(
        "Pan de hamburguesa", ("pan de hamburguesa", "pan"), "Panadería",
        "unidad", 1, "Panadería",
    ),
    IngredienteMenu(
        "Pan de perro", ("pan de perro",), "Panadería",
        "unidad", 1, "Panadería",
    ),
    IngredienteMenu(
        "Arepa de maíz", ("arepa de maiz", "arepa"), "Panadería",
        "unidad", 1, "Panadería",
    ),
    IngredienteMenu(
        "Carne de la casa", ("carne de la casa", "carne de res", "carne de hamburguesa", "trocitos de carne", "carne"),
        "Carnes y embutidos", "g", 140, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Carne Koller", ("carne koller", "koller"), "Carnes y embutidos",
        "g", 140, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Pollo apanado", ("pollo apanado",), "Carnes y embutidos",
        "g", 140, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Pechuga de pollo", ("pechuga a la plancha", "pechuga de pollo", "pechuga"),
        "Carnes y embutidos", "g", 200, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Pollo", ("pollo",), "Carnes y embutidos", "g", 140,
        "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Lomo de res", ("trozos de lomo", "lomo"), "Carnes y embutidos",
        "g", 200, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Churrasco", ("churrasco",), "Carnes y embutidos",
        "g", 300, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Costillas de cerdo", ("costillas",), "Carnes y embutidos",
        "g", 400, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Alitas de pollo", ("alitas",), "Carnes y embutidos",
        "g", 300, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Carne de cerdo", ("trozos de cerdo",), "Carnes y embutidos",
        "g", 150, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Chorizo de cerdo", ("chorizo de cerdo", "chorizo criollo", "chorizo"),
        "Carnes y embutidos", "unidad", 1, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Salchicha americana", ("salchicha americana", "salchicha"),
        "Carnes y embutidos", "unidad", 1, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Tocineta", ("tocineta",), "Carnes y embutidos",
        "porción", 1, "Carnes y embutidos",
    ),
    IngredienteMenu(
        "Queso mozzarella", ("queso mozzarella", "mozzarella"),
        "Lácteos y huevos", "porción", 1, "Lácteos y huevos",
    ),
    IngredienteMenu(
        "Queso americano", ("queso americano",), "Lácteos y huevos",
        "porción", 1, "Lácteos y huevos",
    ),
    IngredienteMenu(
        "Queso", ("queso fundido", "queso"), "Lácteos y huevos",
        "porción", 1, "Lácteos y huevos",
    ),
    IngredienteMenu(
        "Huevo de codorniz", ("huevos de codorniz", "huevo de codorniz"),
        "Lácteos y huevos", "unidad", 1, "Lácteos y huevos",
    ),
    IngredienteMenu(
        "Huevo", ("huevo frito", "huevo"), "Lácteos y huevos",
        "unidad", 1, "Lácteos y huevos",
    ),
    IngredienteMenu(
        "Lechuga", ("lechuga",), "Frutas y verduras",
        "porción", 1, "Frutas y verduras",
    ),
    IngredienteMenu(
        "Tomate", ("tomate",), "Frutas y verduras",
        "porción", 1, "Frutas y verduras",
    ),
    IngredienteMenu(
        "Cebolla", ("cebolla salteada", "cebolla frita", "cebolla"),
        "Frutas y verduras", "porción", 1, "Frutas y verduras",
    ),
    IngredienteMenu(
        "Piña", ("piña",), "Frutas y verduras", "porción", 1,
        "Frutas y verduras",
    ),
    IngredienteMenu(
        "Maíz", ("maiz",), "Frutas y verduras", "g", 100,
        "Frutas y verduras",
    ),
    IngredienteMenu(
        "Papas chips", ("papas chips", "papa chips"),
        "Congelados", "g", 20, "Congelados",
    ),
    IngredienteMenu(
        "Papas a la francesa", ("papas a la francesa", "papas francesas", "papa a la francesa", "papas", "papa"),
        "Congelados", "g", 150, "Congelados",
    ),
    IngredienteMenu(
        "Papas criollas", ("papas criollas", "papa criolla"),
        "Congelados", "g", 150, "Congelados",
    ),
    IngredienteMenu(
        "Casquitos de papa", ("casquitos de papa", "casquitos"),
        "Congelados", "g", 300, "Congelados",
    ),
    IngredienteMenu(
        "Nuggets", ("nuggets",), "Congelados", "unidad", 1,
        "Congelados",
    ),
    IngredienteMenu(
        "Salsa BBQ", ("salsa bbq", "bbq"), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Salsa de tomate", ("salsa de tomate",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Mayonesa", ("mayonesa",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Mostaza", ("mostaza",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Salsa de ajo", ("salsa de ajo",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Salsa tártara", ("salsa tartara",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Salsa de piña", ("salsa de pina",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
    IngredienteMenu(
        "Pepinillos", ("pepinillos",), "Frutas y verduras",
        "porción", 1, "Frutas y verduras",
    ),
    IngredienteMenu(
        "Anillos de cebolla", ("anillos de cebolla",),
        "Congelados", "unidad", 1, "Congelados",
    ),
    IngredienteMenu(
        "Gaseosa", ("gaseosa",), "Bebidas y snacks",
        "ml", 250, "Bebidas y snacks",
    ),
    IngredienteMenu(
        "Jugo de caja", ("juguito de caja", "jugo de caja"),
        "Bebidas y snacks", "unidad", 1, "Bebidas y snacks",
    ),
    IngredienteMenu(
        "Snack infantil", ("snack",), "Bebidas y snacks",
        "unidad", 1, "Bebidas y snacks",
    ),
    IngredienteMenu(
        "Ensalada Primavera", ("ensalada primavera",),
        "Frutas y verduras", "porción", 1, "Frutas y verduras",
    ),
    IngredienteMenu(
        "Ensalada Zanahoria", ("ensalada zanahoria",),
        "Frutas y verduras", "porción", 1, "Frutas y verduras",
    ),
    IngredienteMenu(
        "Orégano", ("oregano",), "Abarrotes y salsas",
        "porción", 1, "Abarrotes y salsas",
    ),
)

CATEGORIAS_CON_RECETA = {
    "Burgers",
    "Sándwiches",
    "Hot Dogs",
    "Fast Food",
    "Mazorcadas",
    "Combos",
    "Para Compartir",
    "Menú Infantil",
    "Adiciones",
    "A la Plancha",
}

OPCIONES_PROTEINA_BURGER = (
    ("Carne de la casa", "Carne de la casa (140 g, 100 % res)", 140),
    ("Carne Koller", "Koller", 140),
    ("Pollo apanado", "Pollo apanado", 140),
)

PROTEINAS_BURGER = {
    "Carne de la casa",
    "Carne Koller",
    "Pollo apanado",
    "Pechuga de pollo",
    "Pollo",
}


def _normalizar(valor):
    normalizado = unicodedata.normalize("NFKD", (valor or "").casefold())
    return " ".join(
        "".join(
            caracter
            for caracter in normalizado
            if not unicodedata.combining(caracter)
        )
        .replace("½", "1 2")
        .replace("\u2044", "/")
        .split()
    )


def _cantidad_ingrediente(texto, inicio, fin, ingrediente):
    prefijo = texto[max(0, inicio - 32):inicio]
    sufijo = texto[fin:]
    if ingrediente.unidad == "g":
        gramos = re.search(
            r"(\d+)\s*(?:g|gr|gramos)\s*(?:(?:de|del)\s*)?$",
            prefijo,
        )
        if gramos:
            return int(gramos.group(1))

    if ingrediente.unidad == "ml":
        volumen = re.match(r"\s*de\s*(\d+)\s*ml", sufijo)
        if volumen:
            return int(volumen.group(1))
    if ingrediente.unidad == "unidad":
        unidades = re.match(r"\s*(\d+)\s*unidades?", sufijo)
        if unidades:
            return int(unidades.group(1))

    porcion_media = re.search(r"(?:1\s*/\s*2|1\s+2)\s*$", prefijo)
    if porcion_media and ingrediente.unidad == "g":
        cantidad = max(1, ingrediente.cantidad // 2)
    else:
        cantidad = ingrediente.cantidad

    multiplicador = re.search(
        r"(doble|dos|tres|cuatro|cinco|seis|[1-9]\d*)"
        r"(?:\s+porcion(?:es)?)?\s*(?:(?:de|del)\s*)?$",
        prefijo,
    )
    if not multiplicador:
        return cantidad
    valor = multiplicador.group(1)
    if valor == "doble":
        return cantidad * 2
    numeros = {
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
    }
    return cantidad * numeros.get(valor, int(valor) if valor.isdigit() else 1)


def extraer_ingredientes_descripcion(descripcion, *, excluir_opciones=False):
    texto = _normalizar(descripcion)
    candidatos = []
    for ingrediente in INGREDIENTES_MENU:
        if excluir_opciones and ingrediente.nombre in PROTEINAS_BURGER:
            continue
        for alias in ingrediente.aliases:
            alias_normalizado = _normalizar(alias)
            patron = re.compile(
                rf"(?<!\w){re.escape(alias_normalizado)}(?!\w)"
            )
            for coincidencia in patron.finditer(texto):
                candidatos.append(
                    (
                        coincidencia.start(),
                        coincidencia.end(),
                        ingrediente,
                    )
                )

    candidatos.sort(
        key=lambda item: (
            -(item[1] - item[0]),
            item[0],
        )
    )
    ocupados = []
    cantidades = {}
    for inicio, fin, ingrediente in candidatos:
        if any(inicio < ocupado_fin and fin > ocupado_inicio for ocupado_inicio, ocupado_fin in ocupados):
            continue
        ocupados.append((inicio, fin))
        cantidades[ingrediente.nombre] = (
            cantidades.get(ingrediente.nombre, 0)
            + _cantidad_ingrediente(texto, inicio, fin, ingrediente)
        )
    return [
        (ingrediente, cantidad)
        for ingrediente in INGREDIENTES_MENU
        if (cantidad := cantidades.get(ingrediente.nombre, 0))
    ]


def _asegurar_proveedores(db_session):
    proveedores_por_nombre = {}
    for nombre, categoria in PROVEEDORES_INGREDIENTES:
        proveedor = (
            db_session.query(proveedores)
            .filter(proveedores.nombre == nombre)
            .first()
        )
        if proveedor is None:
            proveedor = proveedores(
                nombre=nombre,
                que_provee=categoria,
                cuanto_cobra=0,
                estado="ACTIVO",
            )
            db_session.add(proveedor)
            db_session.flush()
        elif proveedor.estado != "ACTIVO":
            proveedor.estado = "ACTIVO"
        proveedores_por_nombre[categoria] = proveedor

        categoria_proveedor = (
            db_session.query(categorias_proveedores)
            .filter(categorias_proveedores.nombre == categoria)
            .first()
        )
        if categoria_proveedor is None:
            db_session.add(
                categorias_proveedores(nombre=categoria, estado="ACTIVO")
            )
    db_session.flush()
    return proveedores_por_nombre


def _asegurar_inventario(db_session):
    proveedores_por_nombre = _asegurar_proveedores(db_session)
    categorias_existentes = {
        categoria.nombre
        for categoria in db_session.query(categorias_inventario).all()
    }
    for ingrediente in INGREDIENTES_MENU:
        if ingrediente.categoria not in categorias_existentes:
            db_session.add(
                categorias_inventario(
                    nombre=ingrediente.categoria,
                    estado="ACTIVO",
                )
            )
            categorias_existentes.add(ingrediente.categoria)
    db_session.flush()

    inventarios_por_nombre = {}
    for item in db_session.query(inventario).all():
        clave = (_normalizar(item.nombre), item.categoria, item.unidad_medida)
        inventarios_por_nombre.setdefault(clave, item)

    for ingrediente in INGREDIENTES_MENU:
        clave = (
            _normalizar(ingrediente.nombre),
            ingrediente.categoria,
            ingrediente.unidad,
        )
        item = inventarios_por_nombre.get(clave)
        if item is None:
            proveedor = proveedores_por_nombre[ingrediente.proveedor]
            item = inventario(
                nombre=ingrediente.nombre,
                categoria=ingrediente.categoria,
                unidad_medida=ingrediente.unidad,
                cantidad=0,
                stock_minimo=0,
                costo_unitario=0,
                id_proveedor=proveedor.id_proveedor,
                estado="ACTIVO",
            )
            db_session.add(item)
            db_session.flush()
            inventarios_por_nombre[clave] = item
        elif item.id_proveedor is None:
            item.id_proveedor = proveedores_por_nombre[
                ingrediente.proveedor
            ].id_proveedor
        ingrediente_id = item.id_inventario
        if ingrediente_id is not None:
            inventarios_por_nombre[clave] = item
    db_session.flush()
    return {
        ingrediente.nombre: inventarios_por_nombre[
            (
                _normalizar(ingrediente.nombre),
                ingrediente.categoria,
                ingrediente.unidad,
            )
        ]
        for ingrediente in INGREDIENTES_MENU
    }


def _sincronizar_catalogo_proveedores_ingredientes(db_session):
    nombres_proveedores = {
        nombre for nombre, _ in PROVEEDORES_INGREDIENTES
    }
    proveedores_ingredientes = (
        db_session.query(proveedores)
        .filter(proveedores.nombre.in_(nombres_proveedores))
        .all()
    )
    proveedores_por_id = {
        proveedor.id_proveedor: proveedor
        for proveedor in proveedores_ingredientes
    }
    if not proveedores_por_id:
        return

    articulos_existentes = {}
    for proveedor_id, nombre in db_session.query(
        catalogo_proveedores.id_proveedor,
        catalogo_proveedores.nombre,
    ).filter(
        catalogo_proveedores.id_proveedor.in_(proveedores_por_id)
    ):
        articulos_existentes.setdefault(proveedor_id, set()).add(
            _normalizar(nombre)
        )

    for item in db_session.query(inventario).filter(
        inventario.id_proveedor.in_(proveedores_por_id)
    ):
        existentes = articulos_existentes.setdefault(
            item.id_proveedor, set()
        )
        nombre_normalizado = _normalizar(item.nombre)
        if nombre_normalizado in existentes:
            continue
        proveedor = proveedores_por_id[item.id_proveedor]
        db_session.add(
            catalogo_proveedores(
                id_proveedor=proveedor.id_proveedor,
                grupo=item.categoria,
                nombre=item.nombre,
                detalles=f"Unidad de inventario: {item.unidad_medida}.",
                precio_unitario=(
                    item.costo_unitario
                    if item.costo_unitario > 0
                    else None
                ),
            )
        )
        existentes.add(nombre_normalizado)


def _guardar_receta(
    db_session,
    producto_id,
    item_inventario,
    cantidad,
    grupo_opcion=None,
    opcion=None,
):
    existente = (
        db_session.query(receta_producto)
        .filter(
            receta_producto.id_producto == producto_id,
            receta_producto.id_inventario == item_inventario.id_inventario,
            receta_producto.grupo_opcion == grupo_opcion,
            receta_producto.opcion == opcion,
        )
        .first()
    )
    if existente is None:
        db_session.add(
            receta_producto(
                id_producto=producto_id,
                id_inventario=item_inventario.id_inventario,
                cantidad=cantidad,
                grupo_opcion=grupo_opcion,
                opcion=opcion,
            )
        )


def sembrar_inventario_y_recetas_menu(db_session):
    """Create editable supplier-backed ingredients and initial menu recipes."""
    inventarios_por_ingrediente = _asegurar_inventario(db_session)
    _sincronizar_catalogo_proveedores_ingredientes(db_session)
    categorias_por_id = {
        categoria.id_categoria: categoria.nombre
        for categoria in db_session.query(categorias).all()
    }
    productos_menu = (
        db_session.query(productos)
        .order_by(productos.id_producto)
        .all()
    )
    nombres_ingredientes = {
        ingrediente.nombre: ingrediente for ingrediente in INGREDIENTES_MENU
    }
    creadas = 0

    for producto in productos_menu:
        categoria_nombre = categorias_por_id.get(producto.id_categoria)
        if categoria_nombre not in CATEGORIAS_CON_RECETA:
            continue
        if db_session.query(receta_producto).filter(
            receta_producto.id_producto == producto.id_producto
        ).first():
            continue

        if categoria_nombre == "Adiciones" and not producto.descripcion:
            texto = producto.nombre
        elif categoria_nombre == "A la Plancha":
            texto = f"{producto.descripcion or ''} {producto.nombre}"
        else:
            texto = producto.descripcion or ""

        excluir_opciones = categoria_nombre == "Burgers"
        componentes = extraer_ingredientes_descripcion(
            texto,
            excluir_opciones=excluir_opciones,
        )
        if not componentes and categoria_nombre != "Burgers":
            componentes = extraer_ingredientes_descripcion(
                f"{producto.nombre} {producto.descripcion or ''}"
            )
        if categoria_nombre == "A la Plancha":
            if producto.nombre == "Mixto":
                componentes = [
                    (
                        ingrediente,
                        150
                        if ingrediente.nombre
                        in {"Churrasco", "Pechuga de pollo"}
                        else cantidad,
                    )
                    for ingrediente, cantidad in componentes
                ]
            else:
                componentes = [
                    (
                        ingrediente,
                        300
                        if ingrediente.nombre == "Pechuga de pollo"
                        else cantidad,
                    )
                    for ingrediente, cantidad in componentes
                ]

        if categoria_nombre == "Burgers":
            cantidad_proteina = (
                280
                if "doble carne" in _normalizar(producto.descripcion)
                or _normalizar(producto.nombre) == "doble"
                else 140
            )
            for nombre, opcion, cantidad in OPCIONES_PROTEINA_BURGER:
                _guardar_receta(
                    db_session,
                    producto.id_producto,
                    inventarios_por_ingrediente[nombre],
                    cantidad_proteina,
                    "proteina_burger",
                    opcion,
                )
                creadas += 1
            if _normalizar(producto.nombre).startswith("mixta"):
                ingrediente = inventarios_por_ingrediente["Pollo"]
                _guardar_receta(
                    db_session,
                    producto.id_producto,
                    ingrediente,
                    140,
                )
                creadas += 1
        elif categoria_nombre == "Menú Infantil":
            componentes = [
                (ingrediente, cantidad)
                for ingrediente, cantidad in componentes
                if ingrediente.nombre
                not in {
                    "Pan de hamburguesa",
                    "Carne de la casa",
                    "Carne Koller",
                    "Pollo apanado",
                    "Pechuga de pollo",
                    "Pollo",
                    "Nuggets",
                    "Queso",
                    "Queso americano",
                    "Queso mozzarella",
                    "Salsa de tomate",
                }
            ]
            for opcion, ingredientes in (
                (
                    "6 Nuggets",
                    (("Nuggets", 6),),
                ),
                (
                    "Hamburguesa con carne Koller",
                    (
                        ("Pan de hamburguesa", 1),
                        ("Carne Koller", 140),
                        ("Queso", 1),
                        ("Salsa de tomate", 1),
                    ),
                ),
                (
                    "Hamburguesa con pollo apanado",
                    (
                        ("Pan de hamburguesa", 1),
                        ("Pollo apanado", 140),
                        ("Queso", 1),
                        ("Salsa de tomate", 1),
                    ),
                ),
            ):
                for nombre, cantidad in ingredientes:
                    _guardar_receta(
                        db_session,
                        producto.id_producto,
                        inventarios_por_ingrediente[nombre],
                        cantidad,
                        "opcion_infantil",
                        opcion,
                    )
                    creadas += 1

        for ingrediente, cantidad in componentes:
            _guardar_receta(
                db_session,
                producto.id_producto,
                inventarios_por_ingrediente[ingrediente.nombre],
                cantidad,
            )
            creadas += 1

    db_session.commit()
    return creadas


def obtener_receta_producto(db_session, producto_id):
    return (
        db_session.query(receta_producto, inventario)
        .join(inventario, inventario.id_inventario == receta_producto.id_inventario)
        .filter(receta_producto.id_producto == producto_id)
        .order_by(
            receta_producto.grupo_opcion,
            receta_producto.opcion,
            inventario.nombre,
        )
        .all()
    )


def guardar_receta_producto(db_session, producto_id, ingredientes):
    if not db_session.get(productos, producto_id):
        raise ValueError("El producto del menú ya no existe.")
    if not ingredientes:
        raise ValueError("La receta debe tener al menos un ingrediente.")

    receta_nueva = []
    for ingrediente in ingredientes:
        try:
            inventario_id = int(ingrediente["id_inventario"])
            cantidad = int(ingrediente["cantidad"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Cada ingrediente debe tener inventario y cantidad válidos.") from error
        if cantidad <= 0:
            raise ValueError("La cantidad de cada ingrediente debe ser mayor que cero.")
        if db_session.get(inventario, inventario_id) is None:
            raise ValueError("Uno de los ingredientes ya no existe en el inventario.")
        grupo = str(ingrediente.get("grupo_opcion") or "").strip() or None
        opcion = str(ingrediente.get("opcion") or "").strip() or None
        if bool(grupo) != bool(opcion):
            raise ValueError("Las opciones de receta deben tener grupo y nombre.")
        receta_nueva.append(
            (inventario_id, cantidad, grupo, opcion)
        )

    clave_unica = [(id_item, grupo, opcion) for id_item, _, grupo, opcion in receta_nueva]
    if len(clave_unica) != len(set(clave_unica)):
        raise ValueError("La receta contiene ingredientes duplicados.")

    db_session.query(receta_producto).filter(
        receta_producto.id_producto == producto_id
    ).delete(synchronize_session=False)
    db_session.add_all(
        [
            receta_producto(
                id_producto=producto_id,
                id_inventario=id_item,
                cantidad=cantidad,
                grupo_opcion=grupo,
                opcion=opcion,
            )
            for id_item, cantidad, grupo, opcion in receta_nueva
        ]
    )
    db_session.commit()
