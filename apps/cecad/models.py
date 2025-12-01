from django.db import models
from django.conf import settings

class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('error', 'Erro'),
    ]

    description = models.CharField("Descrição", max_length=255, blank=True)
    imported_at = models.DateTimeField("Data de Importação", auto_now_add=True)
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default='processing')
    original_file = models.FileField("Arquivo Original", upload_to='imports/cecad/', null=True, blank=True)
    batch_type = models.CharField("Tipo de Lote", max_length=20, choices=[('full', 'Importação Completa'), ('correction', 'Correção')], default='full')
    total_rows = models.IntegerField("Total de Linhas", default=0)
    processed_rows = models.IntegerField("Linhas Processadas", default=0)
    error_message = models.TextField("Mensagem de Erro", blank=True)

    class Meta:
        verbose_name = "Lote de Importação"
        verbose_name_plural = "Lotes de Importação"
        ordering = ["-imported_at"]

    def __str__(self):
        return f"Importação {self.pk} - {self.imported_at.strftime('%d/%m/%Y %H:%M')}"


class Familia(models.Model):
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="familias", verbose_name="Lote de Importação", null=True, blank=True)
    cod_familiar_fam = models.CharField("Código Familiar", max_length=11)
    dat_atual_fam = models.DateField("Data de Atualização")
    vlr_renda_media_fam = models.DecimalField("Renda Média Familiar", max_digits=10, decimal_places=2, null=True, blank=True)
    vlr_renda_total_fam = models.DecimalField("Renda Total Familiar", max_digits=10, decimal_places=2, null=True, blank=True)
    marc_pbf = models.BooleanField("Beneficiário Bolsa Família", default=False)
    ref_cad = models.CharField("Referência Cadastro Único", max_length=20, null=True, blank=True)
    ref_pbf = models.CharField("Referência Bolsa Família", max_length=20, null=True, blank=True)
    qtde_pessoas = models.IntegerField("Quantidade de Pessoas", default=0)
    
    # Endereço
    nom_logradouro_fam = models.CharField("Logradouro", max_length=255, blank=True)
    num_logradouro_fam = models.CharField("Número", max_length=20, blank=True)
    nom_localidade_fam = models.CharField("Bairro/Localidade", max_length=100, blank=True)
    num_cep_logradouro_fam = models.CharField("CEP", max_length=8, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Família"
        verbose_name_plural = "Famílias"
        ordering = ["-dat_atual_fam"]
        # Permitir múltiplas famílias com mesmo código se forem de batches diferentes ou sem batch
        constraints = [
            models.UniqueConstraint(
                fields=['cod_familiar_fam', 'import_batch'],
                name='unique_familia_per_batch',
                condition=models.Q(import_batch__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['cod_familiar_fam'],
                name='unique_manual_familia',
                condition=models.Q(import_batch__isnull=True)
            )
        ]

    def __str__(self):
        return f"{self.cod_familiar_fam} - Renda: {self.vlr_renda_media_fam}"

    def tem_criancas(self):
        """Verifica se a família possui crianças/adolescentes (menores de 18 anos)."""
        from datetime import date
        today = date.today()
        
        # Buscar membros com data de nascimento
        for membro in self.membros.all():
            if membro.dat_nasc_pessoa:
                age = today.year - membro.dat_nasc_pessoa.year - (
                    (today.month, today.day) < (membro.dat_nasc_pessoa.month, membro.dat_nasc_pessoa.day)
                )
                if age < 18:
                    return True
        return False

    def is_rf_homem(self):
        """Verifica se o Responsável Familiar é do sexo masculino."""
        rf = self.membros.filter(cod_parentesco_rf_pessoa=1).first()
        if rf and rf.cod_sexo_pessoa == '1':
            return True
        return False

    def is_unipessoal(self):
        """Verifica se é uma família unipessoal."""
        return self.qtde_pessoas == 1 or self.membros.count() == 1

    def get_responsavel_familiar(self):
        """Retorna o Responsável Familiar (cod_parentesco_rf_pessoa=1) ou None."""
        return self.membros.filter(cod_parentesco_rf_pessoa=1).first()
    
    @property
    def responsavel_familiar(self):
        """Propriedade para acesso fácil ao Responsável Familiar."""
        return self.get_responsavel_familiar()


class Pessoa(models.Model):
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name="membros")
    num_nis_pessoa_atual = models.CharField("NIS", max_length=11)
    nom_pessoa = models.CharField("Nome", max_length=255)
    num_cpf_pessoa = models.CharField("CPF", max_length=11, null=True, blank=True)
    dat_nasc_pessoa = models.DateField("Data de Nascimento", null=True, blank=True)
    cod_parentesco_rf_pessoa = models.IntegerField("Código Parentesco", choices=[
        (1, "Responsável Familiar"),
        (2, "Cônjuge ou Companheiro"),
        (3, "Filho(a)"),
        (4, "Enteado(a)"),
        (5, "Neto(a) ou Bisneto(a)"),
        (6, "Pai ou Mãe"),
        (7, "Sogro(a)"),
        (8, "Irmão ou Irmã"),
        (9, "Genro ou Nora"),
        (10, "Outros Parentes"),
        (11, "Não Parente"),
    ], default=1)
    
    cod_sexo_pessoa = models.CharField("Sexo", max_length=1, choices=[('1', 'Masculino'), ('2', 'Feminino')], default='2')
    
    # Dados Escolares
    cod_curso_frequentou_pessoa_membro = models.IntegerField("Curso Frequentado", null=True, blank=True)
    cod_ano_serie_frequentou_pessoa_membro = models.IntegerField("Ano/Série Frequentado", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pessoa"
        verbose_name_plural = "Pessoas"
        unique_together = ['num_nis_pessoa_atual', 'familia']

    def __str__(self):
        return f"{self.nom_pessoa} ({self.num_nis_pessoa_atual})"
    
    @property
    def import_batch(self):
        """Acesso transitivo ao import_batch via familia."""
        return self.familia.import_batch if self.familia else None


class Beneficio(models.Model):
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name="beneficios")
    tipo_beneficio = models.CharField("Tipo de Benefício", max_length=100)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2)
    data_referencia = models.DateField("Data de Referência")

    class Meta:
        verbose_name = "Benefício"
        verbose_name_plural = "Benefícios"

    def __str__(self):
        return f"{self.tipo_beneficio} - {self.valor}"
    
    @property
    def import_batch(self):
        """Acesso transitivo ao import_batch via familia."""
        return self.familia.import_batch if self.familia else None


class PessoaTransferHistory(models.Model):
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='transferencias')
    origem = models.ForeignKey(Familia, on_delete=models.SET_NULL, null=True, related_name='transferencias_saida')
    destino = models.ForeignKey(Familia, on_delete=models.SET_NULL, null=True, related_name='transferencias_entrada')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    transferido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de Transferência'
        verbose_name_plural = 'Históricos de Transferência'
        ordering = ['-transferido_em']

    def __str__(self):
        pessoa = self.pessoa.nom_pessoa if self.pessoa_id else 'Pessoa removida'
        o = self.origem.cod_familiar_fam if self.origem_id else '-'
        d = self.destino.cod_familiar_fam if self.destino_id else '-'
        return f"{pessoa}: {o} -> {d} em {self.transferido_em:%d/%m/%Y %H:%M}"
