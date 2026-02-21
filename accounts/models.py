from django.db import models
from datetime import date  # Import date from datetime module
import json

import os
import re

def sanitize_name(name):
    """Remove problematic characters for folder/file names."""
    return re.sub(r'[^\w\-_\. ]', '_', name.strip())

from .utills import get_fiscal_year_from_date  # ✅ use your function
from uuid import uuid4
from django.conf import settings

def upload_to(instance, filename):
    from uuid import uuid4
    from datetime import date
    import os

    fiscal_base = instance.from_date or instance.last_date or date.today()
    fiscal_folder = f"fy_{get_fiscal_year_from_date(fiscal_base)}"

    client_part = instance.client.client_id.strip()

    # Determine the account folder
    if instance.account:
        account_part = instance.account.account_id.strip()
    elif instance.virtual_account_type == "1":
        account_part = "sale (1)"
    elif instance.virtual_account_type == "2":
        account_part = "purchase (2)"
    else:
        account_part = "unknown-account"

    # Temporary filename before renaming
    temp_name = f"TEMP_{uuid4().hex}_{filename}"

    # Build full relative path
    relative_path = os.path.join(fiscal_folder, client_part, account_part, temp_name)
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    return relative_path

from django.db import models
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# ---- shared helpers ----
def _normalize_email(e: str) -> str:
    e = (e or "").strip().lower()
    if not e:
        raise ValidationError("Empty email")
    validate_email(e)
    return e

def _normalize_list(emails):
    out = []
    seen = set()
    for e in (emails or []):
        try:
            n = _normalize_email(e)
        except ValidationError:
            continue
        if n not in seen:
            out.append(n)
            seen.add(n)
    return out


# Create your models here.
class Group(models.Model):
    # group_id=models.CharField(max_length=20, unique=True)
    group_name=models.CharField(max_length=100,unique=True)
    group_email=models.EmailField()
    group_phno=models.CharField(max_length=15)
    suspend_date = models.DateField(null=True, blank=True)  # Add this line
    # ✅ multiple emails container (no new table)
    extra_emails = models.JSONField(default=list, blank=True)  # requires MySQL 5.7.8+


      # limit if you want (primary + extras <= MAX)
    MAX_EMAILS = 10

    def clean(self):
        super().clean()
        if self.group_email:
            self.group_email = _normalize_email(self.group_email)
        self.extra_emails = _normalize_list(self.extra_emails)
        # cap total count if desired
        total = (1 if self.group_email else 0) + len(self.extra_emails or [])
        if total > self.MAX_EMAILS:
            raise ValidationError(f"Too many emails (max {self.MAX_EMAILS}).")

    @property
    def emails(self):
        """All unique emails: primary first, then extras."""
        base = [_normalize_email(self.group_email)] if self.group_email else []
        extras = [e for e in (self.extra_emails or []) if e not in base]
        return base + extras

    def add_email(self, email: str, make_primary: bool = False, save: bool = False):
        e = _normalize_email(email)
        emails = set(self.extra_emails or [])
        if make_primary or not self.group_email:
            # move old primary into extras
            if self.group_email and self.group_email != e:
                emails.add(self.group_email)
            self.group_email = e
            emails.discard(e)
        else:
            emails.add(e)
        self.extra_emails = sorted(emails)
        if save:
            self.full_clean()
            self.save(update_fields=["group_email", "extra_emails"])

    def remove_email(self, email: str, save: bool = False):
        e = (email or "").strip().lower()
        changed = False
        if self.group_email and self.group_email.lower() == e:
            self.group_email = None
            changed = True
        emails = set(self.extra_emails or [])
        if e in emails:
            emails.remove(e)
            changed = True
        if changed:
            self.extra_emails = sorted(emails)
            if save:
                self.save(update_fields=["group_email", "extra_emails"])

    def __str__(self):
        return self.group_name
  
