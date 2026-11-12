from sqlalchemy.orm import Session

from database.models import catalogo_proveedores, categorias_proveedores, proveedores


CATALOGO_INICIAL = (
    (
        "Postobón",
        "Bebidas",
        (
            ("Gaseosas saborizadas", "Colombiana - Vidrio", "Presentación en vidrio."),
            ("Gaseosas saborizadas", "Colombiana - PET", "Presentación en PET."),
            ("Gaseosas saborizadas", "Postobón Manzana - Vidrio", "Presentación en vidrio."),
            ("Gaseosas saborizadas", "Postobón Manzana - PET", "Presentación en PET."),
            ("Gaseosas saborizadas", "Postobón Uva - Vidrio", "Presentación en vidrio."),
            ("Gaseosas saborizadas", "Postobón Uva - PET", "Presentación en PET."),
            ("Gaseosas saborizadas", "Postobón Naranja - PET", "Presentación en PET."),
            ("Colas y limonadas internacionales", "Pepsi - Vidrio", "Presentación en vidrio."),
            ("Colas y limonadas internacionales", "7Up - Vidrio", "Presentación en vidrio."),
            ("Jugos Hit", "Hit sabor a Lulo - Vidrio", "Jugo Hit en botella de vidrio."),
            ("Jugos Hit", "Hit sabor a Mango - Vidrio", "Jugo Hit en botella de vidrio."),
            ("Jugos Hit", "Hit sabor a Mora - Vidrio", "Jugo Hit en botella de vidrio."),
            ("Jugos Hit", "Hit sabor a Frutas Tropicales - Vidrio", "Jugo Hit en botella de vidrio."),
            ("Aguas", "Agua Cristal - Vidrio", "Presentación en vidrio."),
            ("Aguas", "Agua Cristal - PET", "Presentación en PET."),
            ("Aguas", "Bretaña - Agua carbonatada", "Agua carbonatada / club soda."),
            ("Aguas", "H2Oh! - Agua saborizada", "Agua saborizada."),
            ("Bebidas energizantes", "Speed Max", "Bebida energizante."),
        ),
    ),
    (
        "Bavaria (AB InBev)",
        "Bebidas",
        (
            ("Cervezas nacionales tradicionales", "Poker - Vidrio", "Botella de vidrio."),
            ("Cervezas nacionales tradicionales", "Águila Original - Vidrio", "Botella de vidrio."),
            ("Cervezas nacionales tradicionales", "Águila Light - Vidrio", "Botella de vidrio."),
            ("Cervezas nacionales tradicionales", "Costeñita - Vidrio", "Botella de vidrio verde pequeña."),
            ("Cervezas nacionales premium", "Club Colombia Dorada", "Cerveza nacional premium."),
            ("Cervezas nacionales premium", "Club Colombia Roja", "Cerveza nacional premium."),
            ("Cervezas nacionales premium", "Club Colombia Negra", "Cerveza nacional premium."),
            ("Cervezas nacionales premium", "Redd's", "Cerveza cítrica en botella pequeña."),
            ("Cervezas importadas", "Stella Artois - Vidrio", "Botella de vidrio."),
            ("Cervezas importadas", "Corona Extra - Vidrio", "Botella de vidrio."),
            ("Cervezas importadas", "Budweiser - Lata", "Lata roja."),
            ("Refajos", "Cola & Pola - Lata", "Lata roja."),
            ("Bebidas de Malta", "Pony Malta - Vidrio", "Presentación en vidrio."),
            ("Bebidas de Malta", "Pony Malta - PET", "Presentación en PET."),
            ("Bebidas de Malta", "Pony Malta - Lata", "Presentación en lata."),
        ),
    ),
    (
        "Coca-Cola FEMSA",
        "Bebidas",
        (
            ("Gaseosas", "Coca-Cola Sabor Original - Vidrio", "Presentación en vidrio."),
            ("Gaseosas", "Coca-Cola Sabor Original - PET", "Presentación en PET."),
            ("Gaseosas", "Coca-Cola Sin Azúcar - Vidrio", "Presentación en vidrio."),
            ("Gaseosas", "Coca-Cola Sin Azúcar - PET", "Presentación en PET."),
            ("Gaseosas", "Sprite - Vidrio", "Presentación en vidrio."),
            ("Gaseosas", "Sprite - PET", "Presentación en PET."),
            ("Gaseosas", "Quatro Toronja - Vidrio", "Presentación en vidrio."),
            ("Gaseosas", "Quatro Toronja - PET", "Presentación en PET."),
            ("Tés", "Fuze Tea", "Botella con líquido oscuro y tapa verde."),
            ("Aguas", "Agua Brisa - PET", "Botella PET transparente."),
            ("Bebidas energizantes", "Monster Energy Clásica", "Presentación clásica, lata verde."),
            ("Bebidas energizantes", "Monster Energy Lo-Carb", "Presentación Lo-Carb, lata azul."),
        ),
    ),
    (
        "Quala",
        "Bebidas",
        (
            ("Bebidas de sábila", "Saviloe", "Bebida de sábila; botella transparente."),
            ("Bebidas energizantes", "Vive 100", "Bebida energizante; botella azul."),
        ),
    ),
    (
        "PepsiCo (Frito-Lay / Alimentos Margarita)",
        "Snacks y galletas",
        (
            ("Papas Margarita", "Natural (empaque azul); Pollo (rojo); Limón (verde); Onduladas (azul claro / blanco)."),
            ("De Todito", "Natural (empaque azul); BBQ (rojo); Limón (verde)."),
            ("Snacks de maíz y queso", "Doritos (rojo); Cheetos (naranja); Cheestris (palitos de queso, naranja); Choclitos (verde)."),
            ("NatuChips", "Plátano verde (empaque verde oscuro); plátano maduro (amarillento)."),
            ("Galletas Quaker", "Empaque pequeño de avena."),
        ),
    ),
    (
        "Comestibles Ricos",
        "Snacks",
        (
            ("Super Ricas", "Papas fritas sabor a pollo (empaque rojo)."),
            ("Todo Rico", "Tradicional / Natural (empaque azul); BBQ (rojo); Criollo (naranja)."),
            ("Chicharrones Super Ricas", "Empaque rojo."),
            ("Tajamiel", "Plátano maduro (empaque rojo); plátano verde (verde)."),
            ("Tostacos", "Picantes (empaque rojo); queso (amarillo)."),
        ),
    ),
    (
        "Industria Licorera de Caldas",
        "Licores",
        (
            ("Aguardiente Amarillo de Manzanares", ""),
            ("Ron Viejo de Caldas", ""),
        ),
    ),
    (
        "Fábrica de Licores de Antioquia (FLA)",
        "Licores",
        (
            ("Aguardiente Antioqueño Tradicional", "Tapa roja."),
            ("Aguardiente Antioqueño Sin Azúcar", "Tapa azul."),
        ),
    ),
    (
        "Diageo Colombia",
        "Licores",
        (
            ("Smirnoff Ice Original", ""),
            ("Smirnoff Ice Green Apple", "Manzana verde."),
        ),
    ),
    (
        "Red Bull Colombia",
        "Bebidas",
        (
            ("Red Bull Energy Drink", "Lata tradicional."),
        ),
    ),
    (
        "Central Cervecera de Colombia",
        "Bebidas",
        (
            ("Cervezas", "Heineken - Lata", "Lata verde."),
        ),
    ),
    (
        "PiSA Farmacéutica (o distribuidores de droguería)",
        "Bebidas",
        (
            ("Electrolit", "Suero hidratante."),
        ),
    ),
    (
        "Philip Morris International (Coltabaco)",
        "Cigarrillos",
        (
            ("Marlboro Rojo", "Cajetilla tradicional roja."),
            ("Marlboro Gold / Light", "Cajetilla blanca con dorado."),
            ("Marlboro Ice / Blue", "Cajetilla azul."),
            ("Marlboro Fusión / Cápsulas", "Cajetillas con detalles morados y verdes / rojos."),
            ("L&M Red / Rojo", "Cajetilla blanca con rojo."),
            ("L&M Blue / Azul", "Cajetilla blanca con azul / verde."),
        ),
    ),
    (
        "British American Tobacco (BAT)",
        "Cigarrillos",
        (
            ("Lucky Strike Menthol / Cápsulas", "Cajetilla negra con verde."),
            ("Lucky Strike Azul", "Cajetilla azul y negra."),
            ("Rothmans Azul", "Cajetilla negra con azul oscuro."),
        ),
    ),
    (
        "Mondelez International",
        "Galletas y confitería",
        (
            ("Club Social Original", "Galletas saladas; empaque azul."),
            ("Trident Canela o Fresa", "Gomas de mascar; caja roja."),
            ("Trident Menta", "Gomas de mascar; caja azul."),
            ("Trident Hierbabuena", "Gomas de mascar; caja verde."),
            ("Chiclets Adams", "Mini empaques amarillos / naranjas."),
            ("Halls Cereza / Frutos Rojos", "Empaque morado / rojo."),
            ("Halls Mentolado Fuerte", "Empaque azul."),
            ("Halls Menta / Eucalipto", "Empaque verde."),
            ("Halls surtidos en pote", "Variedades de menta, cereza, frutos rojos y mentol."),
            ("Halls en exhibidor acrílico", "Mentol / menta fuerte (azul); cereza / frutos rojos (rojo / morado); eucalipto / menta suave (verde)."),
            ("Oreo", "Galleta; empaque azul clásico."),
            ("Ritz", "Galletas saladas."),
        ),
    ),
    (
        "Productos Ramo",
        "Ponqués y pasteles",
        (
            ("Chocoramo", "Tajada de ponqué cubierta de chocolate; empaque naranja."),
            ("Gansito", "Pastelito relleno; empaque azul."),
        ),
    ),
    (
        "Grupo Nutresa (Noel / Nacional de Chocolates / La Especial)",
        "Galletas, chocolates y frutos secos",
        (
            ("Chocolatina Jet Pequeña", "Chocolatina tradicional de leche; empaque individual."),
            ("Barra Jumbo", "Barra de chocolate con maní."),
            ("Chocolatina Gol", "Barra cubierta de chocolate y arroz soplado; empaque morado."),
            ("Maní La Especial Salado", "Empaque rojo."),
            ("Maní La Especial Crocante / Tipo Moto", "Empaque café / dorado."),
            ("Galletas Tosh", "Galletas saludables; empaque verde."),
        ),
    ),
    (
        "Productos Alimenticios Gamba",
        "Ponqués y pasteles",
        (
            ("Torta Gamba / Ponqué tradicional", "Paquete transparente con etiqueta amarilla / café."),
        ),
    ),
)

