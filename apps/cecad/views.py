from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Familia, Pessoa, Beneficio, ImportBatch
from .services.importer import CecadImporter
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
        
        # Filter by batch if provided, otherwise latest
        batch_id = self.request.GET.get('batch')
        if batch_id:
            queryset = queryset.filter(import_batch_id=batch_id)
        else:
            latest_batch = ImportBatch.objects.filter(status='completed', batch_type='full').first()
            if latest_batch:
                queryset = queryset.filter(import_batch=latest_batch)
            else:
                queryset = queryset.none()

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
