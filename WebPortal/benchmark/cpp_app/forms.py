from django import forms

class CppCodeForm(forms.Form):
    cpp_code = forms.CharField(widget=forms.Textarea)
    identifier = forms.CharField(max_length=100)
