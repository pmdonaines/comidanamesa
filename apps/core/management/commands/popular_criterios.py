from django.core.management.base import BaseCommand
from apps.core.models import Categoria, Criterio


class Command(BaseCommand):
    help = 'Popula as 4 categorias e os 18 critérios de elegibilidade do programa Comida na Mesa'

    CATEGORIAS = [
        {
            'codigo': 'desenvolvimento_social',
            'nome': 'Desenvolvimento Social',
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
        # Desenvolvimento Social
        {
            'codigo': 'renda_familiar',
            'categoria_codigo': 'desenvolvimento_social',
            'descricao': 'Famílias em situação de extrema vulnerabilidade social com renda per capita de até R$ 1/4 do salário mínimo',
            'pontos': 14,
            'peso': 2.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        {
            'codigo': 'cadastro_unico',
            'categoria_codigo': 'desenvolvimento_social',
            'descricao': 'Famílias com Cadastro Único no município de Dona Inês/PB, atualizado no período de 2 anos',
            'pontos': 11,
            'peso': 1.5,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        {
            'codigo': 'cpf_regular',
            'categoria_codigo': 'desenvolvimento_social',
            'descricao': 'RF com CPF regular perante a Receita Federal',
            'pontos': 0,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        # Saúde
        {
            'codigo': 'exame_citopatologico',
            'categoria_codigo': 'saude',
            'descricao': 'Realização nos últimos 2 anos de exames citopatológico nas mulheres (25 a 59 anos)',
            'pontos': 6,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True, # Deve ser True para permitir verificação de outros membros (esposa/filha)
            'aplica_se_a_unipessoais': True,
            'idade_minima': 25,
            'idade_maxima': 59,
            'sexo_necessario': '2', # Feminino
            'parentescos_permitidos': '1,2' # RF ou Cônjuge
        },
        {
            'codigo': 'vacinacao_primeira_infancia',
            'categoria_codigo': 'saude',
            'descricao': 'Atualização da caderneta de vacinação na primeira infância (0 a 4 anos)',
            'pontos': 7,
            'peso': 1.2,
            'ativo': True,
            'aplica_se_a_sem_criancas': True, # True para deixar o filtro de idade decidir
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_minima': 0,
            'idade_maxima': 4
        },
        {
            'codigo': 'vacinacao_adolescentes',
            'categoria_codigo': 'saude',
            'descricao': 'Atualização da caderneta de vacinação de adolescentes (9 a 14 anos)',
            'pontos': 7,
            'peso': 1.2,
            'ativo': True,
            'aplica_se_a_sem_criancas': True, # True para deixar o filtro de idade decidir
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_minima': 9,
            'idade_maxima': 14
        },
        {
            'codigo': 'vacinacao_covid19',
            'categoria_codigo': 'saude',
            'descricao': 'Atualização da vacinação covid-19',
            'pontos': 5,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        # Educação
        {
            'codigo': 'eja_2026',
            'categoria_codigo': 'educacao',
            'descricao': 'Alunos matriculados na EJA no ano de 2026, 17 anos ou mais...',
            'pontos': 0,
            'peso': 1.1,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_minima': 17
        },
        {
            'codigo': 'matricula_ativa_2026',
            'categoria_codigo': 'educacao',
            'descricao': 'Matrícula ativa para o ano letivo 2026 (até os 18 anos completos)',
            'pontos': 12,
            'peso': 1.3,
            'ativo': True,
            'aplica_se_a_sem_criancas': True, # Controlado por idade_maxima
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_maxima': 18
        },
        {
            'codigo': 'frequencia_escolar',
            'categoria_codigo': 'educacao',
            'descricao': 'Frequência de 75% do total da carga horária letiva do ano (averiguações bimestrais)',
            'pontos': 13,
            'peso': 1.2,
            'ativo': True,
            'aplica_se_a_sem_criancas': True, # Controlado por idade_maxima (implícito que é para quem estuda)
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_maxima': 18 # Assumindo escolaridade regular
        },
        # Documentação
        {
            'codigo': 'cpf_responsavel_familiar',
            'categoria_codigo': 'documentacao',
            'descricao': 'CPF do responsável familiar',
            'pontos': 5,
            'peso': 1.5,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        {
            'codigo': 'cpf_certidao_filhos',
            'categoria_codigo': 'documentacao',
            'descricao': 'CPF ou Certidão de Nascimento dos filhos com idade de 0 até 18 anos',
            'pontos': 3,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True, # Controlado por idade_maxima
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_maxima': 18
        },
        {
            'codigo': 'cpf_membros_composicao',
            'categoria_codigo': 'documentacao',
            'descricao': 'CPF de todos os membros da Composição familiar (informadas no Cadastro Único)',
            'pontos': 3,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        {
            'codigo': 'quitacao_eleitoral',
            'categoria_codigo': 'documentacao',
            'descricao': 'Certidão/Comprovante de quitação eleitoral (Zona 014 – Município de Dona Inês)',
            'pontos': 3,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_minima': 18 # Idade mínima para votar
        },
        {
            'codigo': 'comprovante_residencia',
            'categoria_codigo': 'documentacao',
            'descricao': 'Comprovante de Residência atualizado',
            'pontos': 4,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        {
            'codigo': 'declaracao_educacao',
            'categoria_codigo': 'documentacao',
            'descricao': 'Declaração de comprovação de critérios na Educação',
            'pontos': 3,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,  # Controlado por idade e parentesco
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True,
            'idade_minima': 4,
            'idade_maxima': 17,  # Menores de 18 anos
            'parentescos_permitidos': '3'  # Apenas filhos
        },
        {
            'codigo': 'declaracao_saude',
            'categoria_codigo': 'documentacao',
            'descricao': 'Declaração de comprovação de critérios na Saúde',
            'pontos': 3,
            'peso': 1.0,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
        },
        {
            'codigo': 'folha_resumo_cadunico',
            'categoria_codigo': 'documentacao',
            'descricao': 'Folha Resumo do Cadastramento Único do Governo Federal',
            'pontos': 1,
            'peso': 0.5,
            'ativo': True,
            'aplica_se_a_sem_criancas': True,
            'aplica_se_a_rf_homem': True,
            'aplica_se_a_unipessoais': True
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