class UserData(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # Storing plain text passwords
    in_date = models.DateField('Date In')
    out_date = models.DateField('Date Out', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

class Bank(models.Model):
    IFSC=models.CharField(max_length=20, unique=True)
    bank_name = models.CharField(max_length=100)
    branch_name = models.CharField(max_length=100)

    def __str__(self):
        return self.bank_name
    

class Client(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Cancelled', 'Cancelled'),
        ('Past', 'Past'),
    ]
    
    GST_SCHEME_CHOICES = [
        ('Regular', 'Regular'),
        ('Composition', 'Composition'),
       
    ]
    
    ACCOUNTING_CHOICES = [
        ('Direct', 'Direct'),
        ('Busy', 'Busy'),
       
    ]
    PERIOD_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
       
    ]

    SALE_DEFINE_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
       
    ]

    
    AUDIT_STATUS_CHOICES = [
        ('Not Applicable', 'Not Applicable'),
        ('Audit', 'Audit'),
        ('Audit as Partnership', 'Audit as Partnership'),
    ]

    client_id = models.CharField(max_length=20, unique=True)
  
    group = models.ForeignKey(
        Group,
        to_field='id',
        on_delete=models.CASCADE,
        related_name='clients',
        null=True,  # Allow null values
        blank=True  # Allow blank in forms
    )
    client_name = models.CharField(max_length=100)
    legal_name = models.CharField(max_length=100)
    address = models.TextField()
    other_info = models.TextField(blank=True, null=True)
    pan = models.CharField(max_length=10)
    gst_no = models.CharField(max_length=15, blank=True, null=True)
    mobile_no = models.CharField(max_length=15,null=True)
    email = models.EmailField()
    file_no = models.CharField(max_length=20, blank=True, null=True)
    busy_code = models.CharField(max_length=20, blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    it_return = models.BooleanField(default=False, verbose_name="Income Tax")
    gst_return = models.BooleanField(default=False, verbose_name="GST")
    tds_return = models.BooleanField(default=False, verbose_name="TDS")
    tcs_return = models.BooleanField(default=False, verbose_name="TCS") 
    trade_name = models.CharField(max_length=100,null=True, blank=True)
    reg_date = models.DateField(default=date.today,null=True, blank=True)
    cancel_date= models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True,choices=STATUS_CHOICES)
    gst_scheme=models.CharField(max_length=20,null=True, blank=True, choices=GST_SCHEME_CHOICES)
    user_id = models.CharField(max_length=50, unique=True,null=True, blank=True)
    password = models.CharField(max_length=128,null=True, blank=True)  
    gst_data = models.CharField(max_length=20, null=True, blank=True,choices=ACCOUNTING_CHOICES)
    period = models.CharField(max_length=20,null=True, blank=True,choices=PERIOD_CHOICES)
    sale_define=models.CharField(max_length=20,null=True, blank=True,choices=SALE_DEFINE_CHOICES)
    timestamp=models.DateField(default=date.today,null=True, blank=True)
    bank= models.ForeignKey(
        Bank,
        to_field='id',
        on_delete=models.CASCADE,
        null=True,  # Allow null values
        blank=True  # Allow blank in forms
    )
    suspend_date = models.DateField(null=True, blank=True)
    it_alloted_to = models.ForeignKey(
        UserData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    audit_status = models.CharField(
        max_length=30,
        choices=AUDIT_STATUS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Audit Status"
    )

    it_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Income Tax Work Start Date"
    )
    # ✅ multiple emails container
    extra_emails = models.JSONField(default=list, blank=True)

    MAX_EMAILS = 10

    # keep your existing save() that normalizes user_id
    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = None
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.email:
            self.email = _normalize_email(self.email)
        self.extra_emails = _normalize_list(self.extra_emails)
        total = (1 if self.email else 0) + len(self.extra_emails or [])
        if total > self.MAX_EMAILS:
            raise ValidationError(f"Too many emails (max {self.MAX_EMAILS}).")

    @property
    def emails(self):
        base = [_normalize_email(self.email)] if self.email else []
        extras = [e for e in (self.extra_emails or []) if e not in base]
        return base + extras

    def add_email(self, email: str, make_primary: bool = False, save: bool = False):
        e = _normalize_email(email)
        emails = set(self.extra_emails or [])
        if make_primary or not self.email:
            if self.email and self.email != e:
                emails.add(self.email)
            self.email = e
            emails.discard(e)
        else:
            emails.add(e)
        self.extra_emails = sorted(emails)
        if save:
            self.full_clean()
            self.save(update_fields=["email", "extra_emails"])

    def remove_email(self, email: str, save: bool = False):
        e = (email or "").strip().lower()
        changed = False
        if self.email and self.email.lower() == e:
            self.email = None
            changed = True
        emails = set(self.extra_emails or [])
        if e in emails:
            emails.remove(e)
            changed = True
        if changed:
            self.extra_emails = sorted(emails)
            if save:
                self.save(update_fields=["email", "extra_emails"])

    def __str__(self):
        return self.client_name
    

