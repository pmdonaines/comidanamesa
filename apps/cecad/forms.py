from django import forms
from django.core.exceptions import ValidationError
from apps.cecad.models import Familia, Pessoa
from datetime import date


class FamiliaForm(forms.ModelForm):
    """Formulário para criação e edição de Família."""
    
    class Meta:
        model = Familia
        fields = [
            'import_batch',
            'cod_familiar_fam',
            'dat_atual_fam',
            'vlr_renda_media_fam',
            'vlr_renda_total_fam',
            'marc_pbf',
            'ref_cad',
            'ref_pbf',
            'qtde_pessoas',
            'nom_logradouro_fam',
            'num_logradouro_fam',
            'nom_localidade_fam',
            'num_cep_logradouro_fam',
        ]
        widgets = {
            'import_batch': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
            }),
            'cod_familiar_fam': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 12345678901',
                'maxlength': '11',
            }),
            'dat_atual_fam': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
            }),
            'vlr_renda_media_fam': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 218.00',
                'step': '0.01',
            }),
            'vlr_renda_total_fam': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 500.00',
                'step': '0.01',
            }),
            'marc_pbf': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500',
            }),
            'ref_cad': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Referência CadÚnico',
            }),
            'ref_pbf': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Referência Bolsa Família',
            }),
            'qtde_pessoas': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'min': '1',
            }),
            'nom_logradouro_fam': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: Rua das Flores',
            }),
            'num_logradouro_fam': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 123',
            }),
            'nom_localidade_fam': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: Centro',
            }),
            'num_cep_logradouro_fam': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 58970000',
                'maxlength': '8',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.cecad.models import ImportBatch
        # Seleciona apenas lotes concluídos e do tipo full
        latest_batch = ImportBatch.objects.filter(status='completed', batch_type='full').order_by('-imported_at').first()
        if latest_batch:
            self.fields['import_batch'].initial = latest_batch.pk
        self.fields['import_batch'].queryset = ImportBatch.objects.filter(status='completed', batch_type='full').order_by('-imported_at')
        self.fields['import_batch'].required = True
    
    def clean_cod_familiar_fam(self):
        """Valida o código familiar."""
        cod = self.cleaned_data.get('cod_familiar_fam')
        if cod and not cod.isdigit():
            raise ValidationError('O código familiar deve conter apenas números.')
        if cod and len(cod) != 11:
            raise ValidationError('O código familiar deve ter 11 dígitos.')
        return cod
    
    def clean_num_cep_logradouro_fam(self):
        """Valida o CEP."""
        cep = self.cleaned_data.get('num_cep_logradouro_fam')
        if cep and not cep.isdigit():
            raise ValidationError('O CEP deve conter apenas números.')
        if cep and len(cep) != 8:
            raise ValidationError('O CEP deve ter 8 dígitos.')
        return cep
    
    def clean_dat_atual_fam(self):
        """Valida a data de atualização."""
        data = self.cleaned_data.get('dat_atual_fam')
        if data and data > date.today():
            raise ValidationError('A data de atualização não pode ser futura.')
        return data


class PessoaForm(forms.ModelForm):
    """Formulário para criação e edição de Pessoa."""
    
    class Meta:
        model = Pessoa
        fields = [
            'num_nis_pessoa_atual',
            'nom_pessoa',
            'num_cpf_pessoa',
            'dat_nasc_pessoa',
            'cod_parentesco_rf_pessoa',
            'cod_sexo_pessoa',
            'cod_curso_frequentou_pessoa_membro',
            'cod_ano_serie_frequentou_pessoa_membro',
        ]
        widgets = {
            'num_nis_pessoa_atual': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 12345678901',
                'maxlength': '11',
            }),
            'nom_pessoa': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Nome completo',
            }),
            'num_cpf_pessoa': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ex: 12345678901',
                'maxlength': '11',
            }),
            'dat_nasc_pessoa': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
            }),
            'cod_parentesco_rf_pessoa': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
            }),
            'cod_sexo_pessoa': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
            }),
            'cod_curso_frequentou_pessoa_membro': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Código do curso',
            }),
            'cod_ano_serie_frequentou_pessoa_membro': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500',
                'placeholder': 'Ano/Série',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.familia = kwargs.pop('familia', None)
        super().__init__(*args, **kwargs)
    
    def clean_num_nis_pessoa_atual(self):
        """Valida o NIS."""
        nis = self.cleaned_data.get('num_nis_pessoa_atual')
        if nis and not nis.isdigit():
            raise ValidationError('O NIS deve conter apenas números.')
        if nis and len(nis) != 11:
            raise ValidationError('O NIS deve ter 11 dígitos.')
        
        # Verificar duplicidade dentro da mesma família
        if self.familia:
            qs = Pessoa.objects.filter(num_nis_pessoa_atual=nis, familia=self.familia)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe uma pessoa com este NIS nesta família.')
        
        return nis
    
    def clean_num_cpf_pessoa(self):
        """Valida o CPF."""
        cpf = self.cleaned_data.get('num_cpf_pessoa')
        if cpf:
            cpf = cpf.strip()
            if not cpf:
                return None
            if not cpf.isdigit():
                raise ValidationError('O CPF deve conter apenas números.')
            if len(cpf) != 11:
                raise ValidationError('O CPF deve ter 11 dígitos.')
        return cpf if cpf else None
    
    def clean_dat_nasc_pessoa(self):
        """Valida a data de nascimento."""
        data = self.cleaned_data.get('dat_nasc_pessoa')
        if data:
            if data > date.today():
                raise ValidationError('A data de nascimento não pode ser futura.')
            
            # Validar idade mínima (não pode ser nascido hoje)
            if data == date.today():
                raise ValidationError('A data de nascimento não pode ser hoje.')
            
            # Validar idade máxima razoável (ex: 150 anos)
            idade = date.today().year - data.year
            if idade > 150:
                raise ValidationError('Data de nascimento inválida (idade muito avançada).')
        
        return data
    
    def clean(self):
        """Validações cross-field."""
        cleaned_data = super().clean()
        parentesco = cleaned_data.get('cod_parentesco_rf_pessoa')
        
        # Verificar se já existe RF na família (apenas para novos membros ou se mudou o parentesco)
        if parentesco == 1 and self.familia:
            qs = Pessoa.objects.filter(familia=self.familia, cod_parentesco_rf_pessoa=1)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({
                    'cod_parentesco_rf_pessoa': 'Esta família já possui um Responsável Familiar.'
                })
        
        return cleaned_data
