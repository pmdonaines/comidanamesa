from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.cecad.models import ImportBatch, Familia, Pessoa
from apps.cecad.services.importer import CecadImporter
import os

class CecadVersioningTest(TestCase):
    def setUp(self):
        self.csv_content_v1 = """d.cod_familiar_fam;d.dat_atual_fam;d.vlr_renda_media_fam;d.vlr_renda_total_fam;d.marc_pbf;d.qtde_pessoas_domic_fam;d.nom_logradouro_fam;d.num_logradouro_fam;d.nom_localidade_fam;d.num_cep_logradouro_fam;p.num_nis_pessoa_atual;p.nom_pessoa;p.num_cpf_pessoa;p.dta_nasc_pessoa;p.cod_parentesco_rf_pessoa;p.cod_curso_frequentou_pessoa_memb;p.cod_ano_serie_frequentou_memb
12345678901;01/01/2024;100,00;200,00;1;2;Rua A;10;Centro;12345000;12345678901;Joao Silva;11122233344;01/01/1980;1;;
12345678901;01/01/2024;100,00;200,00;1;2;Rua A;10;Centro;12345000;12345678902;Maria Silva;22233344455;01/01/1985;2;;
"""
        self.csv_content_v2 = """d.cod_familiar_fam;d.dat_atual_fam;d.vlr_renda_media_fam;d.vlr_renda_total_fam;d.marc_pbf;d.qtde_pessoas_domic_fam;d.nom_logradouro_fam;d.num_logradouro_fam;d.nom_localidade_fam;d.num_cep_logradouro_fam;p.num_nis_pessoa_atual;p.nom_pessoa;p.num_cpf_pessoa;p.dta_nasc_pessoa;p.cod_parentesco_rf_pessoa;p.cod_curso_frequentou_pessoa_memb;p.cod_ano_serie_frequentou_memb
12345678901;01/02/2024;150,00;300,00;1;2;Rua A;10;Centro;12345000;12345678901;Joao Silva;11122233344;01/01/1980;1;;
12345678901;01/02/2024;150,00;300,00;1;2;Rua A;10;Centro;12345000;12345678902;Maria Silva;22233344455;01/01/1985;2;;
"""
        self.file_path_v1 = '/tmp/test_import_v1.csv'
        self.file_path_v2 = '/tmp/test_import_v2.csv'
        
        with open(self.file_path_v1, 'w') as f:
            f.write(self.csv_content_v1)
            
        with open(self.file_path_v2, 'w') as f:
            f.write(self.csv_content_v2)

    def tearDown(self):
        if os.path.exists(self.file_path_v1):
            os.remove(self.file_path_v1)
        if os.path.exists(self.file_path_v2):
            os.remove(self.file_path_v2)

    def test_import_versioning(self):
        # Import Batch 1
        batch1 = ImportBatch.objects.create(description="Batch 1")
        importer1 = CecadImporter(self.file_path_v1, batch1)
        success1, _ = importer1.run()
        self.assertTrue(success1)
        
        # Verify Batch 1 Data
        self.assertEqual(Familia.objects.filter(import_batch=batch1).count(), 1)
        self.assertEqual(Pessoa.objects.filter(import_batch=batch1).count(), 2)
        fam1 = Familia.objects.get(import_batch=batch1, cod_familiar_fam='12345678901')
        self.assertEqual(fam1.vlr_renda_media_fam, 100.00)

        # Import Batch 2
        batch2 = ImportBatch.objects.create(description="Batch 2")
        importer2 = CecadImporter(self.file_path_v2, batch2)
        success2, _ = importer2.run()
        self.assertTrue(success2)
        
        # Verify Batch 2 Data
        self.assertEqual(Familia.objects.filter(import_batch=batch2).count(), 1)
        self.assertEqual(Pessoa.objects.filter(import_batch=batch2).count(), 2)
        fam2 = Familia.objects.get(import_batch=batch2, cod_familiar_fam='12345678901')
        self.assertEqual(fam2.vlr_renda_media_fam, 150.00)

        # Verify Independence
        self.assertNotEqual(fam1.pk, fam2.pk)
        self.assertEqual(Familia.objects.count(), 2)
