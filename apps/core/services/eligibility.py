from datetime import date, timedelta
from decimal import Decimal
from apps.core.models import Criterio, Validacao, ValidacaoCriterio

class EligibilityCalculator:
    def __init__(self, familia):
        self.familia = familia
        self.today = date.today()

    def check_eligibility(self):
        """
        Verifica critérios automáticos e retorna um status preliminar.
        """
        reasons = []
        is_eligible = True

        # Critério 1: Renda per capita <= 218
        if self.familia.vlr_renda_media_fam and self.familia.vlr_renda_media_fam > Decimal('218.00'):
            is_eligible = False
            reasons.append(f"Renda per capita (R$ {self.familia.vlr_renda_media_fam}) acima do limite (R$ 218,00)")

        # Critério 2: CadÚnico atualizado (2 anos)
        two_years_ago = self.today - timedelta(days=365*2)
        if self.familia.dat_atual_fam < two_years_ago:
            is_eligible = False
            reasons.append(f"Cadastro desatualizado (última atualização: {self.familia.dat_atual_fam})")

        return is_eligible, reasons

    def calculate_score(self, validacao):
        """
        Calcula a pontuação total baseada nos critérios avaliados na validação.
        """
        total_points = 0
        avaliacoes = ValidacaoCriterio.objects.filter(validacao=validacao, atendido=True).select_related('criterio')
        
        for avaliacao in avaliacoes:
            # Pontuação = Pontos base * Peso
            points = avaliacao.criterio.pontos * avaliacao.criterio.peso
            total_points += points
            
        return int(total_points)
