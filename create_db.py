from database.database import engine, Base
from database.models import Usuario, rol, estado_usuarios, estados_productos , estados_caja , metodos_pago , estado_ventas, categorias, productos
from services.auth_service import hash_password
from database.database import SessionLocal

def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # crear roles
    roles = ["ADMIN", "VENDEDOR", "CAJERO"]
    for nombre in roles:
        if not db.query(rol).filter(rol.nombre == nombre).first():
            db.add(rol(nombre=nombre))
    db.commit()

    # estados productos
    estados = ["ACTIVO", "INACTIVO"]
    for nombre in estados:
        if not db.query(estados_productos).filter(estados_productos.nombre == nombre).first():
            db.add(estados_productos(nombre=nombre))
    db.commit()

    # crear categorías
    nombres_categorias = ["Burgers", "Hot Dogs", "Fast Food", "Bebidas Frías", "Bebidas Calientes", "Adiciones"]
    for nombre in nombres_categorias:
        if not db.query(categorias).filter(categorias.nombre == nombre).first():
            db.add(categorias(nombre=nombre))
    db.commit()

    from database.models import productos

# buscar categorías y estado activo para productos
    cat_burgers = db.query(categorias).filter(categorias.nombre == "Burgers").first()
    cat_hotdogs = db.query(categorias).filter(categorias.nombre == "Hot Dogs").first()
    cat_fastfood = db.query(categorias).filter(categorias.nombre == "Fast Food").first()
    cat_bebidas_frias = db.query(categorias).filter(categorias.nombre == "Bebidas Frías").first()
    cat_bebidas_calientes = db.query(categorias).filter(categorias.nombre == "Bebidas Calientes").first()
    cat_adiciones = db.query(categorias).filter(categorias.nombre == "Adiciones").first()

    estado_activo_producto = db.query(estados_productos).filter(estados_productos.nombre == "ACTIVO").first()

    lista_productos = [
        # --- BURGERS ---
        {"nombre": "Especial", "precio": 18000, "descripcion": "Pan, doble carne, doble queso mozzarella, tocineta, papa chips, cebolla salteada, lechuga, tomate, salsa BBQ, mayonesa y mostaza", "categoria": cat_burgers},
        {"nombre": "Super Especial", "precio": 24000, "descripcion": "Doble carne, doble queso mozzarella, tocineta, france, papa chips, cebolla salteada, lechuga, tomate y mostaza", "categoria": cat_burgers},
        {"nombre": "Callejera", "precio": 18000, "descripcion": "Pan, carne, queso mozzarella, tocineta, papas chips, cebolla salteada, lechuga, tomate salsa BBQ", "categoria": cat_burgers},
        {"nombre": "Criolla", "precio": 17500, "descripcion": "Pan, queso mozzarella, huevo frito, cebolla salteada, mayonesa, tomate, salsa de tomate", "categoria": cat_burgers},
        {"nombre": "Ranchera", "precio": 23000, "descripcion": "Pan, doble carne, queso mozzarella, chorizo de cerdo, papa chips, cebolla salteada, lechuga, tomate y salsa BBQ", "categoria": cat_burgers},
        {"nombre": "Sencilla", "precio": 13000, "descripcion": "Pan, carne, queso mozzarella, lechuga, tomate, salsa de tomate y mayonesa", "categoria": cat_burgers},
        {"nombre": "Tradicional", "precio": 15500, "descripcion": "Pan, carne, queso mozzarella, cebolla salteada, lechuga, tomate, salsa de tomate y mayonesa", "categoria": cat_burgers},
        {"nombre": "Doble", "precio": 20800, "descripcion": "Doble pan, doble queso mozzarella, cebolla salteada, lechuga, tomate, salsa de tomate y mayonesa", "categoria": cat_burgers},
        {"nombre": "Pollo", "precio": 15000, "descripcion": "Pan, pollo apanado, queso mozzarella, lechuga, tomate, salsa de tomate y mayonesa", "categoria": cat_burgers},
        {"nombre": "Hawaiana", "precio": 18000, "descripcion": "Pan, pollo apanado, queso mozzarella, trozos de piña con tocineta, lechuga, tomate, salsa de tomate y mayonesa", "categoria": cat_burgers},
        {"nombre": "Mixta", "precio": 20000, "descripcion": "Pan, carne, pollo apanado, queso mozzarella, tocineta, lechuga, tomate y mayonesa", "categoria": cat_burgers},
        {"nombre": "Mixta Especial", "precio": 23000, "descripcion": "Carne, pollo apanado, doble queso mozzarella, tocineta, papa chips, cebolla salteada, lechuga, tomate, salsa BBQ y mayonesa", "categoria": cat_burgers},
        {"nombre": "Big BBQ", "precio": 20000, "descripcion": "Pan, queso americano, cebolla frita, tocineta, papa chips, mayonesa y BBQ", "categoria": cat_burgers},
        {"nombre": "Americana", "precio": 16000, "descripcion": "Pan, queso americano, cebolla, papifritas, lechuga, tomate, mayonesa y mostaza", "categoria": cat_burgers},
        {"nombre": "Super Americana", "precio": 20000, "descripcion": "Pan, queso americano, cebolla, papifritas, lechuga, tomate, huevo frito, mayonesa y mostaza", "categoria": cat_burgers},

        # --- SANDWICHES ---
        {"nombre": "Sándwich de Pollo con Tocineta y Huevo", "precio": 18000, "descripcion": "Pan, pechuga a la plancha 200 gr, tocineta, queso mozzarella, huevo frito, lechuga, tomate, salsa de ajo", "categoria": cat_burgers},
        {"nombre": "Sándwich de Pollo", "precio": 18000, "descripcion": "Pan, pechuga a la plancha 200 gr, queso mozzarella, lechuga, tomate, salsa de ajo y mayonesa", "categoria": cat_burgers},
        {"nombre": "Mixta Añadida", "precio": 22000, "descripcion": "Pan, 200 gr de trozos de lomo salteados con cebolla, queso mozzarella y salsa de tomate", "categoria": cat_burgers},

        # --- HOT DOGS ---
        {"nombre": "Perrote", "precio": 20000, "descripcion": "Doble salchicha americana, cebolla salteada, cebolla papa chips, huevo de codorniz, papa chips, mayonesa, mostaza y salsa de tomate", "categoria": cat_hotdogs},
        {"nombre": "Americano", "precio": 12500, "descripcion": "Salchicha americana, cebolla salteada, huevo de codorniz, papa chips, mayonesa, mostaza y salsa de tomate", "categoria": cat_hotdogs},
        {"nombre": "Choriperro", "precio": 15000, "descripcion": "Salchicha de cerdo, cebolla salteada, huevo de codorniz, papa chips, mayonesa, mostaza y salsa de tomate", "categoria": cat_hotdogs},
        {"nombre": "Clásico", "precio": 13500, "descripcion": "Salchicha americana, queso americano, papifritas, cebolla, mayonesa y mostaza", "categoria": cat_hotdogs},
        {"nombre": "Callejero", "precio": 24000, "descripcion": "Trozos de carne, pollo y salchicha salteados con cebolla, papa chips, tres quesos mozzarella, mayonesa y salsa de tomate", "categoria": cat_hotdogs},
        {"nombre": "Sencillo", "precio": 10500, "descripcion": "Salchicha americana, papa chips, mostaza y salsa de tomate", "categoria": cat_hotdogs},

        # --- FAST FOOD ---
        {"nombre": "Salchipapas Especial", "precio": 30000, "descripcion": "Doble porción de papa a la francesa, salchicha americana, trozos de cerdo, trozos de pollo, queso y dos huevos de codorniz", "categoria": cat_fastfood},
        {"nombre": "Salchipapas Mix", "precio": 17000, "descripcion": "Doble porción de papa a la francesa, salchicha americana, trozos de cerdo y dos huevos de codorniz", "categoria": cat_fastfood},
        {"nombre": "Salchipapas", "precio": 13000, "descripcion": "Porción de papa a la francesa y dos huevos de codorniz", "categoria": cat_fastfood},
        {"nombre": "Cazuela de Papas", "precio": 15000, "descripcion": "Doble porción de papa criolla, queso americano, salsa de cebolla", "categoria": cat_fastfood},
        {"nombre": "Alitas BBQ", "precio": 28000, "descripcion": "10 alitas bañadas en salsa BBQ acompañadas de 150 gr de papa a la francesa", "categoria": cat_fastfood},
        {"nombre": "Chorriollas", "precio": 13500, "descripcion": "Chorizo criollo con un chorreado picado", "categoria": cat_fastfood},
        {"nombre": "Chorizo con Arepa", "precio": 7500, "descripcion": "Chorizo de cerdo y arepa de maíz", "categoria": cat_fastfood},
        {"nombre": "Chorifan", "precio": 8500, "descripcion": "Chorizo de cerdo, pan de perro", "categoria": cat_fastfood},
        {"nombre": "Anillos de Cebolla", "precio": 10000, "descripcion": "6 unidades", "categoria": cat_fastfood},
        {"nombre": "Nuggets", "precio": 12000, "descripcion": "6 unidades", "categoria": cat_fastfood},

        # --- BEBIDAS FRIAS ---
        {"nombre": "Bebida 250 ML", "precio": 2500, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Bebida 350 ML", "precio": 3000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Gaseosa PET 250 ML", "precio": 3000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Gaseosa PET 400 ML", "precio": 4000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Bebida PET 500 ML", "precio": 4000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Gaseosa 1.5 L", "precio": 6500, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Coca Cola 1.5 L", "precio": 7500, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "H2Own", "precio": 3000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Agua con Gas", "precio": 3000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Botella de Agua", "precio": 2500, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Cerveza Nacional (Poker, Águila, Andina)", "precio": 4000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Club Colombia", "precio": 4000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Cola y Pola", "precio": 4000, "descripcion": None, "categoria": cat_bebidas_frias},
        {"nombre": "Corona o Stella Artois 355 ML", "precio": 7000, "descripcion": None, "categoria": cat_bebidas_frias},

        # --- BEBIDAS CALIENTES ---
        {"nombre": "Milo", "precio": 5000, "descripcion": None, "categoria": cat_bebidas_calientes},
        {"nombre": "Capuchino", "precio": 4500, "descripcion": None, "categoria": cat_bebidas_calientes},
        {"nombre": "Capuchino Vainilla", "precio": 4500, "descripcion": None, "categoria": cat_bebidas_calientes},
        {"nombre": "Café Latte", "precio": 4500, "descripcion": None, "categoria": cat_bebidas_calientes},
        {"nombre": "Tinto", "precio": 2000, "descripcion": None, "categoria": cat_bebidas_calientes},
        {"nombre": "Aromática", "precio": 2000, "descripcion": None, "categoria": cat_bebidas_calientes},

        # --- ADICIONES ---
        {"nombre": "Papas Chips", "precio": 1500, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Huevo Frito", "precio": 3000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Tocineta", "precio": 4500, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Salchicha", "precio": 6000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Queso", "precio": 3000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Chorizo", "precio": 7000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Trozos de Carne", "precio": 8000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Trozos de Pollo", "precio": 8000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Carne de Hamburguesa", "precio": 9000, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Porción de Huevos de Codorniz", "precio": 4500, "descripcion": None, "categoria": cat_adiciones},
        {"nombre": "Porción de Papas", "precio": 5500, "descripcion": None, "categoria": cat_adiciones},
    ]

    for p in lista_productos:
        if not db.query(productos).filter(productos.nombre == p["nombre"]).first():
            nuevo_producto = productos(
                nombre=p["nombre"],
                precio=p["precio"],
                stock=100,
                descripcion=p["descripcion"],
                id_categoria=p["categoria"].id_categoria if p["categoria"] else None,
                id_estado=estado_activo_producto.id_estado_producto if estado_activo_producto else None,
                id_proveedor=None
            )
            db.add(nuevo_producto)

    db.commit()
    print(f"{len(lista_productos)} productos verificados/creados.")



    # crear estados de usuario
    estados = ["ACTIVO", "INACTIVO"]
    for nombre in estados:
        if not db.query(estado_usuarios).filter(estado_usuarios.nombre == nombre).first():
            db.add(estado_usuarios(nombre=nombre))
    db.commit()

    # estado de caja
    estados = ["ABIERTA", "CERRADA"]
    for nombre in estados:
        if not db.query(estados_caja).filter(estados_caja.nombre == nombre).first():
            db.add(estados_caja(nombre=nombre))
    db.commit()

    # metodos de pago
    metodos = ["EFECTIVO", "TARJETA", "NEQUI"]
    for nombre in metodos:
        if not db.query(metodos_pago).filter(metodos_pago.nombre == nombre).first():
            db.add(metodos_pago(nombre=nombre))
    db.commit()

    # estado ventas
    estados = ["COMPLETADA", "ANULADA"]
    for nombre in estados:
        if not db.query(estado_ventas).filter(estado_ventas.nombre == nombre).first():
            db.add(estado_ventas(nombre=nombre))
    db.commit()


    # buscar el id del rol ADMIN y el estado ACTIVO
    rol_admin = db.query(rol).filter(rol.nombre == "ADMIN").first()
    estado_activo = db.query(estado_usuarios).filter(estado_usuarios.nombre == "ACTIVO").first()

    # crear usuario admin
    if not db.query(Usuario).filter(Usuario.correo == "admin@burgerland.com").first():
        admin = Usuario(
            nombre="Administrador",
            correo="admin@burgerland.com",
            contraseña=hash_password("admin123"),
            id_rol=rol_admin.id_rol,
            id_estado=estado_activo.id_estado
        )
        db.add(admin)
        db.commit()
    
    # buscar rol vendedor y estado activo
    rol_vendedor = db.query(rol).filter(rol.nombre == "VENDEDOR").first()

# crear usuario vendedor
    if not db.query(Usuario).filter(Usuario.correo == "vendedor@burgerland.com").first():
        vendedor = Usuario(
            nombre="Vendedor1",
            correo="vendedor@burgerland.com",
            contraseña=hash_password("vendedor123"),
            id_rol=rol_vendedor.id_rol,
            id_estado=estado_activo.id_estado
        )
        db.add(vendedor)
        db.commit()

    db.close()
    print("Base de datos creada exitosamente")

if __name__ == "__main__":
    init_db()