class AccountBank(models.Model):
    # Account Information
    # client_id = models.CharField(max_length=20, blank=True)
    # client_id = models.ForeignKey('client_id', on_delete=models.CASCADE, related_name='accounts')
    ACCOUNT_GROUP_CHOICES = [
        ("Bank Accounts", "Bank Accounts"),
        ("Credit Card", "Credit Card"),
        ("Bank O/D Account","Bank O/D Account")
    ]
    account_id = models.CharField(max_length=20, blank=True)
    client = models.ForeignKey(
        Client,
        to_field='client_id',     # link using client_id, not id
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    client_name = models.CharField(max_length=100)
    account = models.CharField(max_length=100)
    # account_group = models.CharField(max_length=100)
    account_group = models.CharField(
        max_length=100,
        choices=ACCOUNT_GROUP_CHOICES,
        blank=True   # allows an empty/placeholder option
    )
    data_entry = models.CharField(max_length=20, choices=[('Manual', 'Manual'), ('Import', 'Import')], default='Manual')
    acc_mail_id = models.EmailField(blank=True)

    # Bank Information
    account_no = models.CharField(max_length=50)
    two_match = models.CharField(max_length=50, blank=True)
    full_match = models.BooleanField(default=False)
    ifsc_code = models.CharField(max_length=20, blank=False, null=False)
    acc_type = models.CharField(max_length=20, choices=[('Saving', 'Saving'), ('Current', 'Current')], blank=True)
    e_statement = models.BooleanField(default=False)
    bank_name = models.CharField(max_length=100)
    pw = models.CharField(max_length=100, blank=True)
    branch = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=15, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    bank_mail_id = models.EmailField(null=True, blank=True)
    branch_mail_id = models.EmailField(null=True, blank=True)
    branch_mobile_no = models.CharField(max_length=15, null=True, blank=True)
    statement_frequency = models.CharField(max_length=50, null=True, blank=True)  # or use Choices
    reminder_date = models.DateField(null=True, blank=True)
    cif_number = models.CharField(max_length=50, null=True, blank=True)
    stms_pws=models.CharField(max_length=100, blank=True)
    busyacccode=models.CharField(max_length=100, blank=True)
    def save(self, *args, **kwargs):
        # Automatically set client_name when saving
        if self.client and not self.client_name:
            self.client_name = self.client.client_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.client_name} - {self.account}"
  
        


from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime

def get_first_day_of_last_month():
    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    last_month = first_day_this_month - datetime.timedelta(days=1)
    return last_month.replace(day=1)
def get_last_day_of_last_month():
    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - datetime.timedelta(days=1)
    return last_day_last_month



