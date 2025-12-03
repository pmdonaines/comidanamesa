from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse_lazy, reverse
from .models import Familia, Pessoa, Beneficio, ImportBatch
from .forms import FamiliaForm, PessoaForm
from .services.importer import CecadImporter
from apps.core.models import Validacao
import os
import threading

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "cecad/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get latest completed batch (only full imports)
        latest_batch = ImportBatch.objects.filter(status='completed', batch_type='full').first()
        context['latest_batch'] = latest_batch
        
        if latest_batch:
            context['total_familias'] = Familia.objects.filter(import_batch=latest_batch).count()
            context['total_pessoas'] = Pessoa.objects.filter(familia__import_batch=latest_batch).count()
            context['familias_pbf'] = Familia.objects.filter(import_batch=latest_batch, marc_pbf=True).count()
            context['renda_media_geral'] = Familia.objects.filter(import_batch=latest_batch).aggregate(Avg('vlr_renda_media_fam'))['vlr_renda_media_fam__avg'] or 0
        else:
            context['total_familias'] = 0
            context['total_pessoas'] = 0
            context['familias_pbf'] = 0
            context['renda_media_geral'] = 0
            
        return context

class ImportDataView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "cecad/import_form.html"

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Você não tem permissão para realizar importações.")
            return redirect('cecad_dashboard')
        return super().handle_no_permission()

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo CSV.')
            return redirect('cecad_import')

        csv_file = request.FILES['csv_file']
        description = request.POST.get('description', '')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'O arquivo deve ser um CSV.')
            return redirect('cecad_import')

        # Save temporary file
        import uuid
        ext = os.path.splitext(csv_file.name)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = f'/tmp/{unique_filename}'
        with open(file_path, 'wb+') as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)

        # Create ImportBatch
        batch = ImportBatch.objects.create(
            description=description or f"Importação de {csv_file.name}",
            original_file=csv_file
        )

        # Run import in background thread
        def run_import():
            importer = CecadImporter(file_path, batch)
            importer.run()
            # Clean up temp file after import
            try:
                os.remove(file_path)
            except:
                pass
        
        thread = threading.Thread(target=run_import)
        thread.daemon = True
        thread.start()
        
        # Redirect immediately to progress page
        return redirect('cecad_import_progress', pk=batch.pk)

class ImportCorrectionView(ImportDataView):
    template_name = "cecad/import_correction_form.html"

    def post(self, request):
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Por favor, selecione um arquivo CSV.')
            return redirect('cecad_import_correction')

        csv_file = request.FILES['csv_file']
        description = request.POST.get('description', '')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'O arquivo deve ser um CSV.')
            return redirect('cecad_import_correction')

        # Save temporary file
        import uuid
        ext = os.path.splitext(csv_file.name)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = f'/tmp/{unique_filename}'
        with open(file_path, 'wb+') as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)

        # Create ImportBatch
        batch = ImportBatch.objects.create(
            description=description or f"Correção de {csv_file.name}",
            original_file=csv_file,
            batch_type='correction'
        )

        # Run import in background thread with correction_mode=True
        def run_import():
            importer = CecadImporter(file_path, batch, correction_mode=True)
            importer.run()
            # Clean up temp file after import
            try:
                os.remove(file_path)
            except:
                pass
        
        thread = threading.Thread(target=run_import)
        thread.daemon = True
        thread.start()
        
        # Redirect immediately to progress page
        return redirect('cecad_import_progress', pk=batch.pk)

class ImportBatchListView(LoginRequiredMixin, ListView):
    model = ImportBatch
    template_name = "cecad/import_batch_list.html"
    context_object_name = "batches"
    paginate_by = 10

class ImportBatchDetailView(LoginRequiredMixin, DetailView):
    model = ImportBatch
    template_name = "cecad/import_batch_detail.html"
    context_object_name = "batch"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        batch = self.object
        context['total_familias'] = batch.familias.count()
        context['total_pessoas'] = Pessoa.objects.filter(familia__import_batch=batch).count()
        context['familias_pbf'] = batch.familias.filter(marc_pbf=True).count()
        context['renda_media'] = batch.familias.aggregate(Avg('vlr_renda_media_fam'))['vlr_renda_media_fam__avg'] or 0
        return context

