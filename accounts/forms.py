from django import forms
from .models import Bank, Client,AccountBank,Group,UserData , TaxSuspension,IncomeTaxReturn
from datetime import date, datetime

from django.db.models import Subquery, OuterRef

# Define AUDIT_STATUS_CHOICES if not imported from elsewhere
AUDIT_STATUS_CHOICES = [
    ('', 'Select Audit Status'),
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('not_required', 'Not Required'),
]

class GroupForm(forms.ModelForm):
    group_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    group_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-100'})
    )
    group_phno = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    suspend_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-100'})
    )

    class Meta:
        model = Group
        fields = ['group_name', 'group_email', 'group_phno', 'suspend_date']

    def clean_group_name(self):
        group_name = self.cleaned_data.get('group_name')
        if not group_name:
            raise forms.ValidationError("Group Name is required")
        
        queryset = Group.objects.filter(group_name=group_name)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise forms.ValidationError("This Group Name already exists. Please enter a unique name.")
        return group_name



class ClientForm(forms.ModelForm):
    it_audit = forms.ChoiceField(
        choices=AUDIT_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    client_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    client_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    legal_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    group_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={ "class": "form-select",
        "required": "required"})
    )
    dob = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': ' w-100'}),
        label="Date of Birth"
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': ' w-100', 'rows': 1})
    )
    other_info = forms.CharField(
        widget=forms.Textarea(attrs={'class': ' w-100', 'rows': 1}),
        required=False
    )
    pan = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': ' w-100'})
    )
    gst_no = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': ' w-100'})
    )
    mobile_no = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': ' w-100'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-100'})
    )
    file_no = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': ' w-100'})
    )
    busy_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': ' w-100'})
    )

     # Return Type Fields (new boolean fields)
    it_return = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Income Tax'
    )
    gst_return = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='GST'
    )
    tds_return = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='TDS'
    )
    tcs_return = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='TCS'
    )

    # GST Related Fields
    trade_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
     # GST Related Fields with updated widgets
    gst_scheme = forms.ChoiceField(
        choices=[('', 'Select GST Scheme')] + list(Client.GST_SCHEME_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select-md w-100',
        })
    )
    period = forms.ChoiceField(
        choices=[('', 'Select Filing Period')] + list(Client.PERIOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select-md w-100',
        })
    )
    reg_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'w-100', 'type': 'date'})
    )
    cancel_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'w-100', 'type': 'date'})
    )
    status = forms.ChoiceField(
        choices=[('', 'Select Status')] + list(Client.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select-md w-100',
        })
    )
    user_id = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-100'})
    )
    gst_data = forms.ChoiceField(
        choices=[('', 'Select Accounting Software')] + list(Client.ACCOUNTING_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select-md w-100',
        })
    )
    sale_define = forms.ChoiceField(
        choices=[('', 'Select Sales Defined')] + list(Client.SALE_DEFINE_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select-md w-100',
        })
    )
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),  # Start with empty queryset
        required=False,
        widget=forms.Select(attrs={'class': 'form-select-md w-100'}),
         empty_label="Select Bank Account"
    )
    suspend_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': ' w-100'}),
        label="Suspend Date"
    )

    extra_emails = forms.CharField(
        required=False,
        label="Extra Emails",
        help_text="Add multiple emails; press Enter after each. (They’ll be saved as a list.)",
                widget=forms.TextInput(attrs={"id": "extra-emails", "class": "w-100"})

    )

    def clean_return_types(self):
        return ",".join(self.cleaned_data["return_types"])  # Convert list to CSV

    class Meta:
        model = Client
        fields = [
            'client_id','group', 'client_name', 'legal_name', 'group_name', 'address',
            'other_info', 'pan', 'gst_no', 'mobile_no', 'email', 'file_no',
            'busy_code',  'it_return', 'gst_return', 'tds_return', 'tcs_return','trade_name', 'gst_scheme', 'period',
            'reg_date', 'cancel_date', 'status', 'user_id', 'password',
            'gst_data', 'sale_define', 'bank','dob','suspend_date','it_alloted_to','audit_status','it_start_date',"extra_emails"
        ]
    it_alloted_to = forms.ModelChoiceField(queryset=UserData.objects.all(), required=False)
    it_start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    # it_audit = forms.BooleanField(required=False)
    audit_status = forms.ChoiceField(
    choices=[('', 'Select Audit Status')] + list(Client.AUDIT_STATUS_CHOICES),
    required=False,
    widget=forms.Select(attrs={'class': '-100'})
)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

         # 🔹 Make all fields optional by default
        for field in self.fields.values():
            field.required = False

        # 🔹 Only these fields are required
        self.fields["client_name"].required = True
        self.fields["pan"].required = True
        self.fields["group"].required = True   # IMPORTANT


         # Get all banks and filter unique names in Python
        all_banks = Bank.objects.all().order_by('bank_name', 'id')
        unique_banks = []
        seen_names = set()
        
        for bank in all_banks:
            if bank.bank_name not in seen_names:
                unique_banks.append(bank)
                seen_names.add(bank.bank_name)
        
        # Set the queryset
        self.fields['bank'].queryset = Bank.objects.filter(
            id__in=[b.id for b in unique_banks]
        ).order_by('bank_name')
        
        # Include current bank if editing
        if self.instance and self.instance.bank and self.instance.bank.bank_name not in seen_names:
            self.fields['bank'].queryset = self.fields['bank'].queryset | Bank.objects.filter(id=self.instance.bank.id)

    def clean_group(self):
        group = self.cleaned_data.get("group")

        if not group:
            raise forms.ValidationError("Group is required. Please create/select a group first.")

        return group

    def clean_user_id(self):
        user_id = self.cleaned_data.get("user_id", "").strip()

        # ✅ If empty, just return empty (skip uniqueness check)
        if not user_id:
            return None  

        # ✅ Only check uniqueness if user_id is actually filled
        qs = Client.objects.filter(user_id=user_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)  # allow same value for current client in modify mode

        if qs.exists():
            raise forms.ValidationError("This User ID is already used by another client.")
        return user_id


    def save(self, commit=True):
        instance = super().save(commit=False)
        
                
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance

