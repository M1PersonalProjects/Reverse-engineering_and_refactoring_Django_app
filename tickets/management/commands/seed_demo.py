from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tickets.models import Comment, Profile, Ticket


class Command(BaseCommand):
    help = 'Создает демонстрационные аккаунты и заявки для лабораторной работы.'

    def handle(self, *args, **options):
        users = {
            'alice': ('alice@example.local', 'user'),
            'bob': ('bob@example.local', 'user'),
            'moderator': ('moderator@example.local', 'moderator'),
            'admin': ('admin@example.local', 'admin'),
        }

        for username, (email, role) in users.items():
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})
            user.set_password('password123')
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.phone = '+7 000 000-00-00'
            profile.save()
            self.stdout.write(f'{"created" if created else "updated"}: {username} / password123 / {role}')

        alice = User.objects.get(username='alice')
        bob = User.objects.get(username='bob')
        admin = User.objects.get(username='admin')

        Ticket.objects.all().delete()
        Comment.objects.all().delete()

        t1 = Ticket.objects.create(
            owner=alice,
            title='Не открывается отчет по продажам',
            description='После обновления страницы отчет показывает пустой экран.',
            priority='high',
            status='new',
            is_private=False,
        )
        Comment.objects.create(ticket=t1, author=alice, body='Проблема воспроизводится в Chrome.')

        t2 = Ticket.objects.create(
            owner=bob,
            title='Приватная заявка: доступ к зарплатному файлу',
            description='Нужно проверить права на файл salary.xlsx. Заявка должна быть видна только владельцу и администраторам.',
            priority='high',
            status='new',
            is_private=True,
        )
        Comment.objects.create(ticket=t2, author=bob, body='Пожалуйста, не показывать эту заявку другим пользователям.')

        t3 = Ticket.objects.create(
            owner=admin,
            title='Плановая проверка резервных копий',
            description='Проверить расписание backup-задач и уведомления.',
            priority='normal',
            status='in_progress',
            is_private=False,
        )
        Comment.objects.create(ticket=t3, author=admin, body='Назначить модератору после ревью.')

        self.stdout.write(self.style.SUCCESS('Демо-данные созданы.'))
