from django.core.management.base import BaseCommand
from apps.cecad.services.importer import CecadImporter

class Command(BaseCommand):
    help = 'Importa dados do CECAD a partir de um arquivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Caminho para o arquivo CSV')

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do arquivo: {file_path}'))

        importer = CecadImporter(file_path)
        success, message = importer.run()

        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.ERROR(f'Erro: {message}'))