class AccountForm(forms.ModelForm):
    # account_id = forms.CharField(max_length=20, required=True)
    # account_id = forms.IntegerField(required=False, disabled=True)
    account_id = forms.CharField(required=False, disabled=True)

    class Meta:
        model = AccountBank
        exclude = ['client_name']  # Assuming you calculate or store this manually

        widgets = {
            # 'account_group': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_account_group'}),
            "account_group": forms.Select(attrs={"class": "form-select"}), 
            'acc_mail_id': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_acc_mail_id'}),
            'account': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_account_name'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_bank_name'}),
            'branch': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_branch'}),
            'account_no': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_account_no'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_ifsc_code'}),
            'acc_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_acc_type'}),  # ✅ dropdown
            'data_entry': forms.Select(attrs={'class': 'form-select', 'id': 'id_data_entry'}),  # ✅ dropdown
            'full_match': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_full_match'}),
            'e_statement': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_e_statement'}),
            'two_match': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_two_match'}),  # ✅ plain input
            'contact_no': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contact_no'}),
            'pw': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_pw'}),
            'stms_pws': forms.TextInput(attrs={'class': 'form-control', 'id': 'stms_pws'}),
            'client': forms.Select(attrs={'class': 'form-select', 'id': 'id_client'}),
             'closing_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_closing_date'}),
            'bank_mail_id': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_bank_mail_id'}),
            'branch_mail_id': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_branch_mail_id'}),
            'branch_mobile_no': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_branch_mobile_no'}),
            'statement_frequency': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_statement_frequency'}),
            'reminder_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_reminder_date'}),
            'cif_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cif_number'}),
            'busyacccode': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_busyacccode'}),


        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

          # ✅ Make everything NOT required first
        for field in self.fields:
            self.fields[field].required = False

        # ✅ ONLY THESE ARE REQUIRED
        self.fields['client'].required = True
        self.fields['account'].required = True

        # Client dropdown display
        self.fields['client'].queryset = Client.objects.all()
        self.fields['client'].to_field_name = 'client_id'
        self.fields['client'].label_from_instance = lambda obj: f"{obj.client_name} (ID: {obj.client_id})"

    def save(self, commit=True):
        instance = super().save(commit=False)

        # ✅ Auto-generate ONLY for new account
        if not instance.pk:
            last = AccountBank.objects.order_by('-id').values_list('account_id', flat=True).first()

            if last and last.isdigit():
                instance.account_id = int(last) + 1
            else:
                instance.account_id = 1

        if commit:
            instance.save()
            self.save_m2m()

        return instance


