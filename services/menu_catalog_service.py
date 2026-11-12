import unicodedata

from database.models import categorias, detalle_ventas, estados_productos, productos


CATEGORIAS_MENU = {
    "Burgers": "Hamburguesas clásicas y premium. Carne a elección: carne de la casa de 140 g (100 % res), Koller o pollo apanado. Arepa artesanal: +$1.000.",
    "Sándwiches": "Sándwiches preparados con pechuga a la plancha o lomo, según la descripción.",
    "Hot Dogs": "Elige la opción con tocineta por $3.000 adicionales.",
    "Fast Food": "Salchipapas y otros platos rápidos.",
    "Mazorcadas": "Maíz salteado con cebolla, queso fundido, papas chips y salsa tártara.",
    "Combos": "Disponibles para burgers, sándwiches, hot dogs y mazorcadas. Se agregan al plato en la toma del pedido.",
    "Para Compartir": "Picadas para compartir.",
    "Menú Infantil": "Incluye papas a la francesa, juguito de caja y snack.",
    "Adiciones": "Porciones y extras para acompañar tu pedido.",
    "Bebidas Frías": "Bebidas frías en diferentes presentaciones.",
    "Bebidas Calientes": "Bebidas calientes.",
    "A la Plancha": "Todos los platos son de 300 g, excepto las costillas, e incluyen dos acompañamientos a elección: papas francesas, criollas o casquitos; ensalada Primavera; ensalada Zanahoria; arepa con queso.",
}


