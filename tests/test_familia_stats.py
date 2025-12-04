"""
Testes unitários para FamiliaStatsService.

Testa os 5 tipos de relatórios com diferentes composições familiares.
"""

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.cecad.models import Familia, Pessoa, ImportBatch
from apps.core.models import Validacao
from apps.core.services.familia_stats import FamiliaStatsService


User = get_user_model()


class FamiliaStatsServiceTestCase(TestCase):
    """Testes para FamiliaStatsService."""
    
    @classmethod
    def setUpTestData(cls):
        """Criar dados de teste iniciais."""
        # Criar import batch
        cls.batch = ImportBatch.objects.create(
            description="Lote de teste",
            status='completed',
            batch_type='full'
        )
        
        # Criar user para validações
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def setUp(self):
        """Preparar cada teste."""
        # Limpar famílias e pessoas antes de cada teste
        Familia.objects.all().delete()
        Pessoa.objects.all().delete()
        Validacao.objects.all().delete()
    
    def _criar_familia_com_pessoas(self, cod_familiar, pessoas_dados, bairro=None, status_validacao='aprovado'):
        """
        Helper para criar família com pessoas e validação.
        
        Args:
            cod_familiar: Código da família
            pessoas_dados: Lista de dicts com dados da pessoa
                Ex: [{'nome': 'João', 'parentesco': 1, 'sexo': '1'}, ...]
            bairro: Nome do bairro (optional)
            status_validacao: Status da validação ('aprovado', 'reprovado', 'pendente')
        
        Returns:
            Familia instance
        """
        familia = Familia.objects.create(
            import_batch=self.batch,
            cod_familiar_fam=cod_familiar,
            dat_atual_fam=date.today(),
            nom_localidade_fam=bairro or 'Bairro Teste',
            qtde_pessoas=len(pessoas_dados)
        )
        
        # Criar pessoas com NIS único
        for idx, pessoa_data in enumerate(pessoas_dados):
            nis = f'{cod_familiar.zfill(8)}{idx:03d}'[:11]  # Gerar NIS único
            Pessoa.objects.create(
                familia=familia,
                nom_pessoa=pessoa_data['nome'],
                num_nis_pessoa_atual=nis,
                cod_parentesco_rf_pessoa=pessoa_data.get('parentesco', 1),
                cod_sexo_pessoa=pessoa_data.get('sexo', '1')
            )
        
        # Criar validação
        Validacao.objects.create(
            familia=familia,
            status=status_validacao,
            operador=self.user if status_validacao in ['aprovado', 'reprovado'] else None
        )
        
        return familia
    
    def test_maes_solo_feminina_sem_conjugue(self):
        """Teste: RF feminina sem cônjuge é contada como mãe solo."""
        # Criar: Mãe com 2 filhos (sem cônjuge)
        self._criar_familia_com_pessoas(
            'FAM001',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},  # RF feminina
                {'nome': 'João', 'parentesco': 3, 'sexo': '1'},  # Filho
                {'nome': 'Ana', 'parentesco': 3, 'sexo': '2'},   # Filha
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_maes_solo()
        
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['aprovados'], 1)
        self.assertEqual(result['reprovados'], 0)
        self.assertEqual(result['percentual_aprovacao'], 100.0)
    
    def test_maes_solo_nao_conta_com_conjugue(self):
        """Teste: Família com casal não é contada como mãe solo."""
        # Criar: Casal (RF feminina + cônjuge)
        self._criar_familia_com_pessoas(
            'FAM002',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},  # RF feminina
                {'nome': 'João', 'parentesco': 2, 'sexo': '1'},   # Cônjuge
                {'nome': 'Ana', 'parentesco': 3, 'sexo': '2'},    # Filha
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_maes_solo()
        
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['aprovados'], 0)
    
    def test_unipessoa_uma_pessoa(self):
        """Teste: Família com 1 pessoa é unipessoal."""
        # Criar: Apenas uma pessoa
        self._criar_familia_com_pessoas(
            'FAM003',
            [
                {'nome': 'João', 'parentesco': 1, 'sexo': '1'},  # RF
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_unipessoa()
        
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['aprovados'], 1)
        self.assertEqual(result['percentual_aprovacao'], 100.0)
    
    def test_unipessoa_nao_conta_multiplas_pessoas(self):
        """Teste: Família com múltiplas pessoas não é unipessoal."""
        # Criar: Casal sem filhos
        self._criar_familia_com_pessoas(
            'FAM004',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},
                {'nome': 'João', 'parentesco': 2, 'sexo': '1'},
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_unipessoa()
        
        self.assertEqual(result['total'], 0)
    
    def test_casal_sem_filho_exatamente_dois_sem_filhos(self):
        """Teste: Casal sem filhos (2 pessoas, 0 filhos)."""
        # Criar: Casal puro (sem filhos)
        self._criar_familia_com_pessoas(
            'FAM005',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},
                {'nome': 'João', 'parentesco': 2, 'sexo': '1'},
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_casal_sem_filho()
        
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['aprovados'], 1)
    
    def test_casal_sem_filho_nao_conta_com_filhos(self):
        """Teste: Casal com filhos não é contado em 'casal sem filho'."""
        # Criar: Casal com 1 filho
        self._criar_familia_com_pessoas(
            'FAM006',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},
                {'nome': 'João', 'parentesco': 2, 'sexo': '1'},
                {'nome': 'Ana', 'parentesco': 3, 'sexo': '2'},
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_casal_sem_filho()
        
        self.assertEqual(result['total'], 0)
    
    def test_filhos_quantitativos_categoria_2_filhos(self):
        """Teste: Famílias com exatamente 2 filhos."""
        # Criar: RF + 2 filhos
        self._criar_familia_com_pessoas(
            'FAM007',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},
                {'nome': 'João', 'parentesco': 3, 'sexo': '1'},
                {'nome': 'Ana', 'parentesco': 3, 'sexo': '2'},
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_filhos_quantitativos()
        
        self.assertEqual(result['2']['total'], 1)
        self.assertEqual(result['2']['aprovados'], 1)
        self.assertEqual(result['3']['total'], 0)
        self.assertEqual(result['4']['total'], 0)
    
    def test_filhos_quantitativos_categoria_5_mais(self):
        """Teste: Famílias com 5 ou mais filhos."""
        # Criar: RF + 5 filhos
        pessoas = [{'nome': 'Maria', 'parentesco': 1, 'sexo': '2'}]
        for i in range(5):
            pessoas.append({
                'nome': f'Filho{i+1}',
                'parentesco': 3,
                'sexo': '1' if i % 2 == 0 else '2'
            })
        
        self._criar_familia_com_pessoas('FAM008', pessoas, status_validacao='aprovado')
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_filhos_quantitativos()
        
        self.assertEqual(result['5+']['total'], 1)
        self.assertEqual(result['5+']['aprovados'], 1)
        self.assertEqual(result['2']['total'], 0)
        self.assertEqual(result['3']['total'], 0)
        self.assertEqual(result['4']['total'], 0)
    
    def test_filhos_quantitativos_multiplas_categorias(self):
        """Teste: Múltiplas famílias em diferentes categorias."""
        # Criar: 2 filhos
        self._criar_familia_com_pessoas(
            'FAM009',
            [
                {'nome': 'Maria', 'parentesco': 1, 'sexo': '2'},
                {'nome': 'João', 'parentesco': 3, 'sexo': '1'},
                {'nome': 'Ana', 'parentesco': 3, 'sexo': '2'},
            ],
            status_validacao='aprovado'
        )
        
        # Criar: 3 filhos
        self._criar_familia_com_pessoas(
            'FAM010',
            [
                {'nome': 'Pedro', 'parentesco': 1, 'sexo': '1'},
                {'nome': 'Anna', 'parentesco': 3, 'sexo': '2'},
                {'nome': 'Bruno', 'parentesco': 3, 'sexo': '1'},
                {'nome': 'Carla', 'parentesco': 3, 'sexo': '2'},
            ],
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_filhos_quantitativos()
        
        self.assertEqual(result['2']['total'], 1)
        self.assertEqual(result['3']['total'], 1)
        self.assertEqual(result['4']['total'], 0)
        self.assertEqual(result['5+']['total'], 0)
    
    def test_por_bairro_agregacao_basica(self):
        """Teste: Agregação por bairro."""
        # Criar: 2 famílias no Bairro A
        self._criar_familia_com_pessoas(
            'FAM011',
            [{'nome': 'Maria', 'parentesco': 1, 'sexo': '2'}],
            bairro='Bairro A',
            status_validacao='aprovado'
        )
        
        self._criar_familia_com_pessoas(
            'FAM012',
            [{'nome': 'João', 'parentesco': 1, 'sexo': '1'}],
            bairro='Bairro A',
            status_validacao='reprovado'
        )
        
        # Criar: 1 família no Bairro B
        self._criar_familia_com_pessoas(
            'FAM013',
            [{'nome': 'Pedro', 'parentesco': 1, 'sexo': '1'}],
            bairro='Bairro B',
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_por_bairro()
        
        self.assertIn('Bairro A', result)
        self.assertIn('Bairro B', result)
        self.assertEqual(result['Bairro A']['total'], 2)
        self.assertEqual(result['Bairro A']['aprovados'], 1)
        self.assertEqual(result['Bairro B']['total'], 1)
        self.assertEqual(result['Bairro B']['aprovados'], 1)
    
    def test_por_bairro_filtro_minimo_familias(self):
        """Teste: Filtro de mínimo de famílias por bairro."""
        # Criar: 1 família no Bairro A
        self._criar_familia_com_pessoas(
            'FAM014',
            [{'nome': 'Maria', 'parentesco': 1, 'sexo': '2'}],
            bairro='Bairro A',
            status_validacao='aprovado'
        )
        
        # Criar: 2 famílias no Bairro B
        self._criar_familia_com_pessoas(
            'FAM015',
            [{'nome': 'João', 'parentesco': 1, 'sexo': '1'}],
            bairro='Bairro B',
            status_validacao='aprovado'
        )
        
        self._criar_familia_com_pessoas(
            'FAM016',
            [{'nome': 'Pedro', 'parentesco': 1, 'sexo': '1'}],
            bairro='Bairro B',
            status_validacao='aprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_por_bairro(min_familias=2)
        
        # Apenas Bairro B deve aparecer (tem 2 famílias)
        self.assertNotIn('Bairro A', result)
        self.assertIn('Bairro B', result)
        self.assertEqual(result['Bairro B']['total'], 2)
    
    def test_filtro_por_bairro_na_service(self):
        """Teste: Filtro de bairro funciona corretamente."""
        # Criar: 1 família em Bairro A
        self._criar_familia_com_pessoas(
            'FAM017',
            [{'nome': 'Maria', 'parentesco': 1, 'sexo': '2'}],
            bairro='Bairro A',
            status_validacao='aprovado'
        )
        
        # Criar: 1 família em Bairro B
        self._criar_familia_com_pessoas(
            'FAM018',
            [{'nome': 'João', 'parentesco': 1, 'sexo': '1'}],
            bairro='Bairro B',
            status_validacao='aprovado'
        )
        
        # Service sem filtro: 2 unipessoas
        service_sem_filtro = FamiliaStatsService(import_batch=self.batch)
        result = service_sem_filtro.get_unipessoa()
        self.assertEqual(result['total'], 2)
        
        # Service com filtro Bairro A: 1 unipessoa
        service_com_filtro = FamiliaStatsService(
            import_batch=self.batch,
            filtros={'bairro': 'Bairro A'}
        )
        result = service_com_filtro.get_unipessoa()
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['aprovados'], 1)
    
    def test_percentual_aprovacao_calculo(self):
        """Teste: Percentual de aprovação é calculado corretamente."""
        # Criar: 2 unipessoas, 1 aprovada e 1 reprovada
        self._criar_familia_com_pessoas(
            'FAM019',
            [{'nome': 'Maria', 'parentesco': 1, 'sexo': '2'}],
            status_validacao='aprovado'
        )
        
        self._criar_familia_com_pessoas(
            'FAM020',
            [{'nome': 'João', 'parentesco': 1, 'sexo': '1'}],
            status_validacao='reprovado'
        )
        
        service = FamiliaStatsService(import_batch=self.batch)
        result = service.get_unipessoa()
        
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['aprovados'], 1)
        self.assertEqual(result['reprovados'], 1)
        self.assertEqual(result['percentual_aprovacao'], 50.0)
    
    def test_dados_vazios_sem_erros(self):
        """Teste: Service retorna 0 sem erros quando não há dados."""
        service = FamiliaStatsService(import_batch=self.batch)
        
        # Não deve lançar exceção
        result_maes = service.get_maes_solo()
        result_uni = service.get_unipessoa()
        result_casal = service.get_casal_sem_filho()
        result_filhos = service.get_filhos_quantitativos()
        result_bairro = service.get_por_bairro()
        
        self.assertEqual(result_maes['total'], 0)
        self.assertEqual(result_uni['total'], 0)
        self.assertEqual(result_casal['total'], 0)
        self.assertEqual(result_filhos['2']['total'], 0)
        self.assertEqual(len(result_bairro), 0)