from django import forms
from .models import DataEntry


from django.db.models import Q


from django import forms

class DataEntryForm(forms.ModelForm):
    class Meta:
        model = DataEntry
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alloted_to'].required = False  # 👈 Make not required in form
        # Build dynamic account choices
        account_choices = [
            ('1', 'Sales (Default)'),
            ('2', 'Purchase (Default)'),
        ]
        

        # Add real account entries from DB
        account_objs = AccountBank.objects.all().select_related('client')
        for obj in account_objs:
            label = f"{obj.account} (Bank: {obj.bank_name or 'N/A'})"
            account_choices.append((str(obj.id), label))

        # Override `account` field to use ChoiceField instead of ModelChoiceField
        self.fields['account'] = forms.ChoiceField(choices=account_choices, required=True)

        # self.fields['alloted_to'].required = True
        
        self.fields['client'] = forms.ModelChoiceField(
             queryset=Client.objects.all(),
             to_field_name='client_id',   # <== This is what tells Django to match on 'client_id'
             required=True,
         )
        self.fields['client'].label_from_instance = lambda obj: f"{obj.client_name} (ID: {obj.client_id})"

        self.fields['alloted_to'].queryset = UserData.objects.all()
        self.fields['alloted_to'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username}"
    
    def clean(self):
        cleaned_data = super().clean()
        account_id = cleaned_data.get('account')
        client = cleaned_data.get('client')

        if account_id in ['1', '2']:
            # Default accounts (Sales/Purchase) - these don't need a client
            cleaned_data['account'] = None
            # Remove client requirement for default accounts
            if 'client' in self.errors:
                del self.errors['client']
        else:
            try:
                account_obj = AccountBank.objects.get(id=account_id)
                cleaned_data['account'] = account_obj
                # Only require client for non-default accounts
                if not client:
                    self.add_error('client', 'Client is required for non-default accounts.')
            except AccountBank.DoesNotExist:
                self.add_error('account', 'Selected account does not exist.')

        return cleaned_data


        
class UserForm(forms.ModelForm):
    class Meta:
        model = UserData
        fields = ['username', 'password', 'in_date', 'out_date']
        widgets = {
            'password': forms.PasswordInput(render_value=True),  # Shows the actual value (plain text)
            'in_date': forms.DateInput(attrs={'type': 'date'}),
            'out_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an existing instance, show the plain text password
        if self.instance and self.instance.pk:
            self.initial['password'] = self.instance.password

from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=True
    )



class TaxSuspensionForm(forms.ModelForm):
    class Meta:
        model = TaxSuspension
        fields = [
            'group',
            'client',
            'account',
            'tax_type',
            'from_date',
            'to_date',
            'remarks'
        ]
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'to_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'group': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'tax_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        group = cleaned_data.get('group')
        client = cleaned_data.get('client')
        account = cleaned_data.get('account')
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        # ✅ Ensure at least one entity selected
        if not (group or client or account):
            raise forms.ValidationError("Please select either a Group, Client, or Account.")

        # ✅ Ensure to_date is after from_date
        if to_date and from_date and to_date < from_date:
            raise forms.ValidationError("To Date cannot be earlier than From Date.")

        return cleaned_data
  
# def dynamic_fy_choices(start_year=2015):
#     today = date.today()
#     # April or later → current FY; else previous FY
#     end_year = today.year if today.month >= 4 else today.year - 1
#     return [(f"{y}-{str(y+1)[-2:]}", f"{y}-{str(y+1)[-2:]}") for y in range(start_year, end_year + 1)]
  

# def fy_to_start_date(fy_str: str):
#     """'2024-25' -> date(2024,4,1)"""
#     y = int(fy_str.split('-')[0])
#     return date(y, 4, 1)

