from django.urls import path,include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('group_form/', views.group_form, name='group_form'),
    path('client_form/', views.client_form, name='client_form'),
    path('data_entry/', views.data_entry, name='data_entry'),
    path('account_form/', views.account_form, name='account_form'),
    
    path('account_list/', views.account_list, name='account_list'),
    path('get_account_data/', views.get_account_data, name='get_account_data'),
    path('client_list/', views.client_list, name='client_list'),
    path('clients/delete/<int:client_id>/', views.delete_client, name='delete_client'),
    path('accounts/delete/<int:account_id>/', views.delete_account, name='delete_account'),
    path("clients/bulk-delete/", views.bulk_delete_clients, name="bulk_delete_clients"),
    path('groups/delete/<int:group_id>/', views.delete_group, name='delete_group'),

    path('get_client_accounts/', views.get_client_accounts, name='get_client_accounts'),
    path('group_list/', views.group_list, name='group_list'),
    path('data_entry_list/', views.data_entry_list, name='data_entry_list'),
    path('user_form/', views.user_form, name='user_form'),
    path('user_list/', views.user_list, name='user_list'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('get-client-data/', views.get_client_data, name='get_client_data'),
    path('get-account-data-for-entry/', views.get_account_data_for_entry, name='get_account_data_for_entry'),
    path('data_entry_list/', views.data_entry_list, name='data_entry_list'),
    path('data-entry/delete/<int:entry_id>/', views.delete_data_entry, name='delete_data_entry'),
    path('delete_report_data_entry/', views.delete_report_data_entry, name='delete_report_data_entry'),

    path('data-entry/get/<int:entry_id>/', views.get_entry, name='get_entry'),

    path('data-entry/update/<int:entry_id>/', views.update_data_entry, name='update_data_entry'),
    path('get-client-accounts-edit/', views.get_client_accounts_grouped_edit, name='get_client_accounts_grouped_edit'),
    path('get-client-accounts-add/', views.get_client_accounts_grouped_add, name='get_client_accounts_grouped_add'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reports/', views.reports, name='reports'),
    path("ajax/clients/",  views.ajax_clients,  name="ajax_clients"),
    path("ajax/accounts/", views.ajax_accounts, name="ajax_accounts"),
    path("ajax/report_rows/", views.ajax_report_rows, name="ajax_report_rows"),
    # urls.py
    path("ajax/entry_detail/", views.entry_detail, name="entry_detail"),

    path('download-launcher/', views.download_launcher, name='download_launcher'),
    path("open-bank-pdf/", views.serve_bank_pdf, name="open_bank_pdf"),
    path("ajax/get_busy_status/", views.get_busy_status, name="get_busy_status"),
    path('suspend_form/', views.suspend_form, name='suspend_form'),
    path('suspend_list/', views.suspend_list, name='suspend_list'),
    path('suspend/<int:suspension_id>/', views.suspend_form, name='suspend_form'),  # For modify

    path('tax-suspension/delete/<int:pk>/', views.delete_tax_suspension, name='delete_tax_suspension'),
    path('ajax/clients/', views.get_clients, name='ajax_get_clients'),
    path('group_wise_report/', views.group_wise_report, name='group_wise_report'),
    path('it_return_form/', views.it_return_form, name='it_return_form'),
    path('it-return/modify/', views.it_return_form, name='it_return_modify'),
    path('get-client-details/<int:client_id>/', views.get_client_details, name='get_client_details'),
    path('it_return_list/', views.it_return_list, name='it_return_list'),
    path('itrs/delete/<int:pk>/', views.delete_itr, name='delete_itr'),
    path('upload-pdf/', views.upload_ais_pdf, name='upload_ais_pdf'),
    path('review/<int:upload_id>/', views.review_upload, name='review_upload'),
    path('summary/', views.summary_view, name='summary_view'),
    path("convert-pdfs/", views.convert_pdfs_to_excel, name="convert_pdfs_to_excel"),
    path("download-excel/", views.download_excel, name="download_excel"),  # <-- add this
    path("it-returns/", views.it_return_report, name="it_return_report"),
    path("bank_pdf_upload/", views.bank_pdf_upload, name="bank_pdf_upload"),
    path("footprint/local/", views.footprint_local, name="footprint_local_default"),
    path("footprint/local/<str:key>/", views.footprint_local, name="footprint_local"),
    path("it-returns/upload-status/", views.it_upload_status, name="it_upload_status"),
    path("it/users.json", views.it_user_list_json, name="it_user_list_json"),
    path("it/bulk-reassign/", views.it_bulk_reassign, name="it_bulk_reassign"),
    path("it/group-reassign/", views.it_group_reassign, name="it_group_reassign"),
    path("it/group-list/", views.it_group_list_json, name="it_group_list_json"),
    path("bank/convert/", views.bank_pdf_to_excel, name="bank_pdf_to_excel"),
    path("bank-convert/", views.bank_pdf_to_excel, name="bank_pdf_to_excel"),
    path('mail_log_list/', views.mail_log_list, name='mail_log_list'),
    path("mail_log/fetch/", views.mail_log_fetch, name="mail_log_fetch"),
    path(
        "mail/attachment/<int:mail_id>/<int:idx>/<path:filename>",
        views.mail_attachment_pdf,
        name="mail_attachment_pdf",
    ),
    path("ajax/group-clients/", views.ajax_group_clients, name="ajax_group_clients"),
    path("ajax/associate-email/", views.ajax_associate_email, name="ajax_associate_email"),
    path("mail_log_report/",views.mail_log_report,name="mail_log_report"),
    path("bank_mapping/", views.bank_account_mapping, name="bank_account_mapping"),
    path("ajax/submit-mapping/", views.ajax_submit_mapping, name="ajax_submit_mapping"),

    path('ajax/busy-accounts/', views.ajax_busy_accounts, name='ajax_busy_accounts'),  # NEW
    path("ajax/add_account/", views.ajax_add_account, name="ajax_add_account"),

    path("ajax/clear_mapping/", views.ajax_clear_mapping, name="ajax_clear_mapping"),
    path("ajax/filtered_mapping/", views.ajax_filtered_mapping, name="ajax_filtered_mapping"),
    path("ajax/import_mail_to_dataentry/", views.ajax_import_mail_to_dataentry, name="ajax_import_mail_to_dataentry"),
    path('ajax/group_clients/', views.group_clients, name='group_clients'),
    path('ajax/client_accounts_multi/', views.client_accounts_multi, name='client_accounts_multi'),        
    path("reports/pending_detail_excel/", views.pending_detail_excel, name="pending_detail_excel"),
    path("ajax/pending_detail_summary/", views.pending_detail_summary, name="pending_detail_summary"),  
    # path("open_mail_extract/", views.open_mail_and_extract_link, name="open_mail_extract"),
    # urls.py
    
    path(
        "open_mail_and_extract_link/",
        views.open_mail_and_extract_link,
        name="open_mail_and_extract_link",
    ),

    path("bank-mapping-pending/", views.pending_bank_mapping, name="pending_bank_mapping"),
    path(
        "unmapped-busy-accounts/",
        views.unmapped_busy_accounts_report,
        name="unmapped_busy_accounts_report"
    ),
    path(
        "hardcopy_received_report/",
        views.hardcopy_received_report,
        name="hardcopy_received_report",
    ),

    # document utility
    path("dashboard/", views.doc_dashboard, name="dashboard"),
    path("report/annual-pending/", views.annual_pending_report, name="annual_pending_report"),
    path("report/event-pending/", views.event_pending_report, name="event_pending_report"),

    # APIs 
    path("api/subtypes/", views.api_subtypes, name="api_subtypes"),
    # path("api/create-other-subtype/", views.api_create_other_subtype, name="api_create_other_subtype"),
    path("api/upload/", views.api_upload_doc, name="api_upload_doc"),
    # path("api/create-category/", views.api_create_category, name="api_create_category"),
    # path("api/create-subdoc/", views.api_create_subdoc, name="api_create_subdoc"),
    path("api/dashboard/rows/", views.api_dashboard_rows, name="api_dashboard_rows"),
    path("api/doc-files/", views.api_doc_files, name="api_doc_files"),
    path("api/doc-item/", views.api_doc_item_detail, name="api_doc_item"),
    path("api/doc-delete/", views.api_delete_doc_item, name="api_delete_doc_item"),
    path("api/doc-file/delete/", views.api_delete_doc_file, name="api_delete_doc_file"),
    path("categories/", views.category_list, name="category_list"),
    path("api/category/save/", views.api_save_category, name="api_save_category"),
    path("api/category/delete/", views.api_delete_category, name="api_delete_category"),
    path("sub-documents/", views.subdoc_list, name="subdoc_list"),
    path("api/subdoc/save/", views.api_save_subdoc, name="api_save_subdoc"),
    path("api/subdoc/delete/", views.api_delete_subdoc, name="api_delete_subdoc"),
    path("api/client-category-names/",
         views.api_client_category_names,
         name="api_client_category_names"),

    path("api/category-name/create/",
         views.api_create_category_name,
         name="api_create_category_name"),

    path(
        "client-category-names/",
        views.api_all_category_names,
        name="client_category_names"
    ),

    path("client-category-name/<int:pk>/edit/", views.edit_category_name,name="edit_category_name"),
    path("client-category-name/<int:pk>/delete/", views.delete_category_name,name="delete_category_name"),
    path(
        "ajax/mail/<int:mail_id>/attachments/",
        views.ajax_mail_attachments,
        name="ajax_mail_attachments"
    ),
    
    path(
        "ajax/mail/save-docs/",
        views.save_mail_docs,
        name="ajax_mail_save_docs"
    ),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