class ComparisonView(LoginRequiredMixin, View):
    template_name = "cecad/comparison.html"

    def get(self, request):
        batches = ImportBatch.objects.filter(status='completed')
        return render(request, self.template_name, {'batches': batches})

    def post(self, request):
        batch1_id = request.POST.get('batch1')
        batch2_id = request.POST.get('batch2')
        
        if not batch1_id or not batch2_id:
            messages.error(request, "Selecione dois lotes para comparar.")
            return redirect('cecad_comparison')
            
        batch1 = get_object_or_404(ImportBatch, pk=batch1_id)
        batch2 = get_object_or_404(ImportBatch, pk=batch2_id)
        
        # Simple comparison logic
        stats1 = {
            'total_familias': batch1.familias.count(),
            'total_pessoas': Pessoa.objects.filter(familia__import_batch=batch1).count(),
            'renda_media': batch1.familias.aggregate(Avg('vlr_renda_media_fam'))['vlr_renda_media_fam__avg'] or 0
        }
        
        stats2 = {
            'total_familias': batch2.familias.count(),
            'total_pessoas': Pessoa.objects.filter(familia__import_batch=batch2).count(),
            'renda_media': batch2.familias.aggregate(Avg('vlr_renda_media_fam'))['vlr_renda_media_fam__avg'] or 0
        }
        
        diff = {
            'familias': stats2['total_familias'] - stats1['total_familias'],
            'pessoas': stats2['total_pessoas'] - stats1['total_pessoas'],
            'renda': stats2['renda_media'] - stats1['renda_media']
        }
        
        return render(request, self.template_name, {
            'batches': ImportBatch.objects.filter(status='completed'),
            'batch1': batch1,
            'batch2': batch2,
            'stats1': stats1,
            'stats2': stats2,
            'diff': diff
        })

class FamiliaListView(LoginRequiredMixin, ListView):
    model = Familia
    template_name = "cecad/familia_list.html"
    context_object_name = "familias"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('membros')
        
        # Filter by batch if provided
        batch_id = self.request.GET.get('batch')
        if batch_id:
            queryset = queryset.filter(import_batch_id=batch_id)
        elif batch_id != 'manual':  # Se não especificou batch, mostrar latest + manuais
            latest_batch = ImportBatch.objects.filter(status='completed', batch_type='full').first()
            if latest_batch:
                queryset = queryset.filter(
                    Q(import_batch=latest_batch) | Q(import_batch__isnull=True)
                )
            else:
                # Se não há batch, mostrar apenas manuais
                queryset = queryset.filter(import_batch__isnull=True)

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(cod_familiar_fam__icontains=query) |
                Q(membros__nom_pessoa__icontains=query) |
                Q(membros__num_nis_pessoa_atual__icontains=query)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['batches'] = ImportBatch.objects.filter(status='completed')
        context['selected_batch'] = self.request.GET.get('batch')
        return context

class FamiliaDetailView(LoginRequiredMixin, DetailView):
    model = Familia
    template_name = "cecad/familia_detail.html"
    context_object_name = "familia"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membros'] = self.object.membros.all()
        context['beneficios'] = self.object.beneficios.all()
        return context

class ImportProgressView(LoginRequiredMixin, DetailView):
    model = ImportBatch
    template_name = "cecad/import_progress.html"
    context_object_name = "batch"

class ImportProgressAPIView(LoginRequiredMixin, View):
    """API endpoint for HTMX polling of import progress"""
    
    def get(self, request, pk):
        batch = get_object_or_404(ImportBatch, pk=pk)
        
        # Calculate progress percentage
        if batch.total_rows > 0:
            percent = int((batch.processed_rows / batch.total_rows) * 100)
        else:
            percent = 0
        
        data = {
            'status': batch.status,
            'total_rows': batch.total_rows,
            'processed_rows': batch.processed_rows,
            'percent': percent,
            'error_message': batch.error_message,
        }
        
        return JsonResponse(data)


# ============================================
# CRUD DE FAMÍLIA
# ============================================

