import argparse
from init_db import add_admin, init_db
from main import Session, Admin

def list_admins():
    """Выводит список всех администраторов"""
    session = Session()
    admins = session.query(Admin).all()
    
    if not admins:
        print("Администраторы не найдены")
        return
    
    print("\nСписок администраторов:")
    print("-" * 50)
    print(f"{'ID':<10} {'User ID':<15} {'Username':<20} {'Status':<10}")
    print("-" * 50)
    
    for admin in admins:
        status = "Активен" if admin.is_active else "Неактивен"
        print(f"{admin.id:<10} {admin.user_id:<15} {admin.username:<20} {status:<10}")
    
    session.close()

def remove_admin(user_id: int):
    """Удаляет администратора по user_id"""
    session = Session()
    admin = session.query(Admin).filter_by(user_id=user_id).first()
    
    if not admin:
        print(f"Администратор с ID {user_id} не найден")
        return
    
    session.delete(admin)
    session.commit()
    print(f"Администратор {admin.username} (ID: {user_id}) успешно удален")
    session.close()

def toggle_admin(user_id: int):
    """Активирует/деактивирует администратора"""
    session = Session()
    admin = session.query(Admin).filter_by(user_id=user_id).first()
    
    if not admin:
        print(f"Администратор с ID {user_id} не найден")
        return
    
    admin.is_active = not admin.is_active
    status = "активирован" if admin.is_active else "деактивирован"
    session.commit()
    print(f"Администратор {admin.username} (ID: {user_id}) успешно {status}")
    session.close()

def main():
    parser = argparse.ArgumentParser(description='Управление администраторами бота')
    subparsers = parser.add_subparsers(dest='command', help='Команды')

    # Команда добавления администратора
    add_parser = subparsers.add_parser('add', help='Добавить нового администратора')
    add_parser.add_argument('user_id', type=5093023299, help='5093023299')
    add_parser.add_argument('username', type=str, help='Имя пользователя Telegram')

    # Команда удаления администратора
    remove_parser = subparsers.add_parser('remove', help='Удалить администратора')
    remove_parser.add_argument('user_id', type=int, help='ID пользователя в Telegram')

    # Команда переключения статуса администратора
    toggle_parser = subparsers.add_parser('toggle', help='Активировать/деактивировать администратора')
    toggle_parser.add_argument('user_id', type=int, help='ID пользователя в Telegram')

    # Команда просмотра списка администраторов
    list_parser = subparsers.add_parser('list', help='Показать список администраторов')

    args = parser.parse_args()

    if args.command == 'add':
        add_admin(args.user_id, args.username)
    elif args.command == 'remove':
        remove_admin(args.user_id)
    elif args.command == 'toggle':
        toggle_admin(args.user_id)
    elif args.command == 'list':
        list_admins()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 