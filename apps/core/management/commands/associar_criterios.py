from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Validacao, Criterio, ValidacaoCriterio


class Command(BaseCommand):
    help = 'Associa todos os critérios ativos às validações existentes (operação em massa otimizada)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a recriação de todos os critérios, removendo os existentes primeiro',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.MIGRATE_HEADING('🚀 Associando critérios em massa...'))
        
        # Buscar todos os critérios ativos
        criterios = list(Criterio.objects.filter(ativo=True))
        total_criterios = len(criterios)
        
        if total_criterios == 0:
            self.stdout.write(self.style.ERROR('❌ Nenhum critério ativo encontrado!'))
            self.stdout.write(self.style.WARNING('Execute primeiro: python manage.py popular_criterios'))
            return
        
        self.stdout.write(f'📋 Critérios ativos: {total_criterios}')
        
        self.stdout.write(f'👥 Processando {Validacao.objects.count()} validações...')
        self.stdout.write('⏳ Verificando critérios aplicáveis (pode levar alguns minutos)...')
        
        from apps.core.services.criteria_logic import CriteriaAssociator
        
        total_associacoes = 0
        validacoes = Validacao.objects.select_related('familia').prefetch_related('familia__membros').all()
        
        # Processar em transação para garantir integridade
        with transaction.atomic():
            for i, validacao in enumerate(validacoes, 1):
                criados = CriteriaAssociator.associate_criteria(validacao)
                total_associacoes += criados
                
                if i % 100 == 0:
                    self.stdout.write('.', ending='')
                    self.stdout.flush()
        
        self.stdout.write('')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Processo concluído! {total_associacoes} novas associações criadas.'))
        
        # Recalcular pontuações em massa
        self.stdout.write('🔢 Recalculando pontuações...')
        
        for validacao in validacoes:
            validacao.atualizar_pontuacao()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✨ Todas as pontuações foram atualizadas.'))
        self.stdout.write(self.style.NOTICE(
            f'📈 Total de critérios cadastrados: {ValidacaoCriterio.objects.count():,}'
        ))
