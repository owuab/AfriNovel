from django import forms

from .models import MonetizationConfig, WriterProfile


class WriterApplicationForm(forms.ModelForm):
    class Meta:
        model = WriterProfile
        fields = ['pen_name', 'bio']
        widgets = {'bio': forms.Textarea(attrs={'rows': 5})}


class WithdrawalRequestForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'inputmode': 'decimal'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        minimum = MonetizationConfig.objects.filter(pk=1).values_list('minimum_withdrawal', flat=True).first()
        if minimum is not None:
            self.fields['amount'].min_value = minimum
            self.fields['amount'].help_text = f'Minimum withdrawal: NGN {minimum:,.2f}'