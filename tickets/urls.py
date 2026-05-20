from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/search/', views.ticket_search, name='ticket_search'),
    path('tickets/new/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/<int:pk>/comments/add/', views.comment_add, name='comment_add'),
    path('tickets/<int:pk>/attachments/add/', views.attachment_upload, name='attachment_upload'),
    path('attachments/<int:attachment_id>/download/', views.attachment_download, name='attachment_download'),
    path('profile/', views.profile_edit, name='profile_edit'),
    path('admin-console/', views.admin_console, name='admin_console'),
    path('diagnostics/', views.diagnostics, name='diagnostics'),
    path('go/', views.go_next, name='go_next'),
    path('profile/', views.profile_edit, name='profile_edit'),
    path('profile/role-request/<int:request_id>/', views.handle_role_request, name='handle_role_request'),
]