PRODUCTOS_MENU = [
    # Burgers
    ("Burgers", "Especial", 26000, "Pan, doble carne, doble queso mozzarella, tocineta, papas chips, cebolla salteada, lechuga, tomate, salsa BBQ, mayonesa y mostaza."),
    ("Burgers", "Súper Especial", 28000, "Pan, doble carne, doble queso mozzarella, tocineta, huevo frito, papas chips, cebolla salteada, lechuga, tomate, salsa BBQ, mayonesa y mostaza.", ["Super Especial"]),
    ("Burgers", "Callejera", 20000, "Pan, carne, queso mozzarella, tocineta, papas chips, cebolla salteada, lechuga, tomate, salsa BBQ, mayonesa y mostaza."),
    ("Burgers", "Criolla", 19500, "Pan, carne, queso mozzarella, huevo frito, cebolla salteada con maíz, tomate, lechuga, salsa de tomate y mayonesa."),
    ("Burgers", "Ranchera", 22000, "Pan, carne, queso mozzarella, chorizo de cerdo, cebolla salteada, tomate, lechuga, mayonesa y salsa BBQ."),
    ("Burgers", "Sencilla", 15000, "Pan, carne, cebolla, lechuga, tomate, salsa de tomate y mostaza."),
    ("Burgers", "Tradicional", 17000, "Pan, carne, queso mozzarella, cebolla salteada, lechuga, tomate, salsa de tomate, mayonesa y mostaza."),
    ("Burgers", "Doble", 23000, "Pan, doble carne, doble queso mozzarella, cebolla salteada, lechuga, tomate, salsa de tomate, mayonesa y mostaza."),
    ("Burgers", "Pollo", 17000, "Pan, pollo apanado, queso mozzarella, cebolla salteada, lechuga, tomate, salsa de tomate, mayonesa y mostaza."),
    ("Burgers", "Hawaiana", 20000, "Pan, pollo apanado, queso mozzarella, trozos de piña con tocineta, lechuga, tomate, salsa de piña y mayonesa."),
    ("Burgers", "Mixta", 23000, "Pan, carne, pollo apanado, doble queso mozzarella, cebolla salteada, lechuga, tomate, salsa de tomate, mayonesa y mostaza."),
    ("Burgers", "Mixta Especial", 26000, "Pan, carne, pollo apanado, doble queso mozzarella, tocineta, papas chips, cebolla salteada, lechuga, tomate, salsa BBQ, mayonesa y mostaza."),
    ("Burgers", "Big BBQ", 23000, "Pan, queso americano, anillos de cebolla, tocineta, lechuga, tomate, mayonesa y salsa BBQ."),
    ("Burgers", "Americana", 19000, "Pan, queso americano, cebolla, pepinillos, lechuga, tomate, salsa de tomate y mostaza."),
    ("Burgers", "Súper Americana", 23000, "Pan, queso americano, cebolla, pepinillos, tocineta, huevo frito, lechuga, tomate, salsa de tomate y mostaza.", ["Super Americana"]),
    # Sandwiches
    ("Sándwiches", "Sándwich de Pollo con Tocineta y Huevo", 24500, "Pan, pechuga a la plancha (200 g), tocineta, queso mozzarella, huevo frito, lechuga, tomate y salsa de ajo."),
    ("Sándwiches", "Sándwich de Pollo", 20000, "Pan, pechuga a la plancha (200 g), queso mozzarella, lechuga, tomate y salsa de ajo."),
    ("Sándwiches", "Sándwich Filadelfia", 27000, "Pan, 200 g de trozos de lomo salteados con cebolla, queso mozzarella, queso americano, salsa de ajo y salsa BBQ.", ["Mixta Añadida"]),
    # Hot dogs
    ("Hot Dogs", "Perrote", 22000, "Doble salchicha americana, cebolla salteada con piña en cuadros, doble queso mozzarella, huevo de codorniz, papas chips, mayonesa, mostaza y salsa de tomate."),
    ("Hot Dogs", "Americano", 15000, "Salchicha americana, cebolla salteada con piña en cuadros, queso mozzarella, huevo de codorniz, papas chips, mayonesa, mostaza y salsa de tomate."),
    ("Hot Dogs", "Choriperro", 16000, "Chorizo de cerdo, cebolla salteada con piña en cuadros, queso mozzarella, huevo de codorniz, papas chips, mayonesa, mostaza y salsa de tomate."),
    ("Hot Dogs", "Clásico", 16000, "Salchicha americana, queso americano, trozos de cebolla, pepinillos, tomate, huevo de codorniz, papas chips, mostaza y salsa de tomate."),
    ("Hot Dogs", "Callejero", 27000, "Trozos de carne, pollo y salchicha salteados con cebolla, doble queso mozzarella, 3 huevos de codorniz, papas chips, mayonesa, mostaza y salsa de tomate."),
    ("Hot Dogs", "Sencillo", 12000, "Salchicha americana, papas chips, mostaza y salsa de tomate."),
    # Fast food
    ("Fast Food", "Salchipapas Especial", 35000, "Doble porción de papas a la francesa, salchicha americana, chorizo de cerdo, trozos de carne, trozos de pollo, queso y dos huevos de codorniz."),
    ("Fast Food", "Salchipapas Mix", 20000, "Doble porción de papas a la francesa, salchicha americana, chorizo de cerdo y dos huevos de codorniz."),
    ("Fast Food", "Salchipapas", 16000, "Salchicha americana, doble porción de papas a la francesa y dos huevos de codorniz."),
    ("Fast Food", "Alitas BBQ", 28000, "300 g de alitas bañadas en salsa BBQ, acompañadas de 150 g de papas a la francesa."),
    ("Fast Food", "Choricriollas", 15000, "300 g de papas criollas con un chorizo picado.", ["Chorriollas"]),
    ("Fast Food", "Chorizo con Arepa", 8500, "Chorizo de cerdo y arepa de maíz."),
    ("Fast Food", "Choripan", 9500, "Chorizo de cerdo en pan de perro.", ["Chorifan"]),
    ("Fast Food", "Anillos de Cebolla", 10000, "8 unidades."),
    ("Fast Food", "Nuggets", 12000, "8 unidades."),
    # Mazorcadas
    ("Mazorcadas", "Pollo", 25000, "Maíz salteado con cebolla, queso fundido, papas chips y salsa tártara, con pollo."),
    ("Mazorcadas", "Carne", 28000, "Maíz salteado con cebolla, queso fundido, papas chips y salsa tártara, con carne."),
    ("Mazorcadas", "Mixta", 27000, "Maíz salteado con cebolla, queso fundido, papas chips y salsa tártara, con pollo y carne."),
    ("Mazorcadas", "Pollo y Tocineta", 27000, "Maíz salteado con cebolla, queso fundido, papas chips y salsa tártara, con pollo y tocineta."),
    ("Mazorcadas", "Mega", 33000, "Maíz salteado con cebolla, papas chips y salsa tártara, con carne, pollo, chorizo, tocineta y extra queso."),
    # Combos (selectable as upgrades in the POS)
    ("Combos", "Combo", 7500, "150 g de papas y gaseosa de 250 ml."),
    ("Combos", "Combo Agrandado", 10500, "250 g de papas y gaseosa de 350 ml."),
    # Para compartir
    ("Para Compartir", "Picada BBQ", 56000, "300 g de alitas BBQ, 400 g de costillas BBQ y 300 g de casquitos de papa."),
    ("Para Compartir", "Picada Mix", 52000, "Chorizo de cerdo, salchicha americana, 200 g de trocitos de carne, 200 g de trocitos de pechuga, 300 g de casquitos de papa y anillos de cebolla."),
    ("Para Compartir", "Picada Súper", 75000, "300 g de alitas BBQ, 400 g de costillas BBQ, chorizo de cerdo, salchicha americana, 300 g de casquitos de papa, 150 g de papas criollas y anillos de cebolla."),
    # Menu infantil
    ("Menú Infantil", "Nuggets o Hamburguesa", 21000, "Elige 6 nuggets o hamburguesa con pan, carne Koller o pollo apanado, queso y salsa de tomate. Incluye papas a la francesa, juguito de caja y snack."),
    # Additions
    ("Adiciones", "Papas Chips", 2000, None),
    ("Adiciones", "Pepinillos", 3000, None),
    ("Adiciones", "Huevo Frito", 3500, None),
    ("Adiciones", "Tocineta", 4500, None),
    ("Adiciones", "Salchicha", 6000, None),
    ("Adiciones", "Queso", 3000, None),
    ("Adiciones", "Chorizo", 7000, None),
    ("Adiciones", "Trozos de Carne o Pollo", 8000, None, ["Trozos de Carne", "Trozos de Pollo"]),
    ("Adiciones", "Carne de Hamburguesa", 9000, None),
    ("Adiciones", "Porción de Huevos de Codorniz", 5000, None),
    ("Adiciones", "Porción de Papas", 6500, None),
    # Cold drinks
    ("Bebidas Frías", "Bebidas 250 ml", 3000, None, ["Bebida 250 ML"]),
    ("Bebidas Frías", "Bebidas 350 ml", 4000, None, ["Bebida 350 ML"]),
    ("Bebidas Frías", "Gaseosa PET 250 ml", 3000, None, ["Gaseosa PET 250 ML"]),
    ("Bebidas Frías", "Gaseosa PET 400 ml", 4500, None, ["Gaseosa PET 400 ML"]),
    ("Bebidas Frías", "Gaseosa 1,5 L", 7500, None, ["Gaseosa 1.5 L"]),
    ("Bebidas Frías", "Coca-Cola 1,5 L", 8500, None, ["Coca Cola 1.5 L"]),
    ("Bebidas Frías", "H2Oh!", 4500, None, ["H2Own"]),
    ("Bebidas Frías", "Agua con Gas", 3000, None),
    ("Bebidas Frías", "Botella de Agua", 2500, None),
    # Hot drinks
    ("Bebidas Calientes", "Milo", 5500, None),
    ("Bebidas Calientes", "Capuchino", 5000, None),
    ("Bebidas Calientes", "Capuchino Vainilla", 5000, None),
    ("Bebidas Calientes", "Café Latte", 4500, None),
    ("Bebidas Calientes", "Tinto", 2500, None),
    ("Bebidas Calientes", "Aromática", 2500, None),
    # A la plancha
    ("A la Plancha", "Churrasco", 30000, "300 g. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Churrasco Gratinado", 32000, "300 g, gratinado. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Churrasco Gratinado y Encebollado", 34000, "300 g, gratinado y encebollado. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Pechuga", 27000, "300 g. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Pechuga Gratinada", 29000, "300 g, gratinada. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Pechuga Napolitana", 30000, "300 g, con queso, tomate y orégano. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Mixto", 36000, "300 g: ½ churrasco, ½ pechuga y chorizo de cerdo. Incluye dos acompañamientos a elección."),
    ("A la Plancha", "Costillas BBQ", 31000, "400 g. Incluye dos acompañamientos a elección."),
]