class FamiliaCreateView(LoginRequiredMixin, CreateView):
    """View para criar uma nova família manualmente."""
    model = Familia
    form_class = FamiliaForm
    template_name = 'cecad/familia_form.html'
    
    def get_success_url(self):
        messages.success(self.request, f'Família {self.object.cod_familiar_fam} criada com sucesso!')
        return reverse('cecad_familia_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Criar validação automaticamente
        Validacao.objects.create(familia=self.object)
        return response


class FamiliaUpdateView(LoginRequiredMixin, UpdateView):
    """View para editar uma família existente."""
    model = Familia
    form_class = FamiliaForm
    template_name = 'cecad/familia_form.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Família atualizada com sucesso!')
        return reverse('cecad_familia_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context


class FamiliaDeleteView(LoginRequiredMixin, DeleteView):
    """View para deletar uma família."""
    model = Familia
    template_name = 'cecad/familia_confirm_delete.html'
    success_url = reverse_lazy('cecad_familia_list')
    
    def delete(self, request, *args, **kwargs):
        familia = self.get_object()
        cod = familia.cod_familiar_fam
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Família {cod} excluída com sucesso!')
        return response


# ============================================
# CRUD DE PESSOA (nested dentro de Família)
# ============================================

class PessoaCreateView(LoginRequiredMixin, CreateView):
    """View para adicionar um membro a uma família."""
    model = Pessoa
    form_class = PessoaForm
    template_name = 'cecad/pessoa_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.familia = get_object_or_404(Familia, pk=kwargs['familia_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['familia'] = self.familia
        return kwargs
    
    def form_valid(self, form):
        form.instance.familia = self.familia
        response = super().form_valid(form)
        messages.success(self.request, f'Membro {self.object.nom_pessoa} adicionado com sucesso!')
        return response
    
    def get_success_url(self):
        return reverse('cecad_familia_detail', kwargs={'pk': self.familia.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['familia'] = self.familia
        return context


class PessoaUpdateView(LoginRequiredMixin, UpdateView):
    """View para editar um membro da família."""
    model = Pessoa
    form_class = PessoaForm
    template_name = 'cecad/pessoa_form.html'
    
    def get_object(self):
        """Override to get pessoa by pk from URL kwargs."""
        familia_pk = self.kwargs.get('familia_pk')
        pessoa_pk = self.kwargs.get('pk')
        return get_object_or_404(Pessoa, pk=pessoa_pk, familia_id=familia_pk)
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.familia = self.object.familia
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['familia'] = self.familia
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Membro atualizado com sucesso!')
        return response
    
    def get_success_url(self):
        return reverse('cecad_familia_detail', kwargs={'pk': self.familia.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['familia'] = self.familia
        context['is_update'] = True
        return context


class PessoaDeleteView(LoginRequiredMixin, DeleteView):
    """View para remover um membro da família."""
    model = Pessoa
    template_name = 'cecad/pessoa_confirm_delete.html'
    
    def get_object(self):
        """Override to get pessoa by pk from URL kwargs."""
        familia_pk = self.kwargs.get('familia_pk')
        pessoa_pk = self.kwargs.get('pk')
        return get_object_or_404(Pessoa, pk=pessoa_pk, familia_id=familia_pk)
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.familia = self.object.familia
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('cecad_familia_detail', kwargs={'pk': self.familia.pk})
    
    def delete(self, request, *args, **kwargs):
        pessoa = self.get_object()
        nome = pessoa.nom_pessoa
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Membro {nome} removido com sucesso!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['familia'] = self.familia
        return context


# ============================================
# DETALHE DA PESSOA (com histórico de transferências)
# ============================================
class PessoaDetailView(LoginRequiredMixin, DetailView):
    model = Pessoa
    template_name = 'cecad/pessoa_detail.html'
    context_object_name = 'pessoa'

    def get_object(self):
        familia_pk = self.kwargs.get('familia_pk')
        pessoa_pk = self.kwargs.get('pk')
        return get_object_or_404(Pessoa, pk=pessoa_pk, familia_id=familia_pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pessoa = self.object
        # Histórico de transferências mais recentes
        transferencias = pessoa.transferencias.select_related('origem', 'destino', 'usuario').all()
        context['transferencias'] = transferencias
        context['familia'] = pessoa.familia
        return context

# ============================================
# TRANSFERÊNCIA DE PESSOA ENTRE FAMÍLIAS
# ============================================

class PessoaTransferStartView(LoginRequiredMixin, View):
    template_name = 'cecad/pessoa_transfer_start.html'

    def get(self, request, familia_pk, pessoa_pk):
        familia = get_object_or_404(Familia, pk=familia_pk)
        pessoa = get_object_or_404(Pessoa, pk=pessoa_pk, familia=familia)
        q = request.GET.get('q', '').strip()

        context = {
            'familia': familia,
            'pessoa': pessoa,
            'familia_form': FamiliaForm(),
            'q': q,
        }

        # Pré-carregar resultados de famílias se houver busca na URL
        if q:
            familias = Familia.objects.all().order_by('-updated_at')
            if q.isdigit() and len(q) == 11:
                familias = familias.filter(
                    Q(cod_familiar_fam=q) |
                    Q(membros__num_nis_pessoa_atual=q)
                ).distinct()
            else:
                familias = familias.filter(
                    Q(cod_familiar_fam__icontains=q) |
                    Q(membros__nom_pessoa__icontains=q) |
                    Q(membros__num_nis_pessoa_atual__icontains=q)
                ).distinct()

            familias = familias.exclude(pk=familia.pk)
            paginator = Paginator(familias, 10)
            page_obj = paginator.get_page(request.GET.get('page'))
            context['familias'] = page_obj
            context['pessoa_pk'] = pessoa.pk

        return render(request, self.template_name, context)


class PessoaTransferExistingSearchView(LoginRequiredMixin, View):
    template_name = 'cecad/pessoa_transfer_existing_results.html'

    def get(self, request, pessoa_pk):
        q = request.GET.get('q', '').strip()
        exclude_familia_id = request.GET.get('exclude')

        familias = Familia.objects.all().order_by('-updated_at')
        if q:
            if q.isdigit() and len(q) == 11:
                familias = familias.filter(
                    Q(cod_familiar_fam=q) |
                    Q(membros__num_nis_pessoa_atual=q)
                ).distinct()
            else:
                familias = familias.filter(
                    Q(cod_familiar_fam__icontains=q) |
                    Q(membros__nom_pessoa__icontains=q) |
                    Q(membros__num_nis_pessoa_atual__icontains=q)
                ).distinct()
        if exclude_familia_id:
            familias = familias.exclude(pk=exclude_familia_id)

        paginator = Paginator(familias, 10)
        page_obj = paginator.get_page(request.GET.get('page'))

        return render(request, self.template_name, {
            'familias': page_obj,
            'q': q,
            'pessoa_pk': pessoa_pk,
        })


class PessoaTransferCreateFamilyView(LoginRequiredMixin, CreateView):
    model = Familia
    form_class = FamiliaForm
    template_name = 'cecad/pessoa_transfer_new_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.pessoa = get_object_or_404(Pessoa, pk=kwargs['pessoa_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('cecad_pessoa_transfer_confirm', kwargs={
            'pessoa_pk': self.pessoa.pk,
            'dest_familia_pk': self.object.pk
        })

    def form_valid(self, form):
        # Sempre vincular ao último lote importado (status concluído)
        last_batch = ImportBatch.objects.filter(status='completed').first()
        form.instance.import_batch = last_batch
        response = super().form_valid(form)
        messages.success(self.request, f'Família {self.object.cod_familiar_fam} criada e vinculada ao último lote.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pessoa'] = self.pessoa
        return context


class PessoaTransferConfirmView(LoginRequiredMixin, View):
    template_name = 'cecad/pessoa_transfer_confirm.html'

    def get(self, request, pessoa_pk, dest_familia_pk):
        pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
        dest_familia = get_object_or_404(Familia, pk=dest_familia_pk)
        if pessoa.familia_id == dest_familia.pk:
            messages.error(request, 'A família de destino é a mesma família atual.')
            return redirect('cecad_familia_detail', pk=pessoa.familia_id)

        # Default do parentesco ao mover: "Não Parente" (11)
        parentesco_choices = Pessoa._meta.get_field('cod_parentesco_rf_pessoa').choices
        return render(request, self.template_name, {
            'pessoa': pessoa,
            'dest_familia': dest_familia,
            'parentesco_choices': parentesco_choices,
        })

    def post(self, request, pessoa_pk, dest_familia_pk):
        pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
        dest_familia = get_object_or_404(Familia, pk=dest_familia_pk)
        if pessoa.familia_id == dest_familia.pk:
            return HttpResponseBadRequest('Família de destino inválida.')

        try:
            novo_parentesco = int(request.POST.get('cod_parentesco_rf_pessoa', '11'))
        except ValueError:
            novo_parentesco = 11

        # Validar conflito de NIS no destino
        if Pessoa.objects.filter(familia=dest_familia, num_nis_pessoa_atual=pessoa.num_nis_pessoa_atual).exists():
            messages.error(request, 'Já existe uma pessoa com este NIS na família de destino.')
            return redirect('cecad_pessoa_transfer_confirm', pessoa_pk=pessoa.pk, dest_familia_pk=dest_familia.pk)

        # Validar RF duplicado se escolher 1
        if novo_parentesco == 1 and Pessoa.objects.filter(familia=dest_familia, cod_parentesco_rf_pessoa=1).exists():
            messages.error(request, 'A família de destino já possui um Responsável Familiar.')
            return redirect('cecad_pessoa_transfer_confirm', pessoa_pk=pessoa.pk, dest_familia_pk=dest_familia.pk)

        origem_familia = pessoa.familia

        # Executar transferência
        pessoa.familia = dest_familia
        pessoa.cod_parentesco_rf_pessoa = novo_parentesco
        pessoa.save(update_fields=['familia', 'cod_parentesco_rf_pessoa', 'updated_at'])

        # Registrar histórico de transferência
        try:
            from .models import PessoaTransferHistory
            PessoaTransferHistory.objects.create(
                pessoa=pessoa,
                origem=origem_familia,
                destino=dest_familia,
                usuario=request.user if request.user.is_authenticated else None,
            )
        except Exception:
            # Evitar quebrar o fluxo caso algo saia errado no histórico
            pass

        messages.success(request, f"{pessoa.nom_pessoa} transferido(a) para a família {dest_familia.cod_familiar_fam}.")
        return redirect('cecad_familia_detail', pk=dest_familia.pk)

