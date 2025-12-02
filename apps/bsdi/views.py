from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.db import transaction

from .models import BSDIExportacao
from .services import BSDIExporter


@method_decorator(login_required, name='dispatch')
class ExportacaoListView(ListView):
    """Lista todas as exportações BSDI realizadas."""
    
    model = BSDIExportacao
    template_name = 'bsdi/exportacao_list.html'
    context_object_name = 'exportacoes'
    paginate_by = 20
    
    def get_queryset(self):
        return BSDIExportacao.objects.select_related(
            'import_batch', 'gerado_por'
        ).order_by('-criado_em')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Verificar se existe batch para exportar
        from apps.cecad.models import ImportBatch
        ultimo_batch = ImportBatch.objects.filter(
            status='completed'
        ).order_by('-imported_at').first()
        
        context['ultimo_batch'] = ultimo_batch
        context['pode_exportar'] = bool(ultimo_batch)
        
        return context


@login_required
def gerar_exportacao(request):
    """Gera uma nova exportação BSDI."""
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('bsdi:exportacao_list')
    
    exportacao = None
    
    try:
        # Inicializar exportador primeiro para validar batch
        exporter = BSDIExporter()
        
        with transaction.atomic():
            # Criar registro de exportação com batch já definido
            exportacao = BSDIExportacao.objects.create(
                import_batch=exporter.import_batch,
                gerado_por=request.user,
                status='processando'
            )
            
            # Gerar arquivo
            content_file, nome_arquivo, total = exporter.gerar_arquivo()
            
            # Salvar arquivo
            exportacao.arquivo.save(nome_arquivo, content_file, save=False)
            exportacao.total_beneficiarios = total
            exportacao.status = 'concluido'
            exportacao.descricao = f'Lista gerada do lote #{exportacao.import_batch.pk}'
            exportacao.save()
            
            messages.success(
                request,
                f'Lista BSDI gerada com sucesso! {total} beneficiários exportados.'
            )
            
            # Redirecionar para download
            return redirect('bsdi:exportacao_download', pk=exportacao.pk)
            
    except ValueError as e:
        messages.error(request, f'Erro ao gerar exportação: {str(e)}')
        if exportacao:
            exportacao.status = 'erro'
            exportacao.mensagem_erro = str(e)
            exportacao.save()
    except Exception as e:
        messages.error(request, f'Erro inesperado ao gerar exportação: {str(e)}')
        if exportacao:
            exportacao.status = 'erro'
            exportacao.mensagem_erro = str(e)
            exportacao.save()
    
    return redirect('bsdi:exportacao_list')


@login_required
def download_exportacao(request, pk):
    """Faz download de uma exportação existente."""
    
    exportacao = get_object_or_404(BSDIExportacao, pk=pk)
    
    if not exportacao.arquivo:
        raise Http404("Arquivo não encontrado")
    
    # Retornar arquivo para download
    response = FileResponse(
        exportacao.arquivo.open('rb'),
        as_attachment=True,
        filename=exportacao.arquivo.name.split('/')[-1]
    )
    
    return response
