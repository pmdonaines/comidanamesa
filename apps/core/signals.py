from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import Criterio, Validacao, ValidacaoCriterio
from apps.core.services.criteria_logic import CriteriaAssociator


@receiver(post_save, sender=Criterio)
def associar_criterio_a_validacoes(sender, instance, created, **kwargs):
    """
    Quando um novo critério é criado, associa automaticamente a todas as validações existentes.
    Quando um critério é atualizado, reavalia o impacto em todas as validações.
    """
    if created and instance.ativo:
        # Buscar todas as validações que não possuem este critério
        validacoes = Validacao.objects.select_related('familia').prefetch_related('familia__membros').all()
        
        # Criar associações em massa usando a lógica centralizada
        count = 0
        for validacao in validacoes:
            # Verifica se já existe
            if not ValidacaoCriterio.objects.filter(validacao=validacao, criterio=instance).exists():
                is_applicable, observacao = CriteriaAssociator.check_applicability(instance, validacao.familia)
                
                ValidacaoCriterio.objects.create(
                    validacao=validacao,
                    criterio=instance,
                    atendido=not is_applicable,
                    aplicavel=is_applicable,
                    observacao=observacao
                )
                count += 1
                
        if count > 0:
            print(f"✓ Critério '{instance.descricao}' associado a {count} validações")
            
    elif not created and instance.ativo:
        # Se foi atualizado, chama o serviço de atualização de impacto
        CriteriaAssociator.update_criterion_impact(instance)

