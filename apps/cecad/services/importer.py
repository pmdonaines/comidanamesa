import csv
import logging
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils.dateparse import parse_date
from apps.cecad.models import Familia, Pessoa, ImportBatch
from apps.core.models import Validacao

logger = logging.getLogger(__name__)

class CecadImporter:
    def __init__(self, file_path, import_batch, correction_mode=False):
        self.file_path = file_path
        self.import_batch = import_batch
        self.correction_mode = correction_mode

    def run(self):
        """Executa a importação do arquivo CSV."""
        try:
            self.import_batch.status = 'processing'
            self.import_batch.processed_rows = 0
            self.import_batch.save()

            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                # Count total rows first
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                    dialect.delimiter = ';'
                
                # Count rows
                reader = csv.DictReader(f, dialect=dialect)
                total_rows = sum(1 for _ in reader)
                self.import_batch.total_rows = total_rows
                self.import_batch.save()
                
                # Reset file pointer for actual processing
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)
                
                # Process rows - each row in its own transaction for real-time progress
                for idx, row in enumerate(reader, 1):
                    # Each row is processed atomically (Familia + Pessoa + Validacao together)
                    with transaction.atomic():
                        self._process_row(row)
                    
                    self.import_batch.processed_rows = idx
                    # Save progress every 10 rows to reduce DB writes
                    # This is OUTSIDE the transaction so it's immediately visible to polling
                    if idx % 10 == 0 or idx == total_rows:
                        self.import_batch.save(update_fields=['processed_rows'])
            
            self.import_batch.status = 'completed'
            self.import_batch.save()
            return True, "Importação concluída com sucesso."
        except Exception as e:
            self.import_batch.status = 'error'
            self.import_batch.error_message = str(e)
            self.import_batch.save()
            logger.error(f"Erro na importação: {e}")
            return False, str(e)

    def _process_row(self, row):
        """Processa uma linha do CSV e cria/atualiza Família e Pessoa."""
        # Dados da Família (Prefix d.)
        cod_familiar = row.get('d.cod_familiar_fam')
        if not cod_familiar:
            return

        if self.correction_mode:
            # Correction Mode: Update only specific fields for existing families
            try:
                # Find the latest full import batch to target
                latest_full_batch = ImportBatch.objects.filter(status='completed', batch_type='full').first()
                
                if latest_full_batch:
                    familia = Familia.objects.get(cod_familiar_fam=cod_familiar, import_batch=latest_full_batch)
                else:
                    # Fallback or skip if no full batch exists (shouldn't happen in normal flow)
                    return
                
                # Update fields
                familia.ref_cad = row.get('d.ref_cad')
                familia.ref_pbf = row.get('d.ref_pbf')
                familia.marc_pbf = self._parse_boolean(row.get('d.marc_pbf'))
                
                qtde_pessoas = self._parse_int(row.get('d.qtd_pessoas_domic_fam'))
                if qtde_pessoas is not None:
                    familia.qtde_pessoas = qtde_pessoas
                
                familia.save(update_fields=['ref_cad', 'ref_pbf', 'marc_pbf', 'qtde_pessoas'])
                
                # Link to this batch for tracking, but don't change ownership if not needed
                # Ideally we might want to track that this batch touched this family
                # For now, we just update the fields.
                
            except Familia.DoesNotExist:
                # If family doesn't exist, we skip it in correction mode
                pass
            return

        dat_atual = self._parse_date(row.get('d.dat_atual_fam'))
        renda_media = self._parse_decimal(row.get('d.vlr_renda_media_fam'))
        renda_total = self._parse_decimal(row.get('d.vlr_renda_total_fam'))
        
        familia, created = Familia.objects.update_or_create(
            cod_familiar_fam=cod_familiar,
            import_batch=self.import_batch,
            defaults={
                'dat_atual_fam': dat_atual or datetime.now().date(),
                'vlr_renda_media_fam': renda_media,
                'vlr_renda_total_fam': renda_total,
                'marc_pbf': self._parse_boolean(row.get('d.marc_pbf')),
                'ref_cad': row.get('d.ref_cad'),
                'ref_pbf': row.get('d.ref_pbf'),
                'qtde_pessoas': self._parse_int(row.get('d.qtd_pessoas_domic_fam')) or 0,
                'nom_logradouro_fam': row.get('d.nom_logradouro_fam', ''),
                'num_logradouro_fam': row.get('d.num_logradouro_fam', ''),
                'nom_localidade_fam': row.get('d.nom_localidade_fam', ''),
                'num_cep_logradouro_fam': row.get('d.num_cep_logradouro_fam', ''),
            }
        )

        if created:
            Validacao.objects.create(familia=familia)

        # Dados da Pessoa (Prefix p.)
        nis = row.get('p.num_nis_pessoa_atual')
        if nis:
            cpf = row.get('p.num_cpf_pessoa')
            # Ensure empty CPF is treated as None to avoid unique constraint violation
            if not cpf or not cpf.strip():
                cpf = None
            
            Pessoa.objects.update_or_create(
                num_nis_pessoa_atual=nis,
                familia=familia,
                defaults={
                    'nom_pessoa': row.get('p.nom_pessoa', ''),
                    'num_cpf_pessoa': cpf,
                    'dat_nasc_pessoa': self._parse_date(row.get('p.dta_nasc_pessoa')),
                    'cod_sexo_pessoa': row.get('p.cod_sexo_pessoa', '2'),
                    'cod_parentesco_rf_pessoa': self._parse_int(row.get('p.cod_parentesco_rf_pessoa')) or 1,
                    'cod_curso_frequentou_pessoa_membro': self._parse_int(row.get('p.cod_curso_frequentou_pessoa_memb')),
                    'cod_ano_serie_frequentou_pessoa_membro': self._parse_int(row.get('p.cod_ano_serie_frequentou_memb')),
                }
            )

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            # Tenta formato DD/MM/YYYY
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            try:
                # Tenta formato ISO YYYY-MM-DD
                return parse_date(date_str)
            except:
                return None

    def _parse_decimal(self, value):
        if not value:
            return Decimal('0.00')
        try:
            return Decimal(value.replace(',', '.'))
        except:
            return Decimal('0.00')

    def _parse_int(self, value):
        if not value:
            return None
        try:
            return int(value)
        except:
            return None
    
    def _parse_boolean(self, value):
        """Parse boolean fields that may come as '1', '0', '1 - Sim', '0 - Nao', etc."""
        if not value:
            return False
        # Extract first character and check if it's '1'
        return str(value).strip()[0] == '1'
