from django import forms
from django.forms import inlineformset_factory
from .models import Deck, Problem, Solution, MarketAnalysis, TeamMember, FinancialProjection, FundingAsk, RegisteredUser
from django.contrib.auth.models import User

# Main Deck Form
class DeckForm(forms.ModelForm):
    class Meta:
        model = Deck
        fields = ['company_name', 'tagline', 'logo']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'Enter your company name'
            }),
            'tagline': forms.TextInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'Enter your company tagline'
            }),
            'logo': forms.ClearableFileInput(attrs={
                'class': 'hidden', 'id': 'fileInput'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make logo field not required
        self.fields['logo'].required = False

# One-to-one section forms
class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'h-80 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'Describe the problem your startup is solving...'
            }),
        }

class SolutionForm(forms.ModelForm):
    class Meta:
        model = Solution
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'h-80 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'Explain your solution...'
            }),
        }

class MarketAnalysisForm(forms.ModelForm):
    class Meta:
        model = MarketAnalysis
        fields = [
            'primary_market',
            'target_audience',
            'market_growth_rate',
            'competitive_advantage'
        ]
        widgets = {
            'primary_market': forms.TextInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'e.g. FinTech, HealthTech, etc.'
            }),
            'target_audience': forms.Textarea(attrs={
                'class': 'h-30 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'Describe your target audience...'
            }),
            'market_growth_rate': forms.NumberInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'e.g. 12.5',
                'step': '0.01',
                'min': '0'
            }),
            'competitive_advantage': forms.Textarea(attrs={
                'class': 'h-30 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'What makes your solution stand out?'
            }),
        }
    
    def clean_market_growth_rate(self):
        value = self.cleaned_data.get('market_growth_rate')
        if value is not None and value < 0:
            raise forms.ValidationError("Market growth rate cannot be negative.")
        return value

class FundingAskForm(forms.ModelForm):
    class Meta:
        model = FundingAsk
        fields = ['amount', 'usage_description']
        widgets = {
            'amount': forms.TextInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'e.g. 500000'
            }),
            'usage_description': forms.Textarea(attrs={
                'class': 'h-50 shadow-lg w-full rounded-lg bg-white p-3',
                'placeholder': 'Explain how the funds will be used...'
            }),
        }

# Inline formsets for one-to-many relationships; ideal for optional addition of team members and year projection
class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ['name', 'title']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3 mb-2',
                'placeholder': 'Name'
            }),
            'title': forms.TextInput(attrs={
                'class': 'h-12 shadow-lg w-full rounded-lg bg-white p-3 mb-2',
                'placeholder': 'Title'
            }),
        }

TeamMemberFormSet = inlineformset_factory(
    Deck, TeamMember,
    form=TeamMemberForm,
    extra=1,
    can_delete=True
)

class FinancialProjectionForm(forms.ModelForm):
    class Meta:
        model = FinancialProjection
        fields = ['valuation_multiple', 'current_valuation', 'projected_revenue_final_year', 'years_to_projection']
        widgets = {
            'valuation_multiple': forms.NumberInput(attrs={
                'class': 'p-2 bg-white rounded focus:outline-none focus:ring-2 focus:ring-gray-400 font-semibold',
                'placeholder': 'Valuation Multiple',
                'step': '0.01'
            }),
            'current_valuation': forms.NumberInput(attrs={
                'class': 'p-2 bg-white rounded focus:outline-none focus:ring-2 focus:ring-gray-400 font-semibold',
                'placeholder': 'Current Valuation',
                'step': '0.01'
            }),
            'projected_revenue_final_year': forms.NumberInput(attrs={
                'class': 'p-2 bg-white rounded focus:outline-none focus:ring-2 focus:ring-gray-400 font-semibold',
                'placeholder': 'Projected Revenue (Final Year)',
                'step': '0.01'
            }),
            'years_to_projection': forms.NumberInput(attrs={
                'class': 'p-2 bg-white rounded focus:outline-none focus:ring-2 focus:ring-gray-400 font-semibold',
                'placeholder': 'Years to Projection'
            }),
        }

FinancialProjectionFormSet = inlineformset_factory(
    Deck, FinancialProjection,
    form=FinancialProjectionForm,
    extra=1,
    can_delete=True
)

# Module 3 - Startup Registration

class RegistrationForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your first name'
    }))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your last name'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm your password'
    }))
    label = forms.CharField(max_length=50, required=False)
    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms of Service and Privacy Policy.'},
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password']
        )
        RegisteredUser.objects.create(
            user=user,
            label=self.cleaned_data.get('label')
        )
        return user
    
# Login Form
class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
        'placeholder': 'Enter your email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition',
        'placeholder': 'Enter your password'
    }))
