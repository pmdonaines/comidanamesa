from django.core.management.base import BaseCommand
from apps.cecad.services.importer import CecadImporter
import os

class Command(BaseCommand):
    help = 'Importa dados do CECAD a partir de um arquivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Caminho para o arquivo CSV')

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {csv_file}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do arquivo: {csv_file}'))
        
        importer = CecadImporter(csv_file)
        success, message = importer.run()

        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.ERROR(f'Erro na importação: {message}'))
