from django.db import models
from django.conf import settings
from apps.cecad.models import Familia


class Categoria(models.Model):
    """Categorias temáticas para agrupar critérios de validação."""
    
    CODIGO_CHOICES = [
        ('desenvolvimento_social', 'Desenvolvimento Social'),
        ('saude', 'Saúde'),
        ('educacao', 'Educação'),
        ('documentacao', 'Documentação'),
    ]
    
    codigo = models.CharField(
        "Código", 
        max_length=50, 
        choices=CODIGO_CHOICES, 
        unique=True
    )
    nome = models.CharField("Nome", max_length=100)
    descricao = models.TextField("Descrição", blank=True)
    ordem = models.IntegerField("Ordem de Exibição", default=0)
    icone = models.CharField(
        "Ícone (nome Heroicon)", 
        max_length=50, 
        blank=True,
        help_text="Ex: users, heart, academic-cap, document-text"
    )
    ativo = models.BooleanField("Ativo", default=True)
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['ordem']
    
    def __str__(self):
        return self.nome


class Criterio(models.Model):
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.PROTECT, 
        related_name='criterios',
        verbose_name="Categoria",
        null=True,  # Temporariamente nullable para migration
        blank=True
    )
    descricao = models.CharField("Descrição", max_length=255)
    codigo = models.SlugField("Código Identificador", unique=True, help_text="Ex: renda_per_capita, vacinacao_em_dia")
    ativo = models.BooleanField("Ativo", default=True)
    pontos = models.IntegerField("Pontos", default=10)
    peso = models.DecimalField("Peso", max_digits=4, decimal_places=2, default=1.0)
    
    # Condições de Aplicação
    aplica_se_a_sem_criancas = models.BooleanField(
        "Aplica-se a famílias sem crianças?", 
        default=True,
        help_text="Se desmarcado, este critério será ignorado para famílias que não possuem crianças (menores de 18 anos)."
    )
    aplica_se_a_rf_homem = models.BooleanField(
        "Aplica-se a RF homem?", 
        default=True,
        help_text="Se desmarcado, este critério será ignorado se o Responsável Familiar for homem."
    )
    aplica_se_a_unipessoais = models.BooleanField(
        "Aplica-se a famílias unipessoais?", 
        default=True,
        help_text="Se desmarcado, este critério NÃO será exigido para famílias de uma única pessoa."
    )
    
    # Condições Avançadas (Baseadas nos Membros)
    idade_minima = models.IntegerField(
        "Idade Mínima do Membro", 
        null=True, 
        blank=True,
        help_text="Critério só se aplica se houver membro com idade igual ou superior a esta."
    )
    idade_maxima = models.IntegerField(
        "Idade Máxima do Membro", 
        null=True, 
        blank=True,
        help_text="Critério só se aplica se houver membro com idade igual ou inferior a esta."
    )
    sexo_necessario = models.CharField(
        "Sexo Necessário",
        max_length=1,
        choices=[('1', 'Masculino'), ('2', 'Feminino')],
        null=True,
        blank=True,
        help_text="Critério só se aplica se houver membro deste sexo (respeitando a faixa etária, se definida)."
    )
    parentescos_permitidos = models.CharField(
        "Parentescos Permitidos",
        max_length=50,
        blank=True,
        help_text="Códigos de parentesco permitidos (separados por vírgula). Ex: 1,2 para RF e Cônjuge."
    )
    
    class Meta:
        verbose_name = "Critério"
        verbose_name_plural = "Critérios"
        ordering = ['categoria__ordem', 'codigo']

    def __str__(self):
        cat_nome = self.categoria.nome if self.categoria else "Sem categoria"
        return f"[{cat_nome}] {self.descricao} ({self.pontos} pts)"


