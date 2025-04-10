from main import engine, Base, Product, Session

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
                price=450.0,
                category="sweet",
                image_url="https://example.com/apple_pie.jpg"
            ),
            Product(
                name="Шоколадный пирог",
                description="Шоколадный пирог с вишней",
                price=550.0,
                category="sweet",
                image_url="https://example.com/chocolate_pie.jpg"
            ),
            Product(
                name="Черничный пирог",
                description="Пирог с черникой и ванильным кремом",
                price=500.0,
                category="sweet",
                image_url="https://example.com/blueberry_pie.jpg"
            )
        ]

        # Сытные пироги
        savory_pies = [
            Product(
                name="Мясной пирог",
                description="Пирог с говядиной и грибами",
                price=600.0,
                category="savory",
                image_url="https://example.com/meat_pie.jpg"
            ),
            Product(
                name="Куриный пирог",
                description="Пирог с курицей и овощами",
                price=550.0,
                category="savory",
                image_url="https://example.com/chicken_pie.jpg"
            ),
            Product(
                name="Сырный пирог",
                description="Пирог с тремя видами сыра",
                price=500.0,
                category="savory",
                image_url="https://example.com/cheese_pie.jpg",
                is_special=1  # Специальное предложение
            )
        ]

        # Добавляем все пироги в базу данных
        session.add_all(sweet_pies + savory_pies)
        session.commit()

    session.close()

if __name__ == "__main__":
    init_db() 