class DataEntry(models.Model):
    STATUS_CHOICES = [
        ('Done', 'Done'),
        ('Nil', 'Nil'),
        ('Hold', 'Hold'),
        ('Pending', 'Pending'),

    ]
    FORMAT_CHOICES = [
        ('Soft Copy', 'Soft Copy'),
        ('Hard Copy', 'Hard Copy'),
        ('Link', 'Link'),
    ]

    RECEIVED_BY_CHOICES = [
        ('Mail', 'Mail'),
        ('Acstkameet', 'Acstkameet'),
        ('WhatsApp', 'WhatsApp'),
        ('Anydesk', 'Anydesk'),
    ]
    QUERY_CHOICES = [
        ('No', 'No'),
        ('Pending', 'Pending'),
        ('Done', 'Done'),
    ]

        
    # client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='data_entries',db_constraint=False)
    client = models.ForeignKey('Client', on_delete=models.DO_NOTHING, related_name='data_entries', db_constraint=False)

    account = models.ForeignKey('AccountBank', on_delete=models.SET_NULL, null=True, blank=True,db_constraint=False, related_name='+')
    # user=models.ForeignKey('User',on_delete=models.CASCADE,related_name='users',null=True, blank=True)
    alloted_to = models.ForeignKey('UserData',on_delete=models.CASCADE,max_length=100, blank=True, null=True,db_constraint=False)
    virtual_account_type = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        choices=[('1', 'Sales'), ('2', 'Purchase')]
    )
    # mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='data_entry')
    query = models.CharField(max_length=20, choices=QUERY_CHOICES , null=True,blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,null=True,blank=True)
    is_nil = models.BooleanField(
        default=False,
        verbose_name="Nil",
    )
    # Dates
    rec_date = models.DateField(
        verbose_name="Received Date",
        null=True, blank=True
    )    
    format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default='Soft Copy'
    )
    received_by = models.CharField(
        max_length=20,
        choices=RECEIVED_BY_CHOICES,
        default='Mail'
    )

    from_date = models.DateField(null=True, blank=True)
    last_date = models.DateField(null=True, blank=True)
    alloted_date = models.DateField(null=True, blank=True)
    done_date = models.DateField(null=True, blank=True)    
    remark = models.TextField(blank=True, null=True)
    attach_file = models.FileField(
    upload_to=upload_to,
    max_length=500,
    blank=True,
    null=True
)

    msg_id = models.CharField(max_length=150, null=True,blank=True)

    def save(self, *args, **kwargs):
        using = kwargs.get('using')  # <== detect DB being used
        if not kwargs.get('using'):
            raise Exception("❌ Missing 'using' in save() — default DB being used!")
        is_new = self.pk is None
        old_file = self.attach_file.name if self.attach_file else None

        super().save(*args, **kwargs)  # this uses correct DB

        if is_new and self.attach_file and old_file and not old_file.startswith(f"{self.id}_"):
            import os
            from django.conf import settings

            old_path = os.path.join(settings.MEDIA_ROOT, self.attach_file.name)
            base_dir = os.path.dirname(old_path)
            ext = os.path.splitext(old_path)[1]
            new_filename = f"{self.id}{ext}"
            new_path = os.path.join(base_dir, new_filename)

            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                self.attach_file.name = os.path.relpath(new_path, settings.MEDIA_ROOT)
                super(DataEntry, self).save(using=using, update_fields=["attach_file"])

        
    def __str__(self):
        return f"{self.id} - {self.client.client_name}"
    
    def get_months_list(self):
        return self.months.split(',') if self.months else []
    
    def set_months(self, months):
        self.months = ','.join(months)
    
    class Meta:
        verbose_name_plural = "Data Entries"

from django.dispatch import receiver
from django.db.models.signals import post_save


