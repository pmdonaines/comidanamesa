from apps.core.models import Criterio, ValidacaoCriterio

class CriteriaAssociator:
    @staticmethod
    def associate_criteria(validacao):
        """
        Associa critérios a uma validação, respeitando as condições de aplicação.
        Retorna o número de critérios associados.
        """
        familia = validacao.familia
        criterios = Criterio.objects.filter(ativo=True)
        
        # Pré-calcular condições da família
        has_children = familia.tem_criancas()
        is_rf_male = familia.is_rf_homem()
        is_unipessoal = familia.is_unipessoal()
        
        to_create = []
        existing_ids = set(ValidacaoCriterio.objects.filter(validacao=validacao).values_list('criterio_id', flat=True))
        
        for criterio in criterios:
            # Se já existe, pular
            if criterio.id in existing_ids:
                continue
                
            # Verificar condições
            
            # 1. Famílias sem crianças
            # Se o critério diz que NÃO se aplica a famílias sem crianças (aplica_se_a_sem_criancas=False)
            # E a família NÃO tem crianças -> Ignorar
            if not criterio.aplica_se_a_sem_criancas and not has_children:
                continue
                
            # 2. RF Homem
            # Se o critério diz que NÃO se aplica a RF homem (aplica_se_a_rf_homem=False)
            # E o RF É homem -> Ignorar
            if not criterio.aplica_se_a_rf_homem and is_rf_male:
                continue
                
            # 3. Famílias Unipessoais
            # Se o critério diz que NÃO se aplica a unipessoais (aplica_se_a_unipessoais=False)
            # E a família É unipessoal -> Ignorar
            if not criterio.aplica_se_a_unipessoais and is_unipessoal:
                continue
            
            to_create.append(
                ValidacaoCriterio(
                    validacao=validacao,
                    criterio=criterio,
                    atendido=False
                )
            )
        
        if to_create:
            ValidacaoCriterio.objects.bulk_create(to_create)
            return len(to_create)
        return 0
