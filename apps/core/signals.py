from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import Criterio, Validacao, ValidacaoCriterio


@receiver(post_save, sender=Criterio)
def associar_criterio_a_validacoes(sender, instance, created, **kwargs):
    """
    Quando um novo critério é criado, associa automaticamente a todas as validações existentes.
    """
    if created and instance.ativo:
        # Buscar todas as validações que não possuem este critério
        # Otimizar queries para verificar condições
        validacoes = Validacao.objects.select_related('familia').prefetch_related('familia__membros').all()
        
        # Criar associações em massa
        associacoes = []
        for validacao in validacoes:
            # Verificar condições de aplicação
            familia = validacao.familia
            
            # 1. Famílias sem crianças
            if not instance.aplica_se_a_sem_criancas and not familia.tem_criancas():
                continue
                
            # 2. RF Homem
            if not instance.aplica_se_a_rf_homem and familia.is_rf_homem():
                continue
                
            # 3. Famílias Unipessoais
            if not instance.aplica_se_a_unipessoais and familia.is_unipessoal():
                continue
            
            # Verificar se já existe para evitar duplicação
            if not ValidacaoCriterio.objects.filter(validacao=validacao, criterio=instance).exists():
                associacoes.append(
                    ValidacaoCriterio(
                        validacao=validacao,
                        criterio=instance,
                        atendido=False
                    )
                )
        
        # Criar todas de uma vez
        if associacoes:
            ValidacaoCriterio.objects.bulk_create(associacoes, ignore_conflicts=True)
            print(f"✓ Critério '{instance.descricao}' associado a {len(associacoes)} validações")
