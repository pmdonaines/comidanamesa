from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Q
from apps.cecad.models import Familia, ImportBatch
from apps.core.models import Validacao, Criterio, ValidacaoCriterio, DocumentoValidacao

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get latest completed batch
        latest_batch = ImportBatch.objects.filter(status='completed').order_by('-imported_at').first()
        context['latest_batch'] = latest_batch

        if latest_batch:
            context['total_familias'] = Familia.objects.filter(import_batch=latest_batch).count()
            # Filter validations for families in the latest batch
            validacoes = Validacao.objects.filter(familia__import_batch=latest_batch)
            context['validacoes_pendentes'] = validacoes.filter(status='pendente').count()
            context['validacoes_aprovadas'] = validacoes.filter(status='aprovado').count()
            context['validacoes_reprovadas'] = validacoes.filter(status='reprovado').count()
        else:
            context['total_familias'] = 0
            context['validacoes_pendentes'] = 0
            context['validacoes_aprovadas'] = 0
            context['validacoes_reprovadas'] = 0
            
        return context

class FilaValidacaoView(LoginRequiredMixin, ListView):
    model = Validacao
    template_name = 'core/fila_validacao.html'
    context_object_name = 'validacoes'
    paginate_by = 20

    def get_queryset(self):
        # Filter by latest batch by default
        latest_batch = ImportBatch.objects.filter(status='completed').order_by('-imported_at').first()
        if not latest_batch:
            return Validacao.objects.none()

        queryset = Validacao.objects.select_related('familia').filter(
            familia__import_batch=latest_batch
        )
        
        status = self.request.GET.get('status')
        if status and status != 'todos':
            queryset = queryset.filter(status=status)
        else:
            # Default to showing only pending/in_analysis items for the "Queue" view
            # unless specific filter is applied? 
            # Or should "Todos" show everything? 
            # Given it's a "Queue", let's default to pending/analysis, but if "Todos" is explicitly selected (which is the default option text but maybe not default behavior), 
            # actually, let's make "Todos" show everything, but default to pending/analysis if nothing is sent?
            # But HTMX sends nothing on first load.
            # Let's stick to: Default (no param) = Pending/Analysis. 
            # If user selects "Todos" (param='todos'), show All.
            if status == 'todos':
                pass # Show all
            else:
                queryset = queryset.filter(status__in=['pendente', 'em_analise'])

        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(familia__cod_familiar_fam__icontains=search_query) |
                Q(familia__membros__nom_pessoa__icontains=search_query)
            ).distinct()
        
        return queryset

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['core/partials/lista_validacao.html']
        return ['core/fila_validacao.html']

