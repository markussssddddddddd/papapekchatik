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
                image_url="https://papapek.by/ru/files/megacat/image/1000/0/1723187267.jpg"
            ),
            Product(
                name="Шоколадный пирог",
                description="Шоколадный пирог с вишней",
                price=18.50,
                category="sweet",
                image_url="https://img.iamcook.ru/2020/upl/recipes/cat/u-ca1d10cf0d9bf81ce037e90a6ca68ffe.JPG"
            ),
            Product(
                name="Черничный пирог",
                description="Пирог с черникой и ванильным кремом",
                price=17.20,
                category="sweet",
                image_url="https://cdn.lifehacker.ru/wp-content/uploads/2024/06/shutterstock_273361589_1_1719222634_e1719222675383.jpg"
            ),
            Product(
                name="Клубничный пирог",
                description="Пирог со свежей клубникой и заварным кремом",
                price=19.90,
                category="sweet",
                image_url="https://img.iamcook.ru/old/upl/recipes/zen/u-650af671451806e83b8fcad26950b672.jpg"
            ),
            Product(
                name="Лимонный пирог",
                description="Пирог с лимонной начинкой и безе",
                price=16.80,
                category="sweet",
                image_url="https://www.chefmarket.ru/blog/wp-content/uploads/2023/05/legkij-i-osvezhajushhij-limonnyj-pirog-s-merengoj-2000x1200.jpg"
            ),
            Product(
                name="Карамельный пирог",
                description="Пирог с карамельной начинкой и орехами",
                price=20.50,
                category="sweet",
                image_url="https://img1.russianfood.com/dycontent/images_upl/630/big_629840.jpg"
            ),
            Product(
                name="Творожный пирог",
                description="Пирог с творожной начинкой и изюмом",
                price=17.90,
                category="sweet",
                image_url="https://www.povarenok.ru/data/cache/2016aug/15/38/1676613_79677-710x550x.jpg"
            )
        ]

        # Сытные пироги
        savory_pies = [
            Product(
                name="Мясной пирог",
                description="Пирог с говядиной и грибами",
                price=22.90,
                category="savory",
                image_url="https://cooklikemary.ru/sites/default/files/styles/width_700/public/img_9164-2-2.jpg?itok=rV9p9Z8i"
            ),
            Product(
                name="Куриный пирог",
                description="Пирог с курицей и овощами",
                price=21.50,
                category="savory",
                image_url="https://www.patee.ru/r/x6/0b/f3/be/640m.jpg"
            ),
            Product(
                name="Сырный пирог",
                description="Пирог с тремя видами сыра",
                price=19.90,
                category="savory",
                image_url="https://vkusvill.ru/upload/resize/401903/401903_606x362x90_c.webp",
                is_special=1
            ),
            Product(
                name="Лососевый пирог",
                description="Пирог с лососем и шпинатом",
                price=25.90,
                category="savory",
                image_url="https://img1.russianfood.com/dycontent/images_upl/451/big_450634.jpg"
            ),
            Product(
                name="Овощной пирог",
                description="Пирог с сезонными овощами и зеленью",
                price=18.50,
                category="savory",
                image_url="https://img.7dach.ru/image/600/04/59/69/2015/10/02/440fa2.jpg"
            ),
            Product(
                name="Грибной пирог",
                description="Пирог с лесными грибами и луком",
                price=20.90,
                category="savory",
                image_url="https://img1.russianfood.com/dycontent/images_upl/11/big_10992.jpg"
            ),
            Product(
                name="Картофельный пирог",
                description="Пирог с картофелем и зеленым луком",
                price=16.90,
                category="savory",
                image_url="https://prostokvashino.ru/upload/resize_cache/iblock/4a9/800_800_0/4a9f1458c80718affdc8485f9f951d7d.jpg"
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