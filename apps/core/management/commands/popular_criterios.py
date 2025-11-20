from django.core.management.base import BaseCommand
from apps.core.models import Criterio


class Command(BaseCommand):
    help = 'Popula os 10 critérios de elegibilidade do programa Comida na Mesa'

    CRITERIOS_INICIAIS = [
        {
            'codigo': 'documentacao',
            'descricao': 'Documentação (apresentação e validade dos documentos)',
            'pontos': 10,
            'peso': 1.5,
            'ativo': True
        },
        {
            'codigo': 'renda_familiar',
            'descricao': 'Famílias em extrema vulnerabilidade social com renda per capita de até R$ 218,00',
            'pontos': 15,
            'peso': 2.0,
            'ativo': True
        },
        {
            'codigo': 'cadastro_unico',
            'descricao': 'Cadastro Único do município de Dona Inês/PB atualizado nos últimos 2 anos',
            'pontos': 10,
            'peso': 1.5,
            'ativo': True
        },
        {
            'codigo': 'exame_citopatologico',
            'descricao': 'Realização nos últimos 2 anos de exame citopatológico em mulheres (25–59 anos)',
            'pontos': 5,
            'peso': 1.0,
            'ativo': True
        },
        {
            'codigo': 'vacinacao_primeira_infancia',
            'descricao': 'Atualização da caderneta de vacinação na primeira infância',
            'pontos': 8,
            'peso': 1.2,
            'ativo': True
        },
        {
            'codigo': 'vacinacao_adolescentes',
            'descricao': 'Atualização da caderneta de vacinação de adolescentes',
            'pontos': 8,
            'peso': 1.2,
            'ativo': True
        },
        {
            'codigo': 'vacinacao_covid19',
            'descricao': 'Atualização da vacinação COVID‑19',
            'pontos': 5,
            'peso': 1.0,
            'ativo': True
        },
        {
            'codigo': 'eja_2025',
            'descricao': 'Alunos matriculados no EJA em 2025 (≥17 anos) ou certificado de conclusão',
            'pontos': 7,
            'peso': 1.1,
            'ativo': True
        },
        {
            'codigo': 'matricula_ativa_2025',
            'descricao': 'Matrícula ativa para o ano letivo 2025 (até 18 anos completos) ou certificado de conclusão',
            'pontos': 10,
            'peso': 1.3,
            'ativo': True
        },
        {
            'codigo': 'frequencia_escolar',
            'descricao': 'Frequência ≥75% da carga horária do ano/série (verificações bimestrais)',
            'pontos': 8,
            'peso': 1.2,
            'ativo': True
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Populando critérios de elegibilidade...'))
        
        created_count = 0
        updated_count = 0
        
        for criterio_data in self.CRITERIOS_INICIAIS:
            criterio, created = Criterio.objects.get_or_create(
                codigo=criterio_data['codigo'],
                defaults=criterio_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Criado: {criterio.descricao}')
                )
            else:
                # Atualizar critério existente (exceto o código)
                updated = False
                for field, value in criterio_data.items():
                    if field != 'codigo' and getattr(criterio, field) != value:
                        setattr(criterio, field, value)
                        updated = True
                
                if updated:
                    criterio.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Atualizado: {criterio.descricao}')
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(f'  Já existe: {criterio.descricao}')
                    )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Concluído! {created_count} critérios criados, {updated_count} atualizados.'
        ))
        self.stdout.write(self.style.NOTICE(
            f'Total de critérios ativos: {Criterio.objects.filter(ativo=True).count()}'
        ))