CATALOGO_BEBIDAS_AGRUPADAS_ANTERIOR = {
    "Postobón": {
        "Gaseosas saborizadas",
        "Colas y limonadas internacionales",
        "Jugos Hit",
        "Aguas",
    },
    "Bavaria (AB InBev)": {
        "Cervezas nacionales tradicionales",
        "Cervezas nacionales premium",
        "Cervezas importadas",
        "Cola & Pola",
        "Pony Malta",
    },
    "Coca-Cola FEMSA": {"Gaseosas", "Tés y aguas", "Monster Energy"},
    "Central Cervecera de Colombia": {"Cerveza Heineken"},
}


def sembrar_catalogo_proveedores(db: Session) -> int:
    """Crea los proveedores y artículos iniciales sin sobrescribir datos existentes."""
    proveedores_existentes = {
        proveedor.nombre.strip().casefold(): proveedor
        for proveedor in db.query(proveedores).all()
    }
    categorias_existentes = {
        categoria.nombre.strip().casefold(): categoria
        for categoria in db.query(categorias_proveedores).all()
    }

    nuevos_articulos = 0
    for nombre_proveedor, tipo_suministro, articulos in CATALOGO_INICIAL:
        categoria = categorias_existentes.get(tipo_suministro.casefold())
        if categoria is None:
            categoria = categorias_proveedores(
                nombre=tipo_suministro,
                estado="ACTIVO",
            )
            db.add(categoria)
            categorias_existentes[tipo_suministro.casefold()] = categoria
            db.flush()

        proveedor = proveedores_existentes.get(nombre_proveedor.casefold())
        if proveedor is None:
            proveedor = proveedores(
                nombre=nombre_proveedor,
                que_provee=tipo_suministro,
                telefono=None,
                correo=None,
                cuanto_cobra=0,
                estado="ACTIVO",
            )
            db.add(proveedor)
            db.flush()
            proveedores_existentes[nombre_proveedor.casefold()] = proveedor

        articulos_existentes = {
            nombre.casefold()
            for nombre, in db.query(catalogo_proveedores.nombre)
            .filter(catalogo_proveedores.id_proveedor == proveedor.id_proveedor)
            .all()
        }
        for articulo in articulos:
            if len(articulo) == 2:
                grupo, detalles = articulo
                nombre = grupo
            else:
                grupo, nombre, detalles = articulo
            if grupo.casefold() in articulos_existentes:
                if nombre == grupo:
                    continue
            if nombre.casefold() in articulos_existentes:
                continue
            db.add(
                catalogo_proveedores(
                    id_proveedor=proveedor.id_proveedor,
                    grupo=grupo,
                    nombre=nombre,
                    detalles=detalles or None,
                )
            )
            articulos_existentes.add(nombre.casefold())
            nuevos_articulos += 1

    for nombre_proveedor, nombres_articulos in CATALOGO_BEBIDAS_AGRUPADAS_ANTERIOR.items():
        proveedor = proveedores_existentes.get(nombre_proveedor.casefold())
        if proveedor is None:
            continue
        db.query(catalogo_proveedores).filter(
            catalogo_proveedores.id_proveedor == proveedor.id_proveedor,
            catalogo_proveedores.nombre.in_(nombres_articulos),
        ).delete(synchronize_session=False)

    db.commit()
    return nuevos_articulos


def actualizar_precio_catalogo(
    db: Session, id_producto_proveedor: int, precio_unitario: float
):
    try:
        precio = float(precio_unitario)
    except (TypeError, ValueError):
        raise ValueError("El precio debe ser numérico.")
    if precio < 0:
        raise ValueError("El precio no puede ser negativo.")

    articulo = db.get(catalogo_proveedores, id_producto_proveedor)
    if articulo is None:
        raise ValueError("No se encontró el artículo del catálogo.")
    articulo.precio_unitario = precio
    db.commit()
    return articulo