class ValidacaoDetailView(LoginRequiredMixin, DetailView):
    model = Validacao
    template_name = 'core/validacao_detail.html'
    context_object_name = 'validacao'

    def get(self, request, *args, **kwargs):
        """Verifica se a validação está disponível antes de exibir."""
        self.object = self.get_object()
        
        # Verificar se está disponível para o usuário atual
        if not self.object.is_disponivel_para_usuario(request.user, timeout_minutos=30):
            # Validação bloqueada por outro usuário
            messages.warning(
                request,
                f'Esta validação está sendo avaliada por {self.object.em_avaliacao_por.username}. '
                f'Por favor, aguarde ou tente novamente mais tarde.'
            )
            return redirect('fila_validacao')
        
        # Garantir que os critérios estejam associados (Lazy Loading)
        from apps.core.services.criteria_logic import CriteriaAssociator
        if CriteriaAssociator.associate_criteria(self.object) > 0:
            self.object.atualizar_pontuacao()
        
        # Se está disponível, iniciar/renovar a avaliação
        self.object.iniciar_avaliacao(request.user)
        
        # Continuar normalmente
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        from apps.core.models import Categoria
        from collections import defaultdict
        
        context = super().get_context_data(**kwargs)
        
        # Buscar todos os critérios avaliados
        criterios_avaliados = ValidacaoCriterio.objects.filter(
            validacao=self.object,
            aplicavel=True  # Apenas mostrar critérios aplicáveis na interface
        ).select_related('criterio', 'criterio__categoria').order_by('criterio__categoria__ordem', 'criterio__codigo')
        
        # Agrupar por categoria
        criterios_por_categoria = defaultdict(list)
        for vc in criterios_avaliados:
            if vc.criterio.categoria:
                criterios_por_categoria[vc.criterio.categoria].append(vc)
        
        # Passar categorias ordenadas e seus critérios
        context['categorias'] = Categoria.objects.filter(ativo=True).order_by('ordem').prefetch_related('criterios')
        context['criterios_por_categoria'] = dict(criterios_por_categoria)
        context['criterios'] = criterios_avaliados  # Manter para compatibilidade
        
        # Pontuação detalhada
        context['pontuacao_detalhada'] = self.object.get_pontuacao_detalhada()
        
        # Adicionar Responsável Familiar ao contexto
        context['responsavel_familiar'] = self.object.familia.get_responsavel_familiar()
        context['sem_rf'] = not context['responsavel_familiar']
        
        # Membros ordenados (RF primeiro)
        context['membros_ordenados'] = self.object.familia.membros.all().order_by('cod_parentesco_rf_pessoa', 'nom_pessoa')
        
        # Calcular quantidade de famílias no domicílio
        # Domicílio é identificado pelos primeiros 8 dígitos do código familiar
        cod_domicilio = self.object.familia.cod_familiar_fam[:8]
        context['qtde_familias_domicilio'] = Familia.objects.filter(
            import_batch=self.object.familia.import_batch,
            cod_familiar_fam__startswith=cod_domicilio
        ).count()
        
        return context


    def post(self, request, *args, **kwargs):
        from django.http import HttpResponse
        import json
        
        self.object = self.get_object()
        action = request.POST.get('action')
        
        # Verificar se ainda está com lock do usuário
        if not self.object.is_disponivel_para_usuario(request.user, timeout_minutos=30):
            messages.error(
                request,
                'Você perdeu o acesso a esta validação. Outro usuário pode ter assumido a avaliação.'
            )
            return redirect('fila_validacao')
        
        if action in ['save_criteria', 'finalize']:
            # DEBUG: Print POST data
            print(f"DEBUG: Action={action}, POST keys={list(request.POST.keys())}")
            
            # Primeiro, resetar todos os critérios para atendido=False
            # (checkboxes desmarcados não enviam dados no POST)
            # Primeiro, resetar apenas os critérios APLICÁVEIS para atendido=False
            # (checkboxes desmarcados não enviam dados no POST)
            # Critérios não aplicáveis devem permanecer como atendido=True (pontuação automática)
            ValidacaoCriterio.objects.filter(validacao=self.object, aplicavel=True).update(atendido=False)
            
            # Depois, marcar como atendido=True apenas os critérios que foram marcados
            for key, value in request.POST.items():
                if key.startswith('criterio_'):
                    criterio_id = int(key.split('_')[1])
                    ValidacaoCriterio.objects.filter(
                        validacao=self.object,
                        criterio_id=criterio_id
                    ).update(atendido=True)
            
            # Atualizar observações
            observacoes = request.POST.get('observacoes', '')
            if observacoes:
                self.object.observacoes = observacoes
            
            # Calcular e atualizar pontuação
            self.object.atualizar_pontuacao()
            
            if action == 'save_criteria':
                # Apenas salvar progresso, manter status atual
                self.object.status = 'em_analise'
                self.object.save(update_fields=['status', 'observacoes'])
                
                # Detectar se é uma requisição HTMX (auto-save)
                is_htmx = request.headers.get('HX-Request')
                
                if is_htmx:
                    # Para HTMX, retornar 204 No Content com trigger para atualizar pontuação
                    response = HttpResponse(status=204)
                    response['HX-Trigger'] = json.dumps({
                        'autoSaved': {
                            'pontuacao': self.object.pontuacao_total,
                            'detalhes': self.object.get_pontuacao_detalhada()
                        }
                    })
                    return response
                else:
                    # Para submissão manual, adicionar mensagem e redirecionar
                    messages.success(request, f'Progresso salvo! Pontuação atual: {self.object.pontuacao_total} pontos.')
            
            elif action == 'finalize':
                # Finalizar validação
                from django.utils import timezone
                
                # Calcular status baseado em critérios atendidos
                total_criterios = ValidacaoCriterio.objects.filter(validacao=self.object).count()
                criterios_atendidos = ValidacaoCriterio.objects.filter(
                    validacao=self.object,
                    atendido=True
                ).count()
                
                # Lógica: se a pontuação total >= pontuação mínima configurada
                from apps.core.models import Configuracao
                config = Configuracao.get_solo()
                
                if self.object.pontuacao_total >= config.pontuacao_minima_aprovacao:
                    self.object.status = 'aprovado'
                else:
                    self.object.status = 'reprovado'
                
                self.object.data_validacao = timezone.now()
                self.object.operador = request.user
                self.object.save(update_fields=['status', 'data_validacao', 'operador', 'observacoes'])
                
                # LIBERAR LOCK após finalizar
                self.object.liberar_avaliacao()
                
                messages.success(
                    request, 
                    f'Validação finalizada como {self.object.get_status_display()}! '
                    f'Pontuação final: {self.object.pontuacao_total} pontos. '
                    f'(Mínimo necessário: {config.pontuacao_minima_aprovacao})'
                )
                
                # Redirecionar para fila após finalizar
                return redirect('fila_validacao')
        
        return redirect('validacao_detail', pk=self.object.pk)


