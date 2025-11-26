"""Serviço para rastrear e registrar alterações em validações."""
import json
from apps.core.models import ValidacaoHistorico


class ValidationHistoryTracker:
    """Rastreia e registra alterações em validações."""
    
    @staticmethod
    def capturar_estado_atual(validacao):
        """Captura o estado atual da validação antes de editar.
        
        Args:
            validacao: Instância de Validacao
            
        Returns:
            dict: Dicionário com o estado atual da validação
        """
        return {
            'status': validacao.status,
            'pontuacao_total': validacao.pontuacao_total,
            'observacoes': validacao.observacoes,
            'criterios': {
                vc.criterio_id: {
                    'atendido': vc.atendido,
                    'descricao': vc.criterio.descricao
                }
                for vc in validacao.criterios_avaliados.select_related('criterio').all()
            }
        }
    
    @staticmethod
    def registrar_edicao(validacao, estado_anterior, usuario, observacao=''):
        """Registra uma edição no histórico.
        
        Args:
            validacao: Instância de Validacao
            estado_anterior: dict com estado antes da edição
            usuario: User que fez a edição
            observacao: str com justificativa da edição (opcional)
            
        Returns:
            ValidacaoHistorico: Registro criado
        """
        estado_atual = ValidationHistoryTracker.capturar_estado_atual(validacao)
        
        # Identificar campos alterados
        campos_alterados = {}
        
        # Verificar alteração de status
        if estado_anterior['status'] != estado_atual['status']:
            campos_alterados['status'] = {
                'antes': estado_anterior['status'],
                'depois': estado_atual['status']
            }
        
        # Verificar alteração de pontuação
        if estado_anterior['pontuacao_total'] != estado_atual['pontuacao_total']:
            campos_alterados['pontuacao_total'] = {
                'antes': estado_anterior['pontuacao_total'],
                'depois': estado_atual['pontuacao_total']
            }
        
        # Verificar alteração de observações
        if estado_anterior['observacoes'] != estado_atual['observacoes']:
            campos_alterados['observacoes'] = {
                'antes': estado_anterior['observacoes'][:100] + '...' if len(estado_anterior['observacoes']) > 100 else estado_anterior['observacoes'],
                'depois': estado_atual['observacoes'][:100] + '...' if len(estado_atual['observacoes']) > 100 else estado_atual['observacoes']
            }
        
        # Verificar alterações em critérios
        criterios_alterados = []
        for criterio_id, estado_novo in estado_atual['criterios'].items():
            estado_antigo = estado_anterior['criterios'].get(criterio_id, {})
            if estado_antigo.get('atendido') != estado_novo['atendido']:
                criterios_alterados.append({
                    'criterio_id': criterio_id,
                    'descricao': estado_novo['descricao'],
                    'antes': estado_antigo.get('atendido', False),
                    'depois': estado_novo['atendido']
                })
        
        if criterios_alterados:
            campos_alterados['criterios'] = criterios_alterados
        
        # Criar registro de histórico apenas se houver alterações
        if campos_alterados:
            return ValidacaoHistorico.objects.create(
                validacao=validacao,
                editado_por=usuario,
                campos_alterados=campos_alterados,
                status_anterior=estado_anterior['status'],
                status_novo=estado_atual['status'],
                pontuacao_anterior=estado_anterior['pontuacao_total'],
                pontuacao_nova=estado_atual['pontuacao_total'],
                observacao_edicao=observacao
            )
        
        return None
    
    @staticmethod
    def formatar_historico_para_exibicao(historico):
        """Formata o histórico para exibição no template.
        
        Args:
            historico: ValidacaoHistorico instance
            
        Returns:
            dict: Dados formatados para exibição
        """
        campos = historico.campos_alterados
        
        resumo = []
        
        if 'status' in campos:
            resumo.append(f"Status: {campos['status']['antes']} → {campos['status']['depois']}")
        
        if 'pontuacao_total' in campos:
            resumo.append(f"Pontuação: {campos['pontuacao_total']['antes']} → {campos['pontuacao_total']['depois']} pts")
        
        if 'criterios' in campos:
            qtd = len(campos['criterios'])
            resumo.append(f"{qtd} critério(s) alterado(s)")
        
        if 'observacoes' in campos:
            resumo.append("Observações alteradas")
        
        return {
            'resumo': ', '.join(resumo),
            'detalhes_json': json.dumps(campos, indent=2, ensure_ascii=False)
        }