class Validacao(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado'),
        ('em_analise', 'Em Análise'),
    ]

    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name="validacoes")
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='validacoes_finalizadas')
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default='pendente', db_index=True)
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
    
    def transferir_avaliacao(self, novo_usuario):
        """Transfere a avaliação para outro usuário.
        
        Args:
            novo_usuario: Instância do User para quem a validação será transferida
        """
        from django.utils import timezone
        self.em_avaliacao_por = novo_usuario
        self.iniciado_em = timezone.now()
        self.save(update_fields=['em_avaliacao_por', 'iniciado_em'])
    
    def calcular_pontuacao(self):
        """Calcula a pontuação total baseada nos critérios atendidos.
        
        Regra:
        - Soma de (pontos * peso) por categoria.
        - Cada categoria é limitada a 25 pontos.
        - Soma final é a soma das pontuações das categorias (max 100).
        """
        pontuacao_por_categoria = {}
        
        for vc in self.criterios_avaliados.select_related('criterio', 'criterio__categoria').filter(atendido=True):
            # Se não tiver categoria, usa um ID genérico (mas não deve acontecer)
            cat_id = vc.criterio.categoria_id if vc.criterio.categoria_id else -1
            
            # Mantendo a lógica de truncar para int individualmente
            pontos = int(vc.criterio.pontos * float(vc.criterio.peso))
            
            pontuacao_por_categoria[cat_id] = pontuacao_por_categoria.get(cat_id, 0) + pontos
            
        total = 0
        for cat_id, pontos in pontuacao_por_categoria.items():
            # Limitar a 25 pontos por categoria
            total += min(pontos, 25)
            
        return total
    
    def get_pontuacao_detalhada(self):
        """Retorna detalhes da pontuação por categoria."""
        pontuacao_por_categoria = {}
        
        for vc in self.criterios_avaliados.select_related('criterio', 'criterio__categoria').filter(atendido=True):
            cat_id = vc.criterio.categoria_id if vc.criterio.categoria_id else -1
            pontos = int(vc.criterio.pontos * float(vc.criterio.peso))
            pontuacao_por_categoria[cat_id] = pontuacao_por_categoria.get(cat_id, 0) + pontos
            
        detalhes = {}
        for cat_id, pontos in pontuacao_por_categoria.items():
            detalhes[cat_id] = {
                'total': pontos,
                'efetivo': min(pontos, 25)
            }
        return detalhes

    def atualizar_pontuacao(self):
        """Atualiza o campo pontuacao_total com o cálculo atual e persiste no banco."""
        self.pontuacao_total = self.calcular_pontuacao()
        self.save(update_fields=['pontuacao_total'])


class ValidacaoCriterio(models.Model):
    validacao = models.ForeignKey(Validacao, on_delete=models.CASCADE, related_name="criterios_avaliados")
    criterio = models.ForeignKey(Criterio, on_delete=models.PROTECT)
    atendido = models.BooleanField("Atendido", default=False)
    aplicavel = models.BooleanField("Aplicável", default=True)
    observacao = models.CharField("Observação", max_length=255, blank=True)
    
    # Referência ao documento que comprova o critério
    documento_comprobatorio = models.ForeignKey(
        'DocumentoPessoa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='criterios_comprovados',
        verbose_name="Documento Comprobatório"
    )


    class Meta:
        unique_together = ('validacao', 'criterio')
        verbose_name = "Avaliação de Critério"
        verbose_name_plural = "Avaliações de Critérios"