class ConfiguracaoView(LoginRequiredMixin, TemplateView):
    template_name = 'core/configuracao.html'
    
    def get_context_data(self, **kwargs):
        from apps.core.forms import ConfiguracaoForm
        from apps.core.models import Configuracao
        
        context = super().get_context_data(**kwargs)
        config = Configuracao.get_solo()
        context['form'] = ConfiguracaoForm(instance=config)
        context['config'] = config
        return context
    
    def post(self, request, *args, **kwargs):
        from apps.core.forms import ConfiguracaoForm
        from apps.core.models import Configuracao, Validacao
        
        config = Configuracao.get_solo()
        form = ConfiguracaoForm(request.POST, instance=config)
        
        if form.is_valid():
            new_config = form.save()
            new_min_score = new_config.pontuacao_minima_aprovacao
            
            # Reavaliar validações existentes
            # 1. Downgrade: Aprovados que agora estão abaixo do mínimo
            downgraded = Validacao.objects.filter(
                status='aprovado', 
                pontuacao_total__lt=new_min_score
            ).update(status='reprovado')
            
            # 2. Upgrade: Reprovados que agora atingem o mínimo
            upgraded = Validacao.objects.filter(
                status='reprovado', 
                pontuacao_total__gte=new_min_score
            ).update(status='aprovado')
            
            msg = 'Configurações atualizadas com sucesso!'
            if downgraded > 0 or upgraded > 0:
                msg += f' Reavaliação: {downgraded} reprovados e {upgraded} aprovados pelo novo critério.'
            
            messages.success(request, msg)
            return redirect('configuracao')
        
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class ListaAprovadosView(LoginRequiredMixin, ListView):
    model = Validacao
    template_name = 'core/lista_aprovados.html'
    context_object_name = 'aprovados'
    paginate_by = 50

    def get_queryset(self):
        # Filter by latest batch by default
        latest_batch = ImportBatch.objects.filter(status='completed').order_by('-imported_at').first()
        if not latest_batch:
            return Validacao.objects.none()

        return Validacao.objects.select_related('familia').filter(
            familia__import_batch=latest_batch,
            status='aprovado'
        ).order_by('-pontuacao_total', 'familia__cod_familiar_fam')

    def get_context_data(self, **kwargs):
        from apps.core.models import Configuracao
        
        context = super().get_context_data(**kwargs)
        config = Configuracao.get_solo()
        
        # Calculate rank offset for pagination
        page = context.get('page_obj')
        start_rank = (page.number - 1) * self.paginate_by + 1 if page else 1
        
        context['start_rank'] = start_rank
        context['vagas_disponiveis'] = config.quantidade_vagas
        context['total_aprovados'] = self.get_queryset().count()
        
        return context


class ValidacaoViewOnlyView(LoginRequiredMixin, DetailView):
    """View somente leitura para visualizar validações finalizadas."""
    model = Validacao
    template_name = 'core/validacao_view.html'
    context_object_name = 'validacao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['criterios'] = ValidacaoCriterio.objects.filter(
            validacao=self.object,
            aplicavel=True
        ).select_related('criterio').order_by('criterio__codigo')
        
        # Adicionar Responsável Familiar ao contexto
        context['responsavel_familiar'] = self.object.familia.get_responsavel_familiar()
        context['sem_rf'] = not context['responsavel_familiar']
        
        # Membros ordenados (RF primeiro)
        context['membros_ordenados'] = self.object.familia.membros.all().order_by('cod_parentesco_rf_pessoa', 'nom_pessoa')
        
        # Calcular quantidade de famílias no domicílio
        cod_domicilio = self.object.familia.cod_familiar_fam[:8]
        context['qtde_familias_domicilio'] = Familia.objects.filter(
            import_batch=self.object.familia.import_batch,
            cod_familiar_fam__startswith=cod_domicilio
        ).count()
        
        return context


