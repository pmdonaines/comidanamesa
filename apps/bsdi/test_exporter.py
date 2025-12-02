"""
Script de teste para o módulo BSDI.

Este script demonstra como usar o exportador BSDI.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comidanamesa.settings')
django.setup()

from apps.bsdi.services import BSDIExporter
from apps.cecad.models import ImportBatch
from apps.core.models import Validacao

def test_bsdi_exporter():
    """Testa a geração de arquivo BSDI."""
    
    print("=== TESTE DO EXPORTADOR BSDI ===\n")
    
    # Verificar se há batches disponíveis
    ultimo_batch = ImportBatch.objects.filter(status='completed').order_by('-imported_at').first()
    
    if not ultimo_batch:
        print("❌ Nenhum lote de importação encontrado.")
        print("   Execute uma importação CECAD primeiro.\n")
        return
    
    print(f"✅ Último batch encontrado: #{ultimo_batch.pk}")
    print(f"   Data: {ultimo_batch.imported_at}")
    print(f"   Total de famílias: {ultimo_batch.familias.count()}\n")
    
    # Verificar validações aprovadas
    familias_aprovadas = ultimo_batch.familias.filter(
        validacoes__status='aprovado'
    ).distinct()
    
    total_aprovadas = familias_aprovadas.count()
    
    print(f"✅ Famílias aprovadas: {total_aprovadas}")
    
    if total_aprovadas == 0:
        print("   ⚠️  Nenhuma família aprovada encontrada.")
        print("   Execute validações e aprove algumas famílias primeiro.\n")
        return
    
    print("\n=== GERANDO ARQUIVO XLS ===\n")
    
    try:
        # Inicializar exportador
        exporter = BSDIExporter(import_batch=ultimo_batch)
        
        # Gerar arquivo
        content_file, nome_arquivo, total_beneficiarios = exporter.gerar_arquivo()
        
        print(f"✅ Arquivo gerado com sucesso!")
        print(f"   Nome: {nome_arquivo}")
        print(f"   Total de beneficiários: {total_beneficiarios}")
        print(f"   Tamanho: {len(content_file.read())} bytes\n")
        
        # Salvar arquivo de teste
        test_path = f'/tmp/{nome_arquivo}'
        with open(test_path, 'wb') as f:
            content_file.seek(0)
            f.write(content_file.read())
        
        print(f"✅ Arquivo salvo em: {test_path}")
        print(f"   Você pode abri-lo para verificar o conteúdo.\n")
        
    except Exception as e:
        print(f"❌ Erro ao gerar arquivo: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_bsdi_exporter()