BEBIDAS_CERVEZA = [
    ("Poker", 4000, "Cerveza nacional tradicional, botella de vidrio."),
    ("Águila Original", 4000, "Cerveza nacional tradicional, botella de vidrio."),
    ("Águila Light", 4000, "Cerveza nacional tradicional, botella de vidrio."),
    ("Club Colombia Dorada", 4000, "Cerveza nacional premium."),
    ("Club Colombia Roja", 4000, "Cerveza nacional premium."),
    ("Club Colombia Negra", 4000, "Cerveza nacional premium."),
    ("Cola & Pola", 4000, "Refajo en lata roja."),
    ("Corona Extra", 7000, "Cerveza importada, botella de vidrio."),
    ("Stella Artois", 7000, "Cerveza importada, botella de vidrio."),
    ("Costeñita", None, "Botella de vidrio verde pequeña. Pendiente definir precio."),
    ("Redd's", None, "Cerveza cítrica en botella pequeña. Pendiente definir precio."),
    ("Budweiser", None, "Lata roja. Pendiente definir precio."),
    ("Heineken", None, "Lata verde. Pendiente definir precio."),
]


ALIASES_OBSOLETOS = {
    ("Fast Food", "Cazuela de Papas"),
    ("Fast Food", "Chorriollas"),
    ("Fast Food", "Chorifan"),
    ("Bebidas Frías", "Bebida PET 500 ML"),
    ("Bebidas Frías", "Bebida 250 ML"),
    ("Bebidas Frías", "Bebida 350 ML"),
    ("Bebidas Frías", "H2Own"),
    ("Bebidas Frías", "Cerveza Nacional (Poker, Águila, Andina)"),
    ("Bebidas Frías", "Club Colombia"),
    ("Bebidas Frías", "Cola y Pola"),
    ("Bebidas Frías", "Corona o Stella Artois 355 ML"),
    ("Adiciones", "Trozos de Pollo"),
    ("Adiciones", "Trozos de Carne"),
    ("Burgers", "Hamburguesa prueba"),
    ("Burgers", "Sándwich de Pollo"),
    ("Burgers", "Sándwich de Pollo con Tocineta y Huevo"),
    ("Burgers", "Mixta Añadida"),
    ("Bebidas Frías", "Cerveza Nacional (Poker, Águila, Andina)"),
    ("Bebidas Frías", "Club Colombia"),
    ("Bebidas Frías", "Cola y Pola"),
    ("Bebidas Frías", "Corona o Stella Artois 355 ML"),
}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return "".join(caracter for caracter in texto.casefold() if caracter.isalnum())