class TaxSuspension(models.Model):
    SUSPENSION_TYPES = [
        ('GST', 'GST'),
        ('TDS', 'TDS'),
        ('Income', 'Income Tax'),
        ('TCS', 'TCS'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    account = models.ForeignKey(AccountBank, on_delete=models.CASCADE, null=True, blank=True)
    tax_type = models.CharField(max_length=10, choices=SUSPENSION_TYPES)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True) #suspent is true then is_active=true

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate exactly one entity is selected
        if not any([self.client, self.group, self.account]):
            raise ValidationError("Please select either a Client, Group, or Account")
        
        # Validate date range
        if self.to_date and self.to_date < self.from_date:
            raise ValidationError("To date must be after from date")

    def __str__(self):
        entity = self.client or self.group or self.account
        return f"Suspended {self.get_tax_type_display()} for {entity}"

    class Meta:
        ordering = ['-from_date']


class IncomeTaxReturn(models.Model):
    # YEAR_CHOICES = [(str(y), str(y)) for y in range(2015, 2031)]  # Adjust range as needed
    
    # 1. Year (e.g., 2023-24)
    # year = models.CharField(max_length=9, choices=YEAR_CHOICES)
    year = models.DateField(verbose_name="Financial Year Start Date")


    # 2. Client (ForeignKey to your Client model)
    # client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='income_tax_returns',db_constraint=False)
    client = models.ForeignKey('Client', on_delete=models.DO_NOTHING, related_name='income_tax_returns', db_constraint=False)

    # 3. Audit applicable (Yes/No)
    AUDIT_APPLICABLE_CHOICES = [('as partner', 'as partner'), ('audit applicable', 'audit applicable'), ('not applicable', 'not applicable')]
    audit_applicable = models.CharField(max_length=20, choices=AUDIT_APPLICABLE_CHOICES)

    # 4. CA (CharField, or ForeignKey if you have a CA model)
    ca = models.CharField(max_length=100,null=True, blank=True)

    # 5. AUDIT STAGE (e.g., 'Started', 'In Progress', 'Completed')
    AUDIT_STAGE_CHOICES = [
        ('Audit Sent', 'Audit Sent'),
        ('Query From Audit', 'Query From Audit'),
        ('Audit Received', 'Audit Received'),
        ('Audit Checked', 'Audit Checked'),
        ('Audit Filled', 'Audit Filled'),
    ]
    audit_stage = models.CharField(max_length=20, choices=AUDIT_STAGE_CHOICES, blank=True, null=True)

    # 6. Audit active/hold
    AUDIT_STATUS_CHOICES = [('Active', 'Active'), ('Hold', 'Hold')]
    audit_status = models.CharField(max_length=6, choices=AUDIT_STATUS_CHOICES, default='Active')

    # 7. Audit hold reason
    audit_hold_reason = models.TextField(blank=True, null=True)

    # 8. Audit ACK (Acknowledgement number)
    audit_ack = models.CharField(max_length=50, blank=True, null=True)

    # 9. Audit Date
    audit_date = models.DateField(blank=True, null=True)

    # 10. Return type (e.g., 'Original', 'Revised')
    RETURN_TYPE_CHOICES = [
        ('Original', 'Original'),
        ('Revised', 'Revised'),
        ('Rectified', 'Rectified'),
        ('Updated', 'Updated'),
    ]

    YES_NO = (("Yes", "Yes"), ("No", "No"))
    PENDING_FILED = (("Pending", "Pending"), ("Filed", "Filed"))
    return_type = models.CharField(max_length=10, choices=RETURN_TYPE_CHOICES)

    # 11. Revise no (revision number, if applicable)
    revise_no = models.PositiveIntegerField(blank=True, null=True)

    # 12. Alloted to (ForeignKey to UserData)
    alloted_to = models.ForeignKey('UserData', on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False)

    # 13. Stage (e.g., 'Draft', 'Filed', 'Verified')
    STAGE_CHOICES = [
        ('Sleeping', 'Sleeping'),
        ('Call for data', 'Call for data'),
        ('Working', 'Working'),
        ('Query to client', 'Query to client'),
        ('Pending for checking', 'Pending for checking'),
        ('Pending for approve', 'Pending for approve'),
        ('Pending for audit sent', 'Pending for audit sent'),
        ('audit sent', 'audit sent'),
        ('Pending for filing', 'Pending for filing'),
        ('Filed', 'Filed'),
    ]
    stage = models.CharField(max_length=80, choices=STAGE_CHOICES, blank=True, null=True)

    # 14. Return active/hold
    RETURN_STATUS_CHOICES = [('Active', 'Active'), ('Hold', 'Hold')]
    return_status = models.CharField(max_length=6, choices=RETURN_STATUS_CHOICES, default='Active')

    # 15. Return hold reason
    return_hold_reason = models.TextField(blank=True, null=True)

    # 16. ACK no (Return acknowledgement number)
    ack_no = models.CharField(max_length=50, blank=True, null=True)

    # 17. Ack date
    ack_date = models.DateField(blank=True, null=True)

    # 18. Verification Date
    verification_date = models.DateField(blank=True, null=True)
    flag = models.CharField(max_length=200, blank=True)  # e.g. "High Tax/Return Urgent"

    want_revised = models.CharField(max_length=3, choices=YES_NO, blank=True)

    want_rectified = models.CharField(max_length=3, choices=YES_NO, blank=True)
    rectification_status = models.CharField(max_length=7, choices=PENDING_FILED, blank=True)
    revised_status = models.CharField(max_length=7, choices=PENDING_FILED, blank=True)
    def __str__(self):
        return f"{self.client} - {self.year} - {self.return_type}"

    class Meta:
        verbose_name = "Income Tax Return"
        verbose_name_plural = "Income Tax Returns"
        unique_together = ('year', 'client', 'return_type', 'revise_no')


from django.db.models.signals import post_delete

@receiver(post_delete, sender=DataEntry)
def delete_attach_file_on_entry_delete(sender, instance, **kwargs):
    if instance.attach_file and instance.attach_file.name:
        file_path = os.path.join(settings.MEDIA_ROOT, instance.attach_file.name)
        if os.path.exists(file_path):
            os.remove(file_path)

class AISUpload(models.Model):
    file_name = models.CharField(max_length=255)
    information_code = models.CharField(max_length=50)
    description = models.TextField()
    source = models.TextField()
    count = models.IntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2,null=True,blank=True)
    is_approved = models.BooleanField(default=False)
    total_records = models.IntegerField(default=0)  # ✅ Add this line

    def __str__(self):
        return f"{self.information_code} - {self.description}"