# def date_to_fy_str(d: date):
#     """date(2024,4,1) -> '2024-25'"""
#     y = d.year
#     return f"{y}-{str(y+1)[-2:]}"

# class IncomeTaxReturnForm(forms.ModelForm):
#     class Meta:
#         model = IncomeTaxReturn
#         fields = '__all__'
#         widgets = {
#             'year': forms.DateInput(attrs={'type': 'date'}),
#             'audit_date': forms.DateInput(attrs={'type': 'date'}),
#             'ack_date': forms.DateInput(attrs={'type': 'date'}),
#             'verification_date': forms.DateInput(attrs={'type': 'date'}),
#             'audit_hold_reason': forms.Textarea(attrs={'rows': 2}),
#             'return_hold_reason': forms.Textarea(attrs={'rows': 2}),
            
#         }

#          # ✅ Add this block to fix client & alloted_to binding
#         def __init__(self, *args, **kwargs):
#             super().__init__(*args, **kwargs)
            
#             # ✅ Make CA field optional in form
#             self.fields['ca'].required = False
                
#               # Ensure valid choices always come from default DB
#             self.fields['client'].queryset = Client.objects.using('default').all().order_by('client_name')
#             self.fields['alloted_to'].queryset = UserData.objects.using('default').all().order_by('username')


# --- FY helpers ---
def dynamic_fy_choices(start_year=2015):
    today = date.today()
    end_year = today.year if today.month >= 4 else today.year - 1
    return [(f"{y}-{str(y+1)[-2:]}", f"{y}-{str(y+1)[-2:]}") for y in range(start_year, end_year + 1)]

def fy_to_start_date(fy_str: str):
    """'2024-25' -> date(2024, 4, 1)"""
    y = int(fy_str.split('-')[0])
    return date(y, 4, 1)

def date_to_fy_str(d: date):
    """date(2024, 4, 1) -> '2024-25'"""
    y = d.year
    return f"{y}-{str(y+1)[-2:]}"

