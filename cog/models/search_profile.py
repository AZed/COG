from django.db import models
from constants import APPLICATION_LABEL
from project import Project

# Project-specific search configuration (persisted to the database)
class SearchProfile(models.Model):
    
    project = models.OneToOneField(Project, blank=False, null=False)
    
    # name that identifies this configuration
    #name = models.CharField(max_length=50, blank=False, unique=True, default='')
    
    # The URL of the back-end search service - don't verify its existence because it might take longer than allowed
    url = models.URLField(blank=False, verify_exists=False)
        
    # string of the form name=value, name=value....
    constraints = models.CharField(max_length=200, blank=True, null=True, default='')
    
    def facets(self):
        return self.searchfacet_set.all().order_by('order')
    
    def __unicode__(self):
        return "%s Search Profile" % self.project.short_name
    
    class Meta:
        app_label= APPLICATION_LABEL