class AISRecord(models.Model):
    upload = models.ForeignKey(AISUpload, on_delete=models.CASCADE, related_name='records',blank=True, null=True)
    section_title = models.TextField(blank=True, null=True)
    data_json = models.TextField()  # store JSON as text

    def get_data(self):
        return json.loads(self.data_json)

    def set_data(self, data_dict):
        self.data_json = json.dumps(data_dict)


#fetch mail
# accounts/models.py
import os
import re
from django.db import models
from django.utils import timezone


try:
    from .utills import get_fiscal_year_from_date  # returns '2025_26'
except Exception:
    from datetime import date as _date
    def get_fiscal_year_from_date(d: _date) -> str:
        if d.month >= 4:
            start_year, end_year = d.year, d.year + 1
        else:
            start_year, end_year = d.year - 1, d.year
        return f"{start_year}_{str(end_year)[-2:]}"

def _sanitize_email_for_path(email: str) -> str:
    s = (email or "").strip().lower()
    s = s.replace("@", "_at_")
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"



class MailLog(models.Model):
    # required fields
    mailbox       = models.EmailField(blank=True)
    rec_dat       = models.DateTimeField()             # received datetime (UTC)
    sender_mail   = models.EmailField()
    receiver_mail = models.TextField()                 # raw "To:" (can be multiple)
    subject       = models.TextField(blank=True, default="")
    # REPLACED: store metadata (list of attachments), not a boolean flag
    attachments   = models.JSONField(default=list, blank=True)
    # msg_id should be unique per mailbox, not globally
    msg_id        = models.CharField(max_length=255)
    
    # auto
    fetched_at    = models.DateTimeField(auto_now_add=True)
    statement_link = models.TextField(blank=True, null=True)
    class Meta:
        unique_together = ("mailbox", "msg_id")   # de-dupe per account
        indexes = [
            models.Index(fields=["mailbox", "rec_dat"]),
            models.Index(fields=["rec_dat"]),
            models.Index(fields=["msg_id"]),
        ]

    def __str__(self):
        return f"{self.rec_dat:%Y-%m-%d %H:%M} | {self.sender_mail} | {self.subject[:60]}"

    # ---- Helpers for your fetcher ----
    def fy_str(self) -> str:
        """Indian FY from local date of rec_dat, e.g. '2025_26'."""
        local_d = timezone.localtime(self.rec_dat).date()
        return get_fiscal_year_from_date(local_d)

    def build_attachment_path(self, recipient_email: str, filename: str) -> str:
        """
        Relative path under MEDIA_ROOT where a single file should be stored.
        Example: fy_2025_26/acstkameet_gmail.com/abc_gmail.com/attachment1.pdf
        """
        fy = self.fy_str()                       # '2025_26'
        box = _sanitize_email_for_path(self.mailbox)          # acstkameet_gmail.com
        rec = _sanitize_email_for_path(recipient_email)       # abc_gmail.com
        return os.path.join(f"fy_{fy}", box, rec, filename)

    @property
    def has_attachments(self) -> bool:
        return bool(self.attachments)

    @property
    def db_alias(self) -> str:
        """
        Safe accessor for the database alias this instance came from,
        usable in templates (avoids _state access in templates).
        """
        try:
            return self._state.db or "default"
        except Exception:
            return "default"
    def add_attachment_meta(self, *, recipient: str, filename: str,
                            rel_path: str, content_type: str = "",
                            size_bytes: int = 0, part_index: int = 0) -> None:
        """
        Append one attachment record into JSON list.
        Each item looks like:
          {
            "recipient": "abc@gmail.com",
            "filename": "attachment1.pdf",
            "path": "fy_2025_26/acstkameet_gmail.com/abc_gmail.com/attachment1.pdf",
            "content_type": "application/pdf",
            "size_bytes": 12345,
            "part_index": 0
          }
        """
        meta = {
            "recipient": recipient,
            "filename": filename,
            "path": rel_path.replace("\\", "/"),
            "content_type": content_type or "",
            "size_bytes": int(size_bytes or 0),
            "part_index": int(part_index or 0),
        }
        data = list(self.attachments or [])
        data.append(meta)
        self.attachments = data
        # keep a convenient base dir (first recipient’s dir)
        if not self.attachment_dir and "/" in meta["path"]:
            self.attachment_dir = "/".join(meta["path"].split("/")[:-1])