class RelatoriosView(LoginRequiredMixin, ListView):
    model = Validacao
    template_name = 'core/relatorios.html'
    context_object_name = 'validacoes'
    paginate_by = 50

    def get_queryset(self):
        # Filter by latest batch by default
        latest_batch = ImportBatch.objects.filter(status='completed').order_by('-imported_at').first()
        if not latest_batch:
            return Validacao.objects.none()

        queryset = super().get_queryset().select_related('familia').prefetch_related('familia__membros').filter(
            familia__import_batch=latest_batch
        )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by score
        min_score = self.request.GET.get('min_score', '').strip()
        if min_score:
            try:
                queryset = queryset.filter(pontuacao_total__gte=int(min_score))
            except ValueError:
                # Ignore invalid min_score values
                pass
        
        return queryset.order_by('-pontuacao_total', 'familia__cod_familiar_fam')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics (filtered by latest batch)
        latest_batch = ImportBatch.objects.filter(status='completed').order_by('-imported_at').first()
        if latest_batch:
            all_validacoes = Validacao.objects.filter(familia__import_batch=latest_batch)
        else:
            all_validacoes = Validacao.objects.none()

        context['total_validacoes'] = all_validacoes.count()
        context['total_aprovadas'] = all_validacoes.filter(status='aprovado').count()
        context['total_reprovadas'] = all_validacoes.filter(status='reprovado').count()
        context['total_pendentes'] = all_validacoes.filter(status='pendente').count()
        
        # Current filters
        context['status_filter'] = self.request.GET.get('status', '')
        context['min_score_filter'] = self.request.GET.get('min_score', '')
        
        return context

    def render_to_response(self, context, **response_kwargs):
        # Check if CSV export is requested
        if self.request.GET.get('export') == 'csv':
            return self.export_csv(context['validacoes'])
        
        return super().render_to_response(context, **response_kwargs)

    def export_csv(self, validacoes):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="relatorio_validacoes.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Código Familiar',
            'Responsável',
            'NIS',
            'Renda Per Capita',
            'Status',
            'Pontuação'
        ])
        
        for validacao in validacoes:
            responsavel = validacao.familia.membros.first()
            writer.writerow([
                validacao.familia.cod_familiar_fam,
                responsavel.nom_pessoa if responsavel else '-',
                responsavel.num_nis_pessoa_atual if responsavel else '-',
                validacao.familia.vlr_renda_media_fam,
                validacao.get_status_display(),
                validacao.pontuacao_total
            ])
        
        return response


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


# ============================================
# GESTÃO DE CRITÉRIOS
# ============================================

class CriterioListView(LoginRequiredMixin, ListView):
    model = Criterio
    template_name = 'core/criterio_list.html'
    context_object_name = 'criterios'
    ordering = ['categoria__ordem', 'codigo']

    def get_context_data(self, **kwargs):
        from apps.core.models import Categoria
        from collections import defaultdict
        
        context = super().get_context_data(**kwargs)
        context['total_criterios'] = Criterio.objects.count()
        context['criterios_ativos'] = Criterio.objects.filter(ativo=True).count()
        
        # Agrupar critérios por categoria
        criterios_por_categoria = defaultdict(list)
        for criterio in self.get_queryset().select_related('categoria'):
            if criterio.categoria:
                criterios_por_categoria[criterio.categoria].append(criterio)
        
        context['categorias'] = Categoria.objects.filter(ativo=True).order_by('ordem')
        context['criterios_por_categoria'] = dict(criterios_por_categoria)
        
        return context



class CriterioCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'core/criterio_form.html'

    def get_context_data(self, **kwargs):
        from apps.core.models import Categoria
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo Critério'
        context['button_text'] = 'Criar Critério'
        context['categorias'] = Categoria.objects.filter(ativo=True).order_by('ordem')
        return context

    def post(self, request, *args, **kwargs):
        from apps.core.models import Categoria
        
        # Processar formulário
        descricao = request.POST.get('descricao', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        categoria_id = request.POST.get('categoria')
        
        # Campos numéricos com validação para strings vazias
        pontos_str = request.POST.get('pontos', '').strip()
        pontos = int(pontos_str) if pontos_str else 10
        
        peso_str = request.POST.get('peso', '').strip()
        peso = float(peso_str) if peso_str else 1.0
        
        ativo = request.POST.get('ativo') == 'on'

        if not descricao or not codigo:
            messages.error(request, 'Descrição e código são obrigatórios!')
            return redirect('criterio_create')
        
        if not categoria_id:
            messages.error(request, 'Categoria é obrigatória!')
            return redirect('criterio_create')

        try:
            categoria = Categoria.objects.get(pk=categoria_id)
            # Condições Avançadas
            idade_minima_str = request.POST.get('idade_minima', '').strip()
            idade_minima = int(idade_minima_str) if idade_minima_str else None
            
            idade_maxima_str = request.POST.get('idade_maxima', '').strip()
            idade_maxima = int(idade_maxima_str) if idade_maxima_str else None
            
            sexo_necessario = request.POST.get('sexo_necessario') or None

            Criterio.objects.create(
                descricao=descricao,
                codigo=codigo,
                categoria=categoria,
                pontos=pontos,
                peso=peso,
                ativo=ativo,
                aplica_se_a_sem_criancas=request.POST.get('aplica_se_a_sem_criancas') == 'on',
                aplica_se_a_rf_homem=request.POST.get('aplica_se_a_rf_homem') == 'on',
                aplica_se_a_unipessoais=request.POST.get('aplica_se_a_unipessoais') == 'on',
                idade_minima=idade_minima,
                idade_maxima=idade_maxima,
                sexo_necessario=sexo_necessario
            )
            messages.success(request, f'Critério "{descricao}" criado com sucesso!')
            return redirect('criterio_list')
        except Categoria.DoesNotExist:
            messages.error(request, 'Categoria inválida!')
            return redirect('criterio_create')
        except ValueError as e:
            messages.error(request, f'Erro nos valores numéricos: {str(e)}')
            return redirect('criterio_create')
        except Exception as e:
            messages.error(request, f'Erro ao criar critério: {str(e)}')
            return redirect('criterio_create')


class CriterioUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'core/criterio_form.html'

    def get_context_data(self, **kwargs):
        from apps.core.models import Categoria
        
        context = super().get_context_data(**kwargs)
        criterio = get_object_or_404(Criterio, pk=kwargs['pk'])
        context['criterio'] = criterio
        context['title'] = f'Editar Critério: {criterio.descricao}'
        context['button_text'] = 'Salvar Alterações'
        context['categorias'] = Categoria.objects.filter(ativo=True).order_by('ordem')
        return context

    def post(self, request, *args, **kwargs):
        from apps.core.models import Categoria
        
        criterio = get_object_or_404(Criterio, pk=kwargs['pk'])
        
        # Atualizar campos
        criterio.descricao = request.POST.get('descricao', '').strip()
        categoria_id = request.POST.get('categoria')
        
        # Campos numéricos com validação para strings vazias
        pontos_str = request.POST.get('pontos', '').strip()
        criterio.pontos = int(pontos_str) if pontos_str else 10
        
        peso_str = request.POST.get('peso', '').strip()
        criterio.peso = float(peso_str) if peso_str else 1.0
        
        criterio.ativo = request.POST.get('ativo') == 'on'
        criterio.aplica_se_a_sem_criancas = request.POST.get('aplica_se_a_sem_criancas') == 'on'
        criterio.aplica_se_a_rf_homem = request.POST.get('aplica_se_a_rf_homem') == 'on'
        criterio.aplica_se_a_unipessoais = request.POST.get('aplica_se_a_unipessoais') == 'on'
        
        # Condições Avançadas
        idade_minima_str = request.POST.get('idade_minima', '').strip()
        criterio.idade_minima = int(idade_minima_str) if idade_minima_str else None
            
        idade_maxima_str = request.POST.get('idade_maxima', '').strip()
        criterio.idade_maxima = int(idade_maxima_str) if idade_maxima_str else None
            
        criterio.sexo_necessario = request.POST.get('sexo_necessario') or None
        
        if not criterio.descricao:
            messages.error(request, 'Descrição é obrigatória!')
            return redirect('criterio_update', pk=criterio.pk)
        
        if categoria_id:
            try:
                criterio.categoria = Categoria.objects.get(pk=categoria_id)
            except Categoria.DoesNotExist:
                messages.error(request, 'Categoria inválida!')
                return redirect('criterio_update', pk=criterio.pk)

        try:
            criterio.save()
            messages.success(request, f'Critério "{criterio.descricao}" atualizado com sucesso!')
            return redirect('criterio_list')
        except ValueError as e:
            messages.error(request, f'Erro nos valores numéricos: {str(e)}')
            return redirect('criterio_update', pk=criterio.pk)
        except Exception as e:
            messages.error(request, f'Erro ao atualizar critério: {str(e)}')
            return redirect('criterio_update', pk=criterio.pk)


class CriterioDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'core/criterio_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        criterio = get_object_or_404(Criterio, pk=kwargs['pk'])
        context['criterio'] = criterio
        # Contar quantas validações usam este critério
        context['total_validacoes'] = ValidacaoCriterio.objects.filter(criterio=criterio).count()
        return context

    def post(self, request, *args, **kwargs):
        criterio = get_object_or_404(Criterio, pk=kwargs['pk'])
        descricao = criterio.descricao
        
        try:
            criterio.delete()
            messages.success(request, f'Critério "{descricao}" excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir critério: {str(e)}')
        
        return redirect('criterio_list')