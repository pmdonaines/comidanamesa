from django.db import models
from django.conf import settings


class BSDIExportacao(models.Model):
    """Histórico de exportações de listas para o Banco Social de Dona Inês."""
    
    STATUS_CHOICES = [
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('erro', 'Erro'),
    ]
    
    import_batch = models.ForeignKey(
        'cecad.ImportBatch',
        on_delete=models.CASCADE,
        related_name='exportacoes_bsdi',
        verbose_name="Lote de Importação",
        help_text="Lote CECAD do qual os beneficiários aprovados foram extraídos"
    )
    
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exportacoes_bsdi',
        verbose_name="Gerado por"
    )
    
    arquivo = models.FileField(
        "Arquivo XLS",
        upload_to='exports/bsdi/%Y/%m/',
        null=True,
        blank=True
    )
    
    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default='processando'
    )
    
    total_beneficiarios = models.IntegerField(
        "Total de Beneficiários",
        default=0,
        help_text="Quantidade de famílias aprovadas incluídas na lista"
    )
    
    descricao = models.CharField(
        "Descrição",
        max_length=255,
        blank=True
    )
    
    mensagem_erro = models.TextField(
        "Mensagem de Erro",
        blank=True
    )
    
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)
    
    class Meta:
        verbose_name = "Exportação BSDI"
        verbose_name_plural = "Exportações BSDI"
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"Exportação BSDI #{self.pk} - {self.criado_em.strftime('%d/%m/%Y %H:%M')} ({self.total_beneficiarios} beneficiários)"