class PdfConvertFailure(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    client = models.ForeignKey("Client", on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey("Group", on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey("AccountBank", on_delete=models.SET_NULL, null=True, blank=True)

    attachment_name = models.CharField(max_length=255)
    attachment_path = models.TextField()

    error_message = models.TextField()
    module_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"PDF Failed | {self.attachment_name} | {self.error_message[:40]}"
    




class PendingBusyBankMapping(models.Model):
    """
    Stores BUSY bank accounts which are NOT mapped in KAMEET AccountBank
    One row per (client + account_no + FY)
    """

    # -------------------------
    # Client & Group
    # -------------------------
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="pending_busy_banks"
    )

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # -------------------------
    # BUSY identifiers
    # -------------------------
    busy_company_code = models.CharField(
        max_length=20,
        help_text="Client.busy_code"
    )

    # -------------------------
    # Bank details from BUSY
    # -------------------------
    bank_name = models.CharField(max_length=255)

    account_no = models.CharField(
        max_length=50,
        db_index=True
    )

    ifsc = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    swift = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    # -------------------------
    # FY & BUSY file info
    # -------------------------
    fy = models.CharField(
        max_length=7,   # e.g. 2023-24
        db_index=True
    )

    busy_updated_at = models.DateTimeField(
        help_text="Last modified datetime of BUSY .bds file"
    )

    # -------------------------
    # Audit fields
    # -------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    busy_account_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Account code from BUSY"
    )
    class Meta:
        db_table = "pending_busy_bank_mapping"

        ordering = [
            "client__client_name",
            "fy",
            "bank_name"
        ]

        # ❗ prevent duplicate pending rows
        unique_together = (
            "client",
            "account_no",
            "fy",
        )

        indexes = [
            models.Index(fields=["busy_company_code"]),
            models.Index(fields=["fy"]),
            models.Index(fields=["account_no"]),
        ]

    def __str__(self):
        return f"{self.client.client_name} | {self.bank_name} | {self.account_no} | {self.fy}"
    


# document utility
class DocCategory(models.Model):
    """
    Master table: categories like Share Broker, Property Purchase, etc.
    Must NOT hardcode labels in logic; store flags here. (Spec)
    """
    # name = models.CharField(max_length=120, unique=True)
    category_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    # Flags (spec)
    annual_allowed = models.BooleanField(default=False)
    event_allowed = models.BooleanField(default=False)
    continue_till_closed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)  # predefined categories
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.category_type or ""


