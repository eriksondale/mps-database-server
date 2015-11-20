from django.conf.urls import patterns, url
from .views import *

urlpatterns = patterns('',
    # Proposed URLS:
    # User can view drugtrials
    url(r'^drugtrials/$', DrugTrialList.as_view(), name='drugtrial_list'),
    url(r'^drugtrials/(?P<pk>[0-9]+)/$', drug_trial_detail, name='drugtrial_detail'),
    # User can view adverse events
    url(r'^adverse_events/$', AdverseEventsList.as_view(), name='adverse_events_list'),
    url(r'^adverse_events/(?P<pk>[0-9]+)/$', adverse_events_detail, name='adverse_events_details'),
)