class DocumentoPessoa(models.Model):
    """Documentos pessoais vinculados a membros da família."""
    
    TIPO_CHOICES = [
        ('rg', 'RG'),
        ('cpf', 'CPF'),
        ('certidao_nascimento', 'Certidão de Nascimento'),
        ('certidao_casamento', 'Certidão de Casamento'),
        ('carteira_vacinacao', 'Carteira de Vacinação'),
        ('comprovante_matricula', 'Comprovante de Matrícula'),
        ('historico_escolar', 'Histórico Escolar'),
        ('declaracao_escolar', 'Declaração Escolar'),
        ('exame_citopatologico', 'Exame Citopatológico'),
        ('comprovante_residencia', 'Comprovante de Residência'),
        ('outro', 'Outro'),
    ]
    
    pessoa = models.ForeignKey(
        'cecad.Pessoa', 
        on_delete=models.CASCADE, 
        related_name='documentos',
        verbose_name="Pessoa"
    )
    tipo = models.CharField("Tipo", max_length=50, choices=TIPO_CHOICES)
    arquivo = models.FileField("Arquivo", upload_to="documentos/pessoas/%Y/%m/")
    numero_documento = models.CharField("Número do Documento", max_length=100, blank=True)
    data_emissao = models.DateField("Data de Emissão", null=True, blank=True)
    data_validade = models.DateField("Data de Validade", null=True, blank=True)
    observacoes = models.TextField("Observações", blank=True)
    validado = models.BooleanField("Validado", default=False)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_validados',
        verbose_name="Validado por"
    )
    validado_em = models.DateTimeField("Validado em", null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Documento Pessoal"
        verbose_name_plural = "Documentos Pessoais"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.pessoa.nom_pessoa}"



class DocumentoValidacao(models.Model):
    """Documentos específicos de uma validação (temporários, comprovantes únicos)."""
    
    validacao = models.ForeignKey(
        Validacao, 
        on_delete=models.CASCADE, 
        related_name="documentos_anexos"
    )
    tipo = models.CharField("Tipo de Documento", max_length=100)
    descricao = models.TextField("Descrição", blank=True)
    arquivo = models.FileField("Arquivo", upload_to="documentos/validacoes/%Y/%m/", null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento da Validação"
        verbose_name_plural = "Documentos das Validações"

    def __str__(self):
        return f"{self.tipo} - {self.validacao.familia}"


class Configuracao(models.Model):
    """Configurações globais do sistema (Singleton)."""
    
    pontuacao_minima_aprovacao = models.IntegerField(
        "Pontuação Mínima para Aprovação", 
        default=50,
        help_text="Pontuação mínima necessária para que uma validação seja aprovada."
    )
    
    quantidade_vagas = models.IntegerField(
        "Quantidade de Vagas",
        default=1000,
        help_text="Número total de vagas disponíveis para o benefício."
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"
        
    def __str__(self):
        return "Configuração do Sistema"

    def save(self, *args, **kwargs):
        # Garantir que só exista um objeto
        if not self.pk and Configuracao.objects.exists():
            # Se já existe, atualiza o primeiro
            self.pk = Configuracao.objects.first().pk
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class ValidacaoHistorico(models.Model):
    """Histórico de alterações em validações finalizadas."""
    
    validacao = models.ForeignKey(
        Validacao, 
        on_delete=models.CASCADE, 
        related_name='historico_edicoes',
        verbose_name="Validação"
    )
    editado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='edicoes_validacao',
        verbose_name="Editado por"
    )
    editado_em = models.DateTimeField("Editado em", auto_now_add=True)
    
    # Campos alterados (JSON para flexibilidade)
    campos_alterados = models.JSONField(
        "Campos Alterados",
        help_text="Dicionário com campos modificados e seus valores antes/depois"
    )
    
    # Snapshot dos valores principais para consulta rápida
    status_anterior = models.CharField("Status Anterior", max_length=20, blank=True)
    status_novo = models.CharField("Status Novo", max_length=20, blank=True)
    pontuacao_anterior = models.IntegerField("Pontuação Anterior", null=True, blank=True)
    pontuacao_nova = models.IntegerField("Pontuação Nova", null=True, blank=True)
    
    observacao_edicao = models.TextField(
        "Motivo da Edição",
        blank=True,
        help_text="Justificativa opcional para a edição"
    )
    
    class Meta:
        verbose_name = "Histórico de Edição"
        verbose_name_plural = "Histórico de Edições"
        ordering = ['-editado_em']
    
    def __str__(self):
        return f"Edição de {self.validacao} por {self.editado_por} em {self.editado_em.strftime('%d/%m/%Y %H:%M')}"
