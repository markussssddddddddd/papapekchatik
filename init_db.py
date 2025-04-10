from main import engine, Base, Product, Session, Admin

def init_db():
    Base.metadata.create_all(engine)
    session = Session()

    # Проверяем, есть ли уже данные в базе
    if session.query(Product).count() == 0:
        # Сладкие пироги
        sweet_pies = [
            Product(
                name="Яблочный пирог",
                description="Нежный пирог с яблоками и корицей",
                price=15.90,
                category="sweet",
                image_url="https://i.imgur.com/example1.jpg"
            ),
            Product(
                name="Шоколадный пирог",
                description="Шоколадный пирог с вишней",
                price=18.50,
                category="sweet",
                image_url="https://i.imgur.com/example2.jpg"
            ),
            Product(
                name="Черничный пирог",
                description="Пирог с черникой и ванильным кремом",
                price=17.20,
                category="sweet",
                image_url="https://i.imgur.com/example3.jpg"
            ),
            Product(
                name="Клубничный пирог",
                description="Пирог со свежей клубникой и заварным кремом",
                price=19.90,
                category="sweet",
                image_url="https://i.imgur.com/example4.jpg"
            ),
            Product(
                name="Лимонный пирог",
                description="Пирог с лимонной начинкой и безе",
                price=16.80,
                category="sweet",
                image_url="https://i.imgur.com/example5.jpg"
            ),
            Product(
                name="Карамельный пирог",
                description="Пирог с карамельной начинкой и орехами",
                price=20.50,
                category="sweet",
                image_url="https://i.imgur.com/example6.jpg"
            ),
            Product(
                name="Творожный пирог",
                description="Пирог с творожной начинкой и изюмом",
                price=17.90,
                category="sweet",
                image_url="https://i.imgur.com/example7.jpg"
            )
        ]

        # Сытные пироги
        savory_pies = [
            Product(
                name="Мясной пирог",
                description="Пирог с говядиной и грибами",
                price=22.90,
                category="savory",
                image_url="https://i.imgur.com/example8.jpg"
            ),
            Product(
                name="Куриный пирог",
                description="Пирог с курицей и овощами",
                price=21.50,
                category="savory",
                image_url="https://i.imgur.com/example9.jpg"
            ),
            Product(
                name="Сырный пирог",
                description="Пирог с тремя видами сыра",
                price=19.90,
                category="savory",
                image_url="https://i.imgur.com/example10.jpg",
                is_special=1
            ),
            Product(
                name="Лососевый пирог",
                description="Пирог с лососем и шпинатом",
                price=25.90,
                category="savory",
                image_url="https://i.imgur.com/example11.jpg"
            ),
            Product(
                name="Овощной пирог",
                description="Пирог с сезонными овощами и зеленью",
                price=18.50,
                category="savory",
                image_url="https://i.imgur.com/example12.jpg"
            ),
            Product(
                name="Грибной пирог",
                description="Пирог с лесными грибами и луком",
                price=20.90,
                category="savory",
                image_url="https://i.imgur.com/example13.jpg"
            ),
            Product(
                name="Картофельный пирог",
                description="Пирог с картофелем и зеленым луком",
                price=16.90,
                category="savory",
                image_url="https://i.imgur.com/example14.jpg"
            )
        ]

        # Добавляем все пироги в базу данных
        session.add_all(sweet_pies + savory_pies)
        session.commit()

    session.close()

def add_admin(user_id: int, username: str):
    """Добавляет нового администратора в базу данных"""
    session = Session()
    
    # Проверяем, существует ли уже администратор с таким user_id
    existing_admin = session.query(Admin).filter_by(user_id=user_id).first()
    
    if not existing_admin:
        new_admin = Admin(
            user_id=user_id,
            username=username,
            is_active=True
        )
        session.add(new_admin)
        session.commit()
        print(f"Администратор {username} (ID: {user_id}) успешно добавлен")
    else:
        print(f"Администратор с ID {user_id} уже существует")
    
    session.close()

if __name__ == "__main__":
    init_db()
    # Здесь вы можете добавить администраторов, когда получите их ID
    # Пример: add_admin(123456789, "admin_username") 