class IncomeTaxReturnForm(forms.ModelForm):
    fy = forms.ChoiceField(choices=(), label="Financial Year *")

    class Meta:
        model = IncomeTaxReturn
        fields = [
            'client',
            'audit_applicable', 'ca',
            'audit_stage', 'audit_status', 'audit_hold_reason', 'audit_ack', 'audit_date',
            'return_type', 'revise_no',
            'alloted_to',
            'stage', 'return_status', 'return_hold_reason',
            'ack_no', 'ack_date', 'verification_date',
            'flag',
            'want_revised', 'revised_status',
            'want_rectified', 'rectification_status',
        ]
        widgets = {
            'audit_date': forms.DateInput(attrs={'type': 'date'}),
            'ack_date': forms.DateInput(attrs={'type': 'date'}),
            'verification_date': forms.DateInput(attrs={'type': 'date'}),
            'audit_hold_reason': forms.Textarea(attrs={'rows': 2}),
            'return_hold_reason': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.is_modify_mode = kwargs.pop('is_modify_mode', False)
        super().__init__(*args, **kwargs)

        # FY choices
        self.fields['fy'].choices = dynamic_fy_choices()
        if self.instance and getattr(self.instance, 'year', None):
            self.fields['fy'].initial = date_to_fy_str(self.instance.year)
        elif self.fields['fy'].choices:
            self.fields['fy'].initial = self.fields['fy'].choices[-1][0]

        self.fields['ca'].required = False
        self.fields['client'].queryset = Client.objects.using('default').all().order_by('client_name')
        self.fields['alloted_to'].queryset = UserData.objects.using('default').all().order_by('username')

        if not self.is_modify_mode:
            self.fields['return_type'].initial = 'Original'
            self.fields['return_type'].choices = [('Original', 'Original')]

        self.fields['revise_no'].widget = forms.NumberInput(attrs={'min': 1})

        # 🔑 Allow "Other…" in stage choices so validation accepts it
        if 'stage' in self.fields:
            stage_field = self.fields['stage']
            current = list(stage_field.choices)
            values = {v for v, _ in current}
            if '__other__' not in values:
                current.append(('__other__', 'Other…'))
                stage_field.choices = current
                stage_field.widget.choices = current  # keep widget in sync

    def clean(self):
        cleaned = super().clean()

        # enforce revise_no when needed
        rtype = cleaned.get('return_type')
        rno = cleaned.get('revise_no')
        if rtype in ('Revised', 'Rectified', 'Updated') and not rno:
            self.add_error('revise_no', 'Revise No is required for non-Original return types.')

        # 🔁 Map "Other…" to the typed value
        stage = cleaned.get('stage')
        if stage == '__other__':
            custom = (self.data.get('stage_other') or '').strip()
            if not custom:
                self.add_error('stage', 'Please specify the custom stage.')
            else:
                cleaned['stage'] = custom

        return cleaned

    def save(self, commit=True):
        fy_str = self.cleaned_data['fy']
        self.instance.year = fy_to_start_date(fy_str)
        return super().save(commit=commit)

# class IncomeTaxReturnForm(forms.ModelForm):
#     # UI field for FY; we’ll map to model.year in save()
#     fy = forms.ChoiceField(choices=(), label="Financial Year *")

#     class Meta:
#         model = IncomeTaxReturn
#         # EXCLUDE 'year' from the form; we set it from fy in save()
#         fields = [
#             'client',
#             'audit_applicable', 'ca',
#             'audit_stage', 'audit_status', 'audit_hold_reason', 'audit_ack', 'audit_date',
#             'return_type', 'revise_no',
#             'alloted_to',
#             'stage', 'return_status', 'return_hold_reason',
#             'ack_no', 'ack_date', 'verification_date',
#             "flag",
#             "want_revised", "revised_status",
#             "want_rectified", "rectification_status",
#         ]
#         widgets = {
#             'audit_date': forms.DateInput(attrs={'type': 'date'}),
#             'ack_date': forms.DateInput(attrs={'type': 'date'}),
#             'verification_date': forms.DateInput(attrs={'type': 'date'}),
#             'audit_hold_reason': forms.Textarea(attrs={'rows': 2}),
#             'return_hold_reason': forms.Textarea(attrs={'rows': 2}),
#         }

#     def __init__(self, *args, **kwargs):
#         # Pass is_modify_mode= True/False from the view
#         self.is_modify_mode = kwargs.pop('is_modify_mode', False)
#         super().__init__(*args, **kwargs)

#         # Dynamic FY choices
#         self.fields['fy'].choices = dynamic_fy_choices()

#         # Preselect fy when instance has a year
#         if self.instance and getattr(self.instance, 'year', None):
#             self.fields['fy'].initial = date_to_fy_str(self.instance.year)
#         else:
#             # default to the latest (last item)
#             if self.fields['fy'].choices:
#                 self.fields['fy'].initial = self.fields['fy'].choices[-1][0]

#         # Optional CA
#         self.fields['ca'].required = False

#         # FK querysets from default DB
#         self.fields['client'].queryset = Client.objects.using('default').all().order_by('client_name')
#         self.fields['alloted_to'].queryset = UserData.objects.using('default').all().order_by('username')

#         # Return type behavior
#         if not self.is_modify_mode:
#             # Add mode: lock to Original
#             self.fields['return_type'].initial = 'Original'
#             self.fields['return_type'].choices = [('Original', 'Original')]

#         # Revise no min
#         self.fields['revise_no'].widget = forms.NumberInput(attrs={'min': 1})

#     def clean(self):
#         cleaned = super().clean()
#         rtype = cleaned.get('return_type')
#         rno = cleaned.get('revise_no')
#         if rtype in ('Revised', 'Rectified', 'Updated') and not rno:
#             self.add_error('revise_no', 'Revise No is required for non-Original return types.')
#         return cleaned

#     def save(self, commit=True):
#         # Map fy -> model.year
#         fy_str = self.cleaned_data['fy']
#         self.instance.year = fy_to_start_date(fy_str)
#         return super().save(commit=commit)
    
    

class AISUploadForm(forms.Form):
    pdf_file = forms.FileField(label="Upload AIS PDF")
    password = forms.CharField(
        label="PDF Password",
        required=False,  # required only if PDF is locked
        widget=forms.PasswordInput
    )