def sembrar_menu(db_session):
    estado_activo = db_session.query(estados_productos).filter(
        estados_productos.nombre == "ACTIVO"
    ).first()
    if not estado_activo:
        raise ValueError("No existe el estado ACTIVO para los productos del menú.")
    estado_inactivo = db_session.query(estados_productos).filter(
        estados_productos.nombre == "INACTIVO"
    ).first()
    if not estado_inactivo:
        raise ValueError("No existe el estado INACTIVO para los productos del menú.")

    categorias_por_nombre = {}
    for nombre, descripcion in CATEGORIAS_MENU.items():
        categoria = db_session.query(categorias).filter(
            categorias.nombre == nombre
        ).first()
        if categoria is None:
            categoria = categorias(nombre=nombre, descripcion=descripcion, estado="ACTIVO")
            db_session.add(categoria)
            db_session.flush()
        else:
            categoria.descripcion = descripcion
        categorias_por_nombre[nombre] = categoria

    db_session.flush()
    productos_existentes = (
        db_session.query(productos).order_by(productos.id_producto.asc()).all()
    )
    nombres_por_producto = {
        producto.id_producto: producto.nombre
        for producto in productos_existentes
    }
    for detalle in db_session.query(detalle_ventas).filter(
        detalle_ventas.nombre_producto.is_(None)
    ):
        detalle.nombre_producto = nombres_por_producto.get(detalle.id_producto)

    categorias_por_id = {
        categoria.id_categoria: nombre
        for nombre, categoria in categorias_por_nombre.items()
    }
    por_categoria_y_nombre = {}
    por_nombre = {}
    for producto in productos_existentes:
        por_categoria_y_nombre.setdefault(
            (categorias_por_id.get(producto.id_categoria, ""), _normalizar(producto.nombre)),
            producto,
        )
        por_nombre.setdefault(_normalizar(producto.nombre), producto)

    nombres_vigentes = set()
    productos_vigentes_ids = set()
    for fila in PRODUCTOS_MENU:
        categoria_nombre, nombre, precio, descripcion = fila[:4]
        alias = fila[4] if len(fila) > 4 else []
        categoria = categorias_por_nombre[categoria_nombre]
        clave = (categoria_nombre, _normalizar(nombre))
        producto = por_categoria_y_nombre.get(clave)
        if producto is None:
            producto = next(
                (por_nombre[_normalizar(nombre_alias)] for nombre_alias in alias
                 if _normalizar(nombre_alias) in por_nombre),
                None,
            )
        if producto is None:
            producto = productos(
                nombre=nombre,
                precio=precio,
                stock=0,
                descripcion=descripcion,
                id_categoria=categoria.id_categoria,
                id_estado=estado_activo.id_estado_producto,
                id_proveedor=None,
            )
            db_session.add(producto)
            db_session.flush()
            productos_existentes.append(producto)
            por_nombre[_normalizar(nombre)] = producto
        else:
            producto.nombre = nombre
            producto.precio = precio
            producto.descripcion = descripcion
            producto.id_categoria = categoria.id_categoria
            if producto.id_estado is None:
                producto.id_estado = estado_activo.id_estado_producto
        nombres_vigentes.add((categoria_nombre, _normalizar(nombre)))
        productos_vigentes_ids.add(producto.id_producto)
        por_categoria_y_nombre[clave] = producto

    categoria_bebidas = categorias_por_nombre["Bebidas Frías"]
    for nombre, precio, descripcion in BEBIDAS_CERVEZA:
        clave = ("Bebidas Frías", _normalizar(nombre))
        producto = por_categoria_y_nombre.get(clave)
        estado_producto = (
            estado_activo
            if precio is not None
            else estado_inactivo
        )
        if producto is None:
            producto = productos(
                nombre=nombre,
                precio=precio if precio is not None else 0,
                stock=0,
                descripcion=descripcion,
                id_categoria=categoria_bebidas.id_categoria,
                id_estado=estado_producto.id_estado_producto,
                id_proveedor=None,
            )
            db_session.add(producto)
            db_session.flush()
            productos_existentes.append(producto)
            por_categoria_y_nombre[clave] = producto
        else:
            producto.nombre = nombre
            producto.precio = precio if precio is not None else 0
            producto.descripcion = descripcion
            producto.id_categoria = categoria_bebidas.id_categoria
            producto.id_estado = estado_producto.id_estado_producto
        productos_vigentes_ids.add(producto.id_producto)

    claves_vigentes = {
        (categoria, _normalizar(nombre))
        for categoria, nombre, *_ in PRODUCTOS_MENU
    }
    for producto in productos_existentes:
        clave = (
            categorias_por_id.get(producto.id_categoria, ""),
            _normalizar(producto.nombre),
        )
        if clave in claves_vigentes and producto.id_producto not in productos_vigentes_ids:
            producto.id_estado = estado_inactivo.id_estado_producto

    for categoria_nombre, nombre in ALIASES_OBSOLETOS:
        categoria = categorias_por_nombre[categoria_nombre]
        for producto in productos_existentes:
            if (
                producto.id_categoria == categoria.id_categoria
                and _normalizar(producto.nombre) == _normalizar(nombre)
            ):
                producto.id_estado = estado_inactivo.id_estado_producto

    db_session.commit()
    return len(nombres_vigentes)
