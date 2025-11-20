from django.core.management.base import BaseCommand
from apps.core.models import Categoria, Criterio


class Command(BaseCommand):
    help = 'Verifica a distribuição de pontos por categoria'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== VERIFICAÇÃO DA PONTUAÇÃO ===\n'))
        
        total_geral = 0
        
        for categoria in Categoria.objects.filter(ativo=True).order_by('ordem'):
            criterios = categoria.criterios.filter(ativo=True)
            total_categoria = sum(c.pontos for c in criterios)
            total_geral += total_categoria
            
            self.stdout.write(self.style.MIGRATE_LABEL(f'{categoria.nome}:'))
            for c in criterios:
                self.stdout.write(f'  • {c.descricao[:60]}... = {c.pontos} pontos (peso: {c.peso})')
            
            # Verificar se a categoria tem 25 pontos
            if total_categoria == 25:
                self.stdout.write(self.style.SUCCESS(f'  SUBTOTAL: {total_categoria} pontos ✓\n'))
            else:
                self.stdout.write(self.style.ERROR(f'  SUBTOTAL: {total_categoria} pontos (esperado: 25) ✗\n'))
        
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.MIGRATE_HEADING(f'TOTAL GERAL: {total_geral} pontos'))
        self.stdout.write('=' * 50)
        self.stdout.write('')
        
        # Verificar se está correto
        if total_geral == 100:
            self.stdout.write(self.style.SUCCESS('✅ Pontuação total CORRETA: 100 pontos'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Pontuação total INCORRETA: {total_geral} pontos (esperado: 100)'))
        
        self.stdout.write('')
