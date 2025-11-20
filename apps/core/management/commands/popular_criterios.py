from django.core.management.base import BaseCommand
from apps.core.models import Categoria, Criterio


class Command(BaseCommand):
    help = 'Popula as 4 categorias e os  10 critérios de elegibilidade do programa Comida na Mesa'

    CATEGORIAS = [
        {
            'codigo': 'assistencia_social',
            'nome': 'Assistência Social',
            'descricao': 'Critérios relacionados à renda e cadastros sociais',
            'ordem': 1,
            'icone': 'users',
            'ativo': True
        },
        {
            'codigo': 'saude',
            'nome': 'Saúde',
            'descricao': 'Critérios de saúde e vacinação',
            'ordem': 2,
            'icone': 'heart',
            'ativo': True
        },
        {
            'codigo': 'educacao',
            'nome': 'Educação',
            'descricao': 'Critérios de matrícula e frequência escolar',
            'ordem': 3,
            'icone': 'academic-cap',
            'ativo': True
        },
        {
            'codigo': 'documentacao',
            'nome': 'Documentação',
            'descricao': 'Validação de documentos apresentados',
            'ordem': 4,
            'icone': 'document-text',
            'ativo': True
        },
    ]

    CRITERIOS_INICIAIS = [
        # Assistência Social
        {
            'codigo': 'renda_familiar',
            'categoria_codigo': 'assistencia_social',
            'descricao': 'Famílias em extrema vulnerabilidade social com renda per capita de até R$ 218,00',
            'pontos': 15,
            'peso': 2.0,
            'ativo': True
        },
        {
            'codigo': 'cadastro_unico',
            'categoria_codigo': 'assistencia_social',
            'descricao': 'Cadastro Único do município de Dona Inês/PB atualizado nos últimos 2 anos',
            'pontos': 10,
            'peso': 1.5,
            'ativo': True
        },
        # Saúde
        {
            'codigo': 'exame_citopatologico',
            'categoria_codigo': 'saude',
            'descricao': 'Realização nos últimos 2 anos de exame citopatológico em mulheres (25–59 anos)',
            'pontos': 5,
            'peso': 1.0,
            'ativo': True
        },
        {
            'codigo': 'vacinacao_primeira_infancia',
            'categoria_codigo': 'saude',
            'descricao': 'Atualização da caderneta de vacinação na primeira infância',
            'pontos': 8,
            'peso': 1.2,
            'ativo': True
        },
        {
            'codigo': 'vacinacao_adolescentes',
            'categoria_codigo': 'saude',
            'descricao': 'Atualização da caderneta de vacinação de adolescentes',
            'pontos': 8,
            'peso': 1.2,
            'ativo': True
        },
        {
            'codigo': 'vacinacao_covid19',
            'categoria_codigo': 'saude',
            'descricao': 'Atualização da vacinação COVID‑19',
            'pontos': 5,
            'peso': 1.0,
            'ativo': True
        },
        # Educação
        {
            'codigo': 'eja_2025',
            'categoria_codigo': 'educacao',
            'descricao': 'Alunos matriculados no EJA em 2025 (≥17 anos) ou certificado de conclusão',
            'pontos': 7,
            'peso': 1.1,
            'ativo': True
        },
        {
            'codigo': 'matricula_ativa_2025',
            'categoria_codigo': 'educacao',
            'descricao': 'Matrícula ativa para o ano letivo 2025 (até 18 anos completos) ou certificado de conclusão',
            'pontos': 10,
            'peso': 1.3,
            'ativo': True
        },
        {
            'codigo': 'frequencia_escolar',
            'categoria_codigo': 'educacao',
            'descricao': 'Frequência ≥75% da carga horária do ano/série (verificações bimestrais)',
            'pontos': 8,
            'peso': 1.2,
            'ativo': True
        },
        # Documentação
        {
            'codigo': 'documentacao',
            'categoria_codigo': 'documentacao',
            'descricao': 'Documentação (apresentação e validade dos documentos)',
            'pontos': 10,
            'peso': 1.5,
            'ativo': True
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Populando Categorias e Critérios ===\n'))
        
        # Primeiro, popular as categorias
        self.stdout.write(self.style.MIGRATE_LABEL('Etapa 1: Populando categorias...'))
        categorias_criadas = 0
        categorias_atualizadas = 0
        
        for cat_data in self.CATEGORIAS:
            categoria, created = Categoria.objects.get_or_create(
                codigo=cat_data['codigo'],
                defaults=cat_data
            )
            
            if created:
                categorias_criadas += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Criada: {categoria.nome}')
                )
            else:
                # Atualizar categoria existente
                updated = False
                for field, value in cat_data.items():
                    if field != 'codigo' and getattr(categoria, field) != value:
                        setattr(categoria, field, value)
                        updated = True
                
                if updated:
                    categoria.save()
                    categorias_atualizadas += 1
                    self.stdout.write(
                        self.style.WARNING(f'  ↻ Atualizada: {categoria.nome}')
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(f'    Já existe: {categoria.nome}')
                    )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Categorias: {categorias_criadas} criadas, {categorias_atualizadas} atualizadas\n'
        ))
        
        # Segundo, popular os critérios
        self.stdout.write(self.style.MIGRATE_LABEL('Etapa 2: Populando critérios...'))
        criterios_criados = 0
        criterios_atualizados = 0
        
        for crit_data in self.CRITERIOS_INICIAIS:
            # Buscar a categoria
            categoria_codigo = crit_data.pop('categoria_codigo')
            categoria = Categoria.objects.get(codigo=categoria_codigo)
            
            # Adicionar categoria ao defaults
            crit_data_copy = crit_data.copy()
            crit_data_copy['categoria'] = categoria
            
            criterio, created = Criterio.objects.get_or_create(
                codigo=crit_data['codigo'],
                defaults=crit_data_copy
            )
            
            if created:
                criterios_criados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Criado: [{categoria.nome}] {criterio.descricao[:60]}...')
                )
            else:
                # Atualizar critério existente
                updated = False
                for field, value in crit_data.items():
                    if field != 'codigo':
                        current_value = getattr(criterio, field, None)
                        if current_value != value:
                            setattr(criterio, field, value)
                            updated = True
                
                # Atualizar categoria se mudou
                if criterio.categoria != categoria:
                    criterio.categoria = categoria
                    updated = True
                
                if updated:
                    criterio.save()
                    criterios_atualizados += 1
                    self.stdout.write(
                        self.style.WARNING(f'  ↻ Atualizado: [{categoria.nome}] {criterio.descricao[:60]}...')
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(f'    Já existe: [{categoria.nome}] {criterio.descricao[:60]}...')
                    )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Critérios: {criterios_criados} criados, {criterios_atualizados} atualizados\n'
        ))
        
        # Resumo final
        self.stdout.write(self.style.MIGRATE_HEADING('=== RESUMO ==='))
        self.stdout.write(self.style.SUCCESS(f'Total de categorias ativas: {Categoria.objects.filter(ativo=True).count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total de critérios ativos: {Criterio.objects.filter(ativo=True).count()}'))
        
        # Exibir distribuição por categoria
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL('Distribuição por categoria:'))
        for categoria in Categoria.objects.filter(ativo=True).order_by('ordem'):
            count = categoria.criterios.filter(ativo=True).count()
            self.stdout.write(f'  • {categoria.nome}: {count} critérios')
        
        self.stdout.write('')