class DocSubType(models.Model):
    """
    Master table: sub-documents under category: Ledger, Contract Notes, etc.
    User can add extra; must be stored permanently (spec).
    """
    category = models.ForeignKey(DocCategory, on_delete=models.CASCADE, related_name="subtypes")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.category_type} - {self.name}"


# client wise category
class ClientWiseCategoryName(models.Model):
    """
    Stores client-wise category specific name
    e.g.
    Client: Aarti Jewellers
    Category: Mutual Fund Broker
    Name: Rajendra Prasad
    """

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="category_names"
    )

    category = models.ForeignKey(
        DocCategory,
        on_delete=models.CASCADE,
        related_name="client_category_names"
    )

    name = models.CharField(
        max_length=120,
        help_text="e.g. Rajendra Prasad, Rakesh Shah"
    )
      # ✅ NEW (optional, multiple passwords allowed)
    passwords = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated passwords (optional)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("client", "category", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.client} | {self.category.category_type} | {self.name}"


# Client document
class ClientDocItem(models.Model):
    """
    This represents one "expected document checklist item" for a client,
    for a FY (annual) or for an event (event-based).
    This is how we track pending/received/NA (spec).
    """

    DOC_KIND_CHOICES = (
        ("ANNUAL", "Annual"),
        ("EVENT", "Event"),
    )
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("RECEIVED", "Received"),
        ("NA", "Not Applicable"),
    )
    DATA_ENTRY_STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("DONE", "Done"),
        ("HOLD", "Hold"),
        ("DONE_NO_RECEIVE", "Done without Received"),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="doc_items",db_constraint=False)
    category = models.ForeignKey(DocCategory, on_delete=models.PROTECT,db_constraint=False)
    subtype = models.ForeignKey(DocSubType, on_delete=models.PROTECT, null=True, blank=True,db_constraint=False)

    doc_kind = models.CharField(max_length=10, choices=DOC_KIND_CHOICES)

    # annual fields
    financial_year = models.CharField(max_length=7, blank=True, default="")  # e.g. 2024_25

    # event fields
    event_name = models.CharField(max_length=120, blank=True, default="")

    remarks = models.TextField(blank=True, default="")
    # Received Status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    data_entry_status = models.CharField(
        max_length=20,
        choices=DATA_ENTRY_STATUS_CHOICES,
        default="PENDING"
    )
    category_name = models.ForeignKey(
        ClientWiseCategoryName,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "financial_year", "status"]),
            models.Index(fields=["client", "doc_kind", "status"]),
        ]

    def __str__(self):
        tag = self.financial_year if self.doc_kind == "ANNUAL" else self.event_name
        return f"{self.client} | {self.category} | {self.subtype or '-'} | {tag}"


def client_document_upload_path(instance, filename):
    # store client-wise docs
    # Example path: documents/CLIENTID/2024_25/Share Broker/Ledger/file.pdf
    client_id = getattr(instance.doc_item.client, "client_id", None) or instance.doc_item.client.id
    fy = instance.doc_item.financial_year or "events"
    cat = instance.doc_item.category.category_type.replace("/", "-")
    sub = (instance.doc_item.subtype.name if instance.doc_item.subtype else "general").replace("/", "-")
    return f"documents/{client_id}/{fy}/{cat}/{sub}/{filename}"


class ClientDocFile(models.Model):
    """
    Attach multiple files per item (spec).
    Stores file password (optional) + carry-forward preference + history via separate table.
    """
    doc_item = models.ForeignKey(ClientDocItem, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=client_document_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    file_password = models.CharField(max_length=80, blank=True, default="")
    password_validity_year = models.CharField(max_length=7, blank=True, default="")  # FY for which password valid
    carry_password_forward = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.doc_item} ({self.file.name})"


class DocPasswordHistory(models.Model):
    """
    Maintain password history (spec).
    """
    doc_item = models.ForeignKey(ClientDocItem, on_delete=models.CASCADE, related_name="password_history")
    password = models.CharField(max_length=80)
    validity_year = models.CharField(max_length=7, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)


