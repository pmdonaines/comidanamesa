from django.db import models
from django.conf import settings
from apps.cecad.models import Familia

class Criterio(models.Model):
    descricao = models.CharField("Descrição", max_length=255)
    codigo = models.SlugField("Código Identificador", unique=True, help_text="Ex: renda_per_capita, vacinacao_em_dia")
    ativo = models.BooleanField("Ativo", default=True)
    pontos = models.IntegerField("Pontos", default=10)
    peso = models.DecimalField("Peso", max_digits=4, decimal_places=2, default=1.0)
    
    class Meta:
        verbose_name = "Critério"
        verbose_name_plural = "Critérios"

    def __str__(self):
        return f"{self.descricao} ({self.pontos} pts)"


class Validacao(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado'),
        ('em_analise', 'Em Análise'),
    ]

    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name="validacoes")
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='validacoes_finalizadas')
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField("Observações", blank=True)
    pontuacao_total = models.IntegerField("Pontuação Total", default=0)
    data_validacao = models.DateTimeField("Data da Validação", null=True, blank=True)
    
    # Controle de lock para avaliação simultânea
    em_avaliacao_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='validacoes_em_avaliacao',
        help_text="Usuário que está avaliando atualmente"
    )
    iniciado_em = models.DateTimeField(
        "Iniciado em", 
        null=True, 
        blank=True,
        help_text="Quando o usuário iniciou a avaliação"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Validação"
        verbose_name_plural = "Validações"

    def __str__(self):
        return f"Validação {self.familia} - {self.get_status_display()}"
    
    def is_disponivel_para_usuario(self, usuario, timeout_minutos=30):
        """
        Verifica se a validação está disponível para o usuário avaliar.
        
        Retorna True se:
        - Não está sendo avaliada por ninguém
        - Está sendo avaliada pelo próprio usuário
        - O lock expirou (timeout)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Se não há ninguém avaliando, está disponível
        if not self.em_avaliacao_por:
            return True
        
        # Se é o mesmo usuário, está disponível
        if self.em_avaliacao_por == usuario:
            return True
        
        # Se o lock expirou (timeout), está disponível
        if self.iniciado_em:
            tempo_decorrido = timezone.now() - self.iniciado_em
            if tempo_decorrido > timedelta(minutes=timeout_minutos):
                return True
        
        # Caso contrário, está bloqueada
        return False
    
    def iniciar_avaliacao(self, usuario):
        """Marca a validação como sendo avaliada pelo usuário."""
        from django.utils import timezone
        self.em_avaliacao_por = usuario
        self.iniciado_em = timezone.now()
        self.status = 'em_analise'
        self.save(update_fields=['em_avaliacao_por', 'iniciado_em', 'status'])
    
    def liberar_avaliacao(self):
        """Libera a validação para outros usuários."""
        self.em_avaliacao_por = None
        self.iniciado_em = None
        self.save(update_fields=['em_avaliacao_por', 'iniciado_em'])
    
    def calcular_pontuacao(self):
        """Calcula a pontuação total baseada nos critérios atendidos.
        
        Fórmula: soma de (pontos * peso) para cada critério atendido.
        """
        pontuacao = 0
        for vc in self.criterios_avaliados.select_related('criterio').filter(atendido=True):
            # Fórmula: pontos * peso
            pontuacao += int(vc.criterio.pontos * float(vc.criterio.peso))
        return pontuacao
    
    def atualizar_pontuacao(self):
        """Atualiza o campo pontuacao_total com o cálculo atual e persiste no banco."""
        self.pontuacao_total = self.calcular_pontuacao()
        self.save(update_fields=['pontuacao_total'])


class ValidacaoCriterio(models.Model):
    validacao = models.ForeignKey(Validacao, on_delete=models.CASCADE, related_name="criterios_avaliados")
    criterio = models.ForeignKey(Criterio, on_delete=models.PROTECT)
    atendido = models.BooleanField("Atendido", default=False)
    observacao = models.CharField("Observação", max_length=255, blank=True)

    class Meta:
        unique_together = ('validacao', 'criterio')
        verbose_name = "Avaliação de Critério"
        verbose_name_plural = "Avaliações de Critérios"


class Documento(models.Model):
    validacao = models.ForeignKey(Validacao, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField("Tipo de Documento", max_length=100)
    arquivo = models.FileField("Arquivo", upload_to="documentos/%Y/%m/", null=True, blank=True)
    validado = models.BooleanField("Validado", default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return f"{self.tipo} - {self.validacao.familia}"
