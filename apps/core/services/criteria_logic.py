from apps.core.models import Criterio, ValidacaoCriterio, Validacao
from django.db import transaction

class CriteriaAssociator:
    @staticmethod
    def check_applicability(criterio, familia):
        """
        Verifica se um critério é aplicável a uma família.
        Retorna (is_applicable, observacao).
        """
        # Pré-calcular condições da família
        has_children = familia.tem_criancas()
        is_rf_male = familia.is_rf_homem()
        is_unipessoal = familia.is_unipessoal()

        is_applicable = True
        observacao = ""

        # 1. Famílias sem crianças
        if not criterio.aplica_se_a_sem_criancas and not has_children:
            is_applicable = False
            observacao = "Não aplicável: Família sem crianças"
            return is_applicable, observacao
            
        # 2. RF Homem
        elif not criterio.aplica_se_a_rf_homem and is_rf_male:
            is_applicable = False
            observacao = "Não aplicável: RF é homem"
            return is_applicable, observacao
            
        # 3. Famílias Unipessoais
        elif not criterio.aplica_se_a_unipessoais and is_unipessoal:
            is_applicable = False
            observacao = "Não aplicável: Família unipessoal"
            return is_applicable, observacao
            
        # 4. Condições Avançadas (Idade/Sexo)
        elif criterio.idade_minima is not None or criterio.idade_maxima is not None or criterio.sexo_necessario:
            has_matching_member = False
            from datetime import date
            today = date.today()
            
            for membro in familia.membros.all():
                # Verificar Sexo
                if criterio.sexo_necessario and membro.cod_sexo_pessoa != criterio.sexo_necessario:
                    continue

                # Verificar Parentesco
                if criterio.parentescos_permitidos:
                    try:
                        allowed_codes = [int(c.strip()) for c in criterio.parentescos_permitidos.split(',') if c.strip()]
                        if membro.cod_parentesco_rf_pessoa not in allowed_codes:
                            continue
                    except ValueError:
                        continue
                    
                # Verificar Idade
                if membro.dat_nasc_pessoa:
                    age = today.year - membro.dat_nasc_pessoa.year - (
                        (today.month, today.day) < (membro.dat_nasc_pessoa.month, membro.dat_nasc_pessoa.day)
                    )
                    
                    # Checar Min
                    if criterio.idade_minima is not None and age < criterio.idade_minima:
                        continue
                        
                    # Checar Max
                    if criterio.idade_maxima is not None and age > criterio.idade_maxima:
                        continue
                        
                    # Se passou por tudo, este membro atende!
                    has_matching_member = True
                    break
            
            # Se nenhum membro atende às condições avançadas, não aplicável
            if not has_matching_member:
                is_applicable = False
                observacao = "Não aplicável: Nenhum membro atende aos requisitos"
                return is_applicable, observacao
        
        return is_applicable, observacao

    @staticmethod
    def associate_criteria(validacao):
        """
        Associa critérios a uma validação, respeitando as condições de aplicação.
        Retorna o número de critérios associados.
        """
        criterios = Criterio.objects.filter(ativo=True)
        
        to_create = []
        existing_ids = set(ValidacaoCriterio.objects.filter(validacao=validacao).values_list('criterio_id', flat=True))
        
        for criterio in criterios:
            if criterio.id in existing_ids:
                continue
                
            is_applicable, observacao = CriteriaAssociator.check_applicability(criterio, validacao.familia)
            
            to_create.append(
                ValidacaoCriterio(
                    validacao=validacao,
                    criterio=criterio,
                    atendido=not is_applicable, # Se não aplicável, conta como atendido (pontuação máxima)
                    aplicavel=is_applicable,
                    observacao=observacao
                )
            )
        
        if to_create:
            ValidacaoCriterio.objects.bulk_create(to_create)
            return len(to_create)
        return 0

    @staticmethod
    def update_criterion_impact(criterio):
        """
        Atualiza todas as validações quando um critério é alterado.
        Reavalia a aplicabilidade e recalcula a pontuação.
        """
        # Buscar todas as validações que possuem este critério associado
        # Usar select_related para otimizar o acesso à família e membros
        validacoes_afetadas = Validacao.objects.filter(
            criterios_avaliados__criterio=criterio
        ).select_related('familia').prefetch_related('familia__membros').distinct()
        
        updates_vc = []
        validacoes_to_update = []
        
        print(f"Atualizando impacto do critério '{criterio}' em {validacoes_afetadas.count()} validações...")
        
        with transaction.atomic():
            for validacao in validacoes_afetadas:
                # Reavaliar aplicabilidade
                is_applicable, observacao = CriteriaAssociator.check_applicability(criterio, validacao.familia)
                
                # Buscar o ValidacaoCriterio específico
                vc = validacao.criterios_avaliados.get(criterio=criterio)
                
                changed = False
                if vc.aplicavel != is_applicable:
                    vc.aplicavel = is_applicable
                    # Se tornou não aplicável -> atendido = True
                    # Se tornou aplicável -> atendido = False (precisa comprovar) - A MENOS que já tenha sido validado antes?
                    # Regra de negócio: Se tornou aplicável agora, assume que não foi atendido ainda.
                    # Se tornou não aplicável, assume atendido.
                    if not is_applicable:
                        vc.atendido = True
                    else:
                        # CUIDADO: Se já estava atendido (por exemplo, tinha documento), manter?
                        # Se a condição mudou para ser aplicável, talvez o usuário precise enviar documento.
                        # Vamos assumir False para forçar nova validação se necessário, ou manter se tiver documento validado?
                        # Por segurança, se tem documento validado, mantemos atendido?
                        # O modelo atual não linka documento diretamente ao atendido de forma rígida sem lógica.
                        # Vamos simplificar: Se virou aplicável, reseta para não atendido (False).
                        vc.atendido = False
                    
                    vc.observacao = observacao
                    vc.save() # Salvar individualmente ou adicionar a lista para bulk_update?
                    # Como vamos recalcular pontuação, melhor salvar logo para o cálculo pegar o valor novo no banco
                    # Ou atualizar o objeto em memória e passar para o calculo?
                    # O método calcular_pontuacao usa self.criterios_avaliados.filter(atendido=True)
                    # Então precisa estar salvo no banco.
                    changed = True
                
                # Se a pontuação do critério mudou, ou peso, ou aplicabilidade, precisa recalcular total da validação
                # Mesmo que aplicabilidade não mude, os pontos do critério podem ter mudado.
                validacao.atualizar_pontuacao()

