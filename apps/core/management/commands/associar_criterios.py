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
        
        # Buscar IDs de validações que precisam de critérios
        if force:
            self.stdout.write(self.style.WARNING('⚠️  Modo --force: removendo critérios existentes...'))
            ValidacaoCriterio.objects.all().delete()
            validacao_ids = list(Validacao.objects.values_list('id', flat=True))
        else:
            # IDs de todas as validações
            todas_validacoes = set(Validacao.objects.values_list('id', flat=True))
            
            # IDs de validações que já possuem todos os critérios
            from django.db.models import Count
            validacoes_completas = set(
                ValidacaoCriterio.objects
                .values('validacao_id')
                .annotate(total=Count('validacao_id'))
                .filter(total=total_criterios)
                .values_list('validacao_id', flat=True)
            )
            
            # IDs de validações que precisam de critérios
            validacao_ids = list(todas_validacoes - validacoes_completas)
            
            if validacoes_completas:
                self.stdout.write(
                    f'✓ {len(validacoes_completas)} validações já possuem todos os critérios (pulando)'
                )
        
        total_validacoes = len(validacao_ids)
        
        if total_validacoes == 0:
            self.stdout.write(self.style.SUCCESS('✅ Todas as validações já possuem critérios!'))
            return
        
        self.stdout.write(f'👥 Validações a processar: {total_validacoes}')
        self.stdout.write(f'📊 Total de associações a criar: {total_validacoes * total_criterios:,}')
        self.stdout.write('')
        self.stdout.write('⏳ Criando associações em lote (pode levar alguns segundos)...')
        
        # Criar todos os ValidacaoCriterio em massa usando bulk_create
        validacoes_criterios = []
        batch_size = 1000  # Processar em lotes de 1000 para não sobrecarregar memória
        
        with transaction.atomic():
            for validacao_id in validacao_ids:
                for criterio in criterios:
                    validacoes_criterios.append(
                        ValidacaoCriterio(
                            validacao_id=validacao_id,
                            criterio=criterio,
                            atendido=False
                        )
                    )
                    
                    # Criar em lotes
                    if len(validacoes_criterios) >= batch_size:
                        ValidacaoCriterio.objects.bulk_create(
                            validacoes_criterios,
                            ignore_conflicts=True  # Ignorar se já existir
                        )
                        validacoes_criterios = []
                        self.stdout.write('.', ending='')
                        self.stdout.flush()
            
            # Criar o restante
            if validacoes_criterios:
                ValidacaoCriterio.objects.bulk_create(
                    validacoes_criterios,
                    ignore_conflicts=True
                )
                self.stdout.write('.', ending='')
        
        self.stdout.write('')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Associações criadas com sucesso!'))
        
        # Recalcular pontuações em massa
        self.stdout.write('🔢 Recalculando pontuações...')
        
        validacoes = Validacao.objects.filter(id__in=validacao_ids)
        for validacao in validacoes.iterator(chunk_size=100):
            validacao.atualizar_pontuacao()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'✨ Concluído! {total_validacoes:,} validações atualizadas com '
            f'{total_criterios} critérios cada.'
        ))
        self.stdout.write(self.style.NOTICE(
            f'📈 Total de critérios cadastrados: {ValidacaoCriterio.objects.count():,}'
        ))
