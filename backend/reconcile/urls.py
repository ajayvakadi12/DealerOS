from django.urls import path
from .views import DisagreementListView, SummaryMetricsView, OrganizationListView

urlpatterns = [
    path('disagreements/', DisagreementListView.as_view(), name='disagreements-list'),
    path('summary/', SummaryMetricsView.as_view(), name='summary-metrics'),
    path('organizations/', OrganizationListView.as_view(), name='organizations-list'),
]
