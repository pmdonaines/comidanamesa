import pytest
from datetime import date, timedelta
from decimal import Decimal
from apps.cecad.models import Familia
from apps.core.models import Validacao, Criterio, ValidacaoCriterio
from apps.core.services.eligibility import EligibilityCalculator

@pytest.mark.django_db
def test_eligibility_check_income():
    # Família com renda alta
    familia = Familia.objects.create(
        cod_familiar_fam="123",
        dat_atual_fam=date.today(),
        vlr_renda_media_fam=Decimal('300.00')
    )
    calculator = EligibilityCalculator(familia)
    eligible, reasons = calculator.check_eligibility()
    assert eligible is False
    assert "Renda per capita" in reasons[0]

    # Família com renda baixa
    familia.vlr_renda_media_fam = Decimal('100.00')
    familia.save()
    calculator = EligibilityCalculator(familia)
    eligible, reasons = calculator.check_eligibility()
    assert eligible is True
    assert len(reasons) == 0

@pytest.mark.django_db
def test_eligibility_check_date():
    # Família desatualizada
    old_date = date.today() - timedelta(days=365*3)
    familia = Familia.objects.create(
        cod_familiar_fam="456",
        dat_atual_fam=old_date,
        vlr_renda_media_fam=Decimal('100.00')
    )
    calculator = EligibilityCalculator(familia)
    eligible, reasons = calculator.check_eligibility()
    assert eligible is False
    assert "Cadastro desatualizado" in reasons[0]

@pytest.mark.django_db
def test_calculate_score():
    familia = Familia.objects.create(
        cod_familiar_fam="789",
        dat_atual_fam=date.today(),
        vlr_renda_media_fam=Decimal('100.00')
    )
    validacao = Validacao.objects.create(familia=familia)
    
    c1 = Criterio.objects.create(descricao="C1", codigo="c1", pontos=10, peso=1.0)
    c2 = Criterio.objects.create(descricao="C2", codigo="c2", pontos=5, peso=2.0) # 10 pontos
    
    ValidacaoCriterio.objects.create(validacao=validacao, criterio=c1, atendido=True)
    ValidacaoCriterio.objects.create(validacao=validacao, criterio=c2, atendido=True)
    
    calculator = EligibilityCalculator(familia)
    score = calculator.calculate_score(validacao)
    assert score